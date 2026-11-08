r"""
Adaptive Assessment & Mastery Engine Service
Project: Vedantu Online Coding Assessment Platform (Phase 6)
Workspace: E:\VedantuCodingPlatform_New

Calculates deterministic topic mastery, tracks learning progression,
identifies strengths & weaknesses, dynamically adjusts difficulty levels,
and delivers explainable coding question recommendations based on authoritative functional evaluations.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.student_topic_mastery import StudentTopicMastery
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.user import User
from app.schemas.adaptive import (
    DifficultyBreakdownItem,
    MasteryHistoryResponse,
    MasteryHistorySnapshot,
    QuestionRecommendationItem,
    QuestionRecommendationListResponse,
    StrengthsAndWeaknessesResponse,
    StudentPerformanceResponse,
    TopicCatalogItem,
    TopicCatalogResponse,
    TopicMasteryItem,
    TopicMasteryListResponse,
    TopicPracticeDetailResponse,
    TopicPracticeQuestionItem,
)
from app.core.question_seed_data import TOPIC_DESCRIPTIONS
from app.schemas.question import QuestionPublicResponse, TestCasePublicResponse
from app.schemas.submission import SubmissionCreate, SubmissionResponse
from app.services.evaluation_service import evaluation_service

logger = logging.getLogger("adaptive_service")

# ------------------------------------------------------------------------------
# Deterministic Difficulty & Scoring Constants
# ------------------------------------------------------------------------------
DIFFICULTY_WEIGHTS: Dict[str, float] = {
    "EASY": 1.0,
    "MEDIUM": 1.5,
    "HARD": 2.0,
}

PRIOR_MASTERY_SCORE = 30.0
PRIOR_WEIGHT_K = 1.5


def classify_mastery_level(score: float) -> str:
    """Deterministic topic mastery tiers."""
    if score >= 85.0:
        return "ADVANCED"
    elif score >= 65.0:
        return "PROFICIENT"
    elif score >= 40.0:
        return "DEVELOPING"
    return "BEGINNER"


def classify_confidence_level(attempt_count: int) -> str:
    """Confidence tier based on question sample volume."""
    if attempt_count >= 5:
        return "HIGH"
    elif attempt_count >= 2:
        return "MEDIUM"
    return "LOW"


class AdaptiveService:
    """
    Core Adaptive Assessment Engine.
    Analyzes historical submissions, computes explainable topic masteries,
    generates personalized recommendations, and adjusts difficulty dynamically.
    """

    async def calculate_topic_mastery(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        persist: bool = True,
        trigger_event: str = "RECALCULATION",
    ) -> List[StudentTopicMastery]:
        """
        Calculates and optionally persists authoritative topic mastery records for a student.
        Uses Bayesian smoothing with attempt efficiency penalties and difficulty weighting.
        """
        # 1. Fetch all distinct topics available across active questions
        topics_stmt = (
            select(Question.topic)
            .where(Question.is_archived == False)  # noqa: E712
            .distinct()
        )
        topics_res = await db.execute(topics_stmt)
        all_system_topics = [t for t in topics_res.scalars().all() if t]

        # 2. Fetch all student submissions with associated questions
        sub_stmt = (
            select(Submission)
            .options(selectinload(Submission.question))
            .where(Submission.user_id == user_id)
            .order_by(Submission.created_at.asc())
        )
        sub_res = await db.execute(sub_stmt)
        submissions = sub_res.scalars().all()

        # Group submissions by topic
        topic_subs: Dict[str, List[Submission]] = {t: [] for t in all_system_topics}
        for sub in submissions:
            if sub.question and sub.question.topic:
                t = sub.question.topic
                if t not in topic_subs:
                    topic_subs[t] = []
                topic_subs[t].append(sub)

        now = datetime.now(timezone.utc)
        results: List[StudentTopicMastery] = []

        # 3. Compute topic metrics
        for topic, subs in topic_subs.items():
            if not subs:
                # Student has no submissions in this topic
                mastery_record = StudentTopicMastery(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    topic=topic,
                    mastery_score=0.0,
                    mastery_level="BEGINNER",
                    confidence_level="LOW",
                    questions_attempted=0,
                    questions_solved=0,
                    total_submissions=0,
                    successful_submissions=0,
                    best_score=0.0,
                    recommended_difficulty="EASY",
                    trend="STABLE",
                    last_calculated_at=now,
                )
                results.append(mastery_record)
                continue

            # Group submissions by distinct question
            q_map: Dict[uuid.UUID, List[Submission]] = {}
            for s in subs:
                q_id = s.question_id
                if q_id not in q_map:
                    q_map[q_id] = []
                q_map[q_id].append(s)

            q_attempted = len(q_map)
            q_solved = 0
            weighted_points_sum = 0.0
            weights_sum = 0.0
            best_overall_score = 0.0
            successful_subs = sum(1 for s in subs if s.status == "ACCEPTED")

            easy_solved = 0
            med_solved = 0
            hard_solved = 0
            easy_att = 0
            med_att = 0
            hard_att = 0

            for q_id, q_subs in q_map.items():
                first_sub = q_subs[0]
                q_diff = (first_sub.question.difficulty or "MEDIUM").upper()
                q_marks = first_sub.question.marks or 10
                diff_weight = DIFFICULTY_WEIGHTS.get(q_diff, 1.5)

                if q_diff == "EASY":
                    easy_att += 1
                elif q_diff == "HARD":
                    hard_att += 1
                else:
                    med_att += 1

                # Best score achieved on this question
                best_sub_score = max(s.score for s in q_subs)
                if best_sub_score > best_overall_score:
                    best_overall_score = best_sub_score

                is_solved = any(s.status == "ACCEPTED" for s in q_subs)
                if is_solved:
                    q_solved += 1
                    if q_diff == "EASY":
                        easy_solved += 1
                    elif q_diff == "HARD":
                        hard_solved += 1
                    else:
                        med_solved += 1

                # Score ratio
                score_ratio = min(1.0, max(0.0, best_sub_score / (q_marks if q_marks > 0 else 1)))

                # Efficiency decay based on attempts
                attempt_count = len(q_subs)
                efficiency = max(0.70, 1.0 - (attempt_count - 1) * 0.05)

                weighted_points_sum += diff_weight * score_ratio * efficiency * 100.0
                weights_sum += diff_weight

            # Bayesian smoothed mastery score
            numerator = (PRIOR_WEIGHT_K * PRIOR_MASTERY_SCORE) + weighted_points_sum
            denominator = PRIOR_WEIGHT_K + weights_sum
            mastery_score = round(numerator / denominator, 1) if denominator > 0 else 0.0
            mastery_score = min(100.0, max(0.0, mastery_score))

            level = classify_mastery_level(mastery_score)
            confidence = classify_confidence_level(q_attempted)

            # Adaptive recommended difficulty for this topic
            med_rate = (med_solved / med_att) if med_att > 0 else 0.0
            easy_rate = (easy_solved / easy_att) if easy_att > 0 else 0.0

            if mastery_score >= 80.0 or (med_att >= 2 and med_rate >= 0.75):
                rec_diff = "HARD"
            elif mastery_score >= 50.0 or (easy_att >= 2 and easy_rate >= 0.75):
                rec_diff = "MEDIUM"
            else:
                rec_diff = "EASY"

            # Check consecutive recent failures on Hard or Medium to step down
            recent_subs = subs[-3:]
            if len(recent_subs) >= 3 and all(s.status != "ACCEPTED" for s in recent_subs):
                if rec_diff == "HARD":
                    rec_diff = "MEDIUM"
                elif rec_diff == "MEDIUM":
                    rec_diff = "EASY"

            # Trend calculation (comparing last 3 submissions vs earlier)
            trend = "STABLE"
            if len(subs) >= 4:
                earlier = subs[:-3]
                recent = subs[-3:]
                earlier_rate = sum(1 for s in earlier if s.status == "ACCEPTED") / len(earlier)
                recent_rate = sum(1 for s in recent if s.status == "ACCEPTED") / len(recent)
                if (recent_rate - earlier_rate) >= 0.25:
                    trend = "IMPROVING"
                elif (earlier_rate - recent_rate) >= 0.25:
                    trend = "DECLINING"

            mastery_record = StudentTopicMastery(
                id=uuid.uuid4(),
                user_id=user_id,
                topic=topic,
                mastery_score=mastery_score,
                mastery_level=level,
                confidence_level=confidence,
                questions_attempted=q_attempted,
                questions_solved=q_solved,
                total_submissions=len(subs),
                successful_submissions=successful_subs,
                best_score=best_overall_score,
                recommended_difficulty=rec_diff,
                trend=trend,
                last_calculated_at=now,
            )
            results.append(mastery_record)

        # 4. Upsert records and history snapshots if persist=True
        if persist:
            existing_stmt = select(StudentTopicMastery).where(StudentTopicMastery.user_id == user_id)
            existing_res = await db.execute(existing_stmt)
            existing_map = {m.topic: m for m in existing_res.scalars().all()}

            for r in results:
                existing = existing_map.get(r.topic)
                score_changed = False
                if existing:
                    if abs(existing.mastery_score - r.mastery_score) >= 0.5:
                        score_changed = True
                    existing.mastery_score = r.mastery_score
                    existing.mastery_level = r.mastery_level
                    existing.confidence_level = r.confidence_level
                    existing.questions_attempted = r.questions_attempted
                    existing.questions_solved = r.questions_solved
                    existing.total_submissions = r.total_submissions
                    existing.successful_submissions = r.successful_submissions
                    existing.best_score = r.best_score
                    existing.recommended_difficulty = r.recommended_difficulty
                    existing.trend = r.trend
                    existing.last_calculated_at = now
                else:
                    score_changed = True
                    db.add(r)

                if score_changed and r.questions_attempted > 0:
                    history_entry = TopicMasteryHistory(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        topic=r.topic,
                        mastery_score=r.mastery_score,
                        mastery_level=r.mastery_level,
                        trigger_event=trigger_event,
                        recorded_at=now,
                    )
                    db.add(history_entry)

            await db.commit()

        return results

    async def get_topic_mastery_list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> TopicMasteryListResponse:
        """Returns topic-wise mastery list and overall aggregated mastery metrics."""
        masteries = await self.calculate_topic_mastery(db, user_id, persist=True)

        items: List[TopicMasteryItem] = []
        total_score_sum = 0.0
        active_count = 0

        for m in sorted(masteries, key=lambda x: x.topic):
            sr = round((m.questions_solved / m.questions_attempted * 100), 1) if m.questions_attempted > 0 else 0.0
            if m.questions_attempted > 0:
                total_score_sum += m.mastery_score
                active_count += 1

            items.append(
                TopicMasteryItem(
                    topic=m.topic,
                    mastery_score=m.mastery_score,
                    mastery_level=m.mastery_level,
                    confidence_level=m.confidence_level,
                    questions_attempted=m.questions_attempted,
                    questions_solved=m.questions_solved,
                    total_submissions=m.total_submissions,
                    successful_submissions=m.successful_submissions,
                    success_rate=sr,
                    best_score=m.best_score,
                    recommended_difficulty=m.recommended_difficulty,
                    trend=m.trend,
                    last_calculated_at=m.last_calculated_at,
                )
            )

        overall_score = round(total_score_sum / active_count, 1) if active_count > 0 else 0.0
        overall_level = classify_mastery_level(overall_score)

        if overall_score >= 80.0:
            overall_diff = "HARD"
        elif overall_score >= 50.0:
            overall_diff = "MEDIUM"
        else:
            overall_diff = "EASY"

        return TopicMasteryListResponse(
            topics=items,
            overall_mastery_score=overall_score,
            overall_mastery_level=overall_level,
            overall_recommended_difficulty=overall_diff,
            total_topics_tracked=len(items),
        )

    async def get_strengths_and_weaknesses(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> StrengthsAndWeaknessesResponse:
        """Identifies strong topics, areas requiring improvement, improving topics, and unattempted topics."""
        mastery_list_resp = await self.get_topic_mastery_list(db, user_id)
        topics = mastery_list_resp.topics

        strong: List[TopicMasteryItem] = []
        needs_improvement: List[TopicMasteryItem] = []
        improving: List[TopicMasteryItem] = []
        unattempted: List[str] = []

        for t in topics:
            if t.questions_attempted == 0:
                unattempted.append(t.topic)
            else:
                if t.mastery_score >= 65.0 or t.success_rate >= 75.0:
                    strong.append(t)
                elif t.mastery_score < 50.0 or t.success_rate < 50.0:
                    needs_improvement.append(t)

                if t.trend == "IMPROVING":
                    improving.append(t)

        insights: List[str] = []

        if strong:
            top_strong = sorted(strong, key=lambda x: x.mastery_score, reverse=True)[0]
            insights.append(
                f"Core Strength: Demonstrated solid mastery in {top_strong.topic} ({top_strong.mastery_score}%) with {top_strong.questions_solved} solved challenges."
            )
        else:
            insights.append("Focus on completing foundational challenges to establish your core topic strengths.")

        if needs_improvement:
            top_need = sorted(needs_improvement, key=lambda x: x.mastery_score)[0]
            insights.append(
                f"Target Opportunity: {top_need.topic} has {top_need.mastery_score}% mastery with {top_need.questions_attempted - top_need.questions_solved} unsolved problems. Targeted practice recommended."
            )

        if improving:
            insights.append(
                f"Positive Momentum: Upward trend identified across {len(improving)} topic(s): {', '.join(t.topic for t in improving)}."
            )

        if unattempted:
            insights.append(
                f"Unexplored Curriculum: You have not yet attempted coding questions in {len(unattempted)} topic(s), including {unattempted[0]}."
            )

        return StrengthsAndWeaknessesResponse(
            strong_topics=strong,
            needs_improvement_topics=needs_improvement,
            improving_topics=improving,
            unattempted_topics=unattempted,
            insights_summary=insights,
        )

    async def get_performance_metrics(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> StudentPerformanceResponse:
        """Returns comprehensive student performance metrics across questions, submissions, and difficulty tiers."""
        # Submissions
        sub_stmt = (
            select(Submission)
            .options(selectinload(Submission.question))
            .where(Submission.user_id == user_id)
        )
        sub_res = await db.execute(sub_stmt)
        submissions = sub_res.scalars().all()

        # Assessment attempts
        att_stmt = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user_id, AssessmentAttempt.status == "COMPLETED")
        )
        att_res = await db.execute(att_stmt)
        completed_attempts = len(att_res.scalars().all())

        diff_stats: Dict[str, Dict[str, Any]] = {
            "EASY": {"attempted": set(), "solved": set()},
            "MEDIUM": {"attempted": set(), "solved": set()},
            "HARD": {"attempted": set(), "solved": set()},
        }
        topic_counts: Dict[str, int] = {}
        all_attempted_q: Set[uuid.UUID] = set()
        all_solved_q: Set[uuid.UUID] = set()
        successful_subs = 0

        for s in submissions:
            if not s.question:
                continue
            qid = s.question_id
            diff = (s.question.difficulty or "MEDIUM").upper()
            topic = s.question.topic or "General"

            all_attempted_q.add(qid)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

            if diff in diff_stats:
                diff_stats[diff]["attempted"].add(qid)

            if s.status == "ACCEPTED":
                successful_subs += 1
                all_solved_q.add(qid)
                if diff in diff_stats:
                    diff_stats[diff]["solved"].add(qid)

        diff_breakdown: Dict[str, DifficultyBreakdownItem] = {}
        for d, data in diff_stats.items():
            att_len = len(data["attempted"])
            sol_len = len(data["solved"])
            rate = round((sol_len / att_len * 100), 1) if att_len > 0 else 0.0
            diff_breakdown[d] = DifficultyBreakdownItem(
                attempted=att_len,
                solved=sol_len,
                success_rate=rate,
            )

        total_att = len(all_attempted_q)
        total_sol = len(all_solved_q)
        overall_rate = round((total_sol / total_att * 100), 1) if total_att > 0 else 0.0

        return StudentPerformanceResponse(
            total_questions_attempted=total_att,
            total_questions_solved=total_sol,
            overall_success_rate=overall_rate,
            total_submissions=len(submissions),
            successful_submissions=successful_subs,
            difficulty_breakdown=diff_breakdown,
            assessments_completed=completed_attempts,
            topic_distribution=topic_counts,
        )

    async def get_recommended_questions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 6,
    ) -> QuestionRecommendationListResponse:
        """
        Deterministic Recommendation Engine.
        Selects uncompleted questions tailored to student topic mastery and dynamic difficulty,
        providing clear educational rationale for each recommendation.
        """
        # 1. Fetch student's solved questions
        solved_stmt = (
            select(Submission.question_id)
            .where(Submission.user_id == user_id, Submission.status == "ACCEPTED")
            .distinct()
        )
        solved_res = await db.execute(solved_stmt)
        solved_ids = set(solved_res.scalars().all())

        # 2. Fetch current topic masteries
        masteries = await self.calculate_topic_mastery(db, user_id, persist=False)
        mastery_map = {m.topic: m for m in masteries}

        # 3. Overall difficulty tier
        active_masteries = [m for m in masteries if m.questions_attempted > 0]
        avg_score = (
            sum(m.mastery_score for m in active_masteries) / len(active_masteries)
            if active_masteries
            else 0.0
        )
        if avg_score >= 80.0:
            student_overall_diff = "HARD"
        elif avg_score >= 50.0:
            student_overall_diff = "MEDIUM"
        else:
            student_overall_diff = "EASY"

        # 4. Fetch all available, non-archived questions
        q_stmt = (
            select(Question)
            .where(Question.is_archived == False)  # noqa: E712
            .order_by(Question.created_at.desc())
        )
        q_res = await db.execute(q_stmt)
        all_questions = q_res.scalars().all()

        # Filter out questions already solved
        candidates = [q for q in all_questions if q.id not in solved_ids]

        recommendations: List[QuestionRecommendationItem] = []
        used_qids: Set[uuid.UUID] = set()

        # Prioritize topics: Needs Improvement -> Unattempted -> Improving -> Others
        priority_topics = sorted(
            masteries,
            key=lambda m: (
                0 if m.questions_attempted > 0 and m.mastery_score < 50.0 else
                1 if m.questions_attempted == 0 else
                2 if m.trend == "IMPROVING" else
                3
            )
        )

        for tm in priority_topics:
            if len(recommendations) >= limit:
                break

            target_diff = tm.recommended_difficulty
            # Find matching question in this topic
            matching_q = next(
                (q for q in candidates if q.topic == tm.topic and q.difficulty.upper() == target_diff and q.id not in used_qids),
                None
            )
            if not matching_q:
                # Fallback to any difficulty in this topic
                matching_q = next(
                    (q for q in candidates if q.topic == tm.topic and q.id not in used_qids),
                    None
                )

            if matching_q:
                used_qids.add(matching_q.id)

                # Generate transparent reason
                if tm.questions_attempted == 0:
                    reason = f"Recommended as an introductory {matching_q.difficulty} challenge in {tm.topic} where you have no prior practice history."
                elif tm.mastery_score < 50.0:
                    reason = f"Recommended to strengthen your {tm.mastery_level.capitalize()} mastery ({tm.mastery_score}%) in {tm.topic} through targeted {matching_q.difficulty} practice."
                elif tm.trend == "IMPROVING":
                    reason = f"Recommended to reinforce your recent positive progress in {tm.topic}."
                else:
                    reason = f"Recommended to challenge your {tm.mastery_level.capitalize()} mastery ({tm.mastery_score}%) in {tm.topic} with {matching_q.difficulty} problem-solving."

                recommendations.append(
                    QuestionRecommendationItem(
                        question_id=matching_q.id,
                        title=matching_q.title,
                        topic=matching_q.topic,
                        difficulty=matching_q.difficulty,
                        marks=matching_q.marks,
                        time_limit_seconds=matching_q.time_limit_seconds,
                        memory_limit_mb=matching_q.memory_limit_mb,
                        recommendation_reason=reason,
                        target_mastery_level=tm.mastery_level,
                    )
                )

        # If we still have slots, fill from remaining candidate questions
        if len(recommendations) < limit:
            remaining = [q for q in candidates if q.id not in used_qids]
            for q in remaining:
                if len(recommendations) >= limit:
                    break
                used_qids.add(q.id)
                tm = mastery_map.get(q.topic)
                score_str = f" ({tm.mastery_score}%)" if tm and tm.questions_attempted > 0 else ""
                recommendations.append(
                    QuestionRecommendationItem(
                        question_id=q.id,
                        title=q.title,
                        topic=q.topic,
                        difficulty=q.difficulty,
                        marks=q.marks,
                        time_limit_seconds=q.time_limit_seconds,
                        memory_limit_mb=q.memory_limit_mb,
                        recommendation_reason=f"Recommended for broad technical practice in {q.topic}{score_str}.",
                        target_mastery_level=tm.mastery_level if tm else "BEGINNER",
                    )
                )

        now = datetime.now(timezone.utc)
        return QuestionRecommendationListResponse(
            recommendations=recommendations,
            student_overall_difficulty=student_overall_diff,
            generated_at=now,
        )

    async def get_mastery_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> MasteryHistoryResponse:
        """Returns longitudinal mastery snapshots over time for trend charts and audit tracking."""
        stmt = select(TopicMasteryHistory).where(TopicMasteryHistory.user_id == user_id)
        if topic:
            stmt = stmt.where(TopicMasteryHistory.topic == topic)
        stmt = stmt.order_by(TopicMasteryHistory.recorded_at.desc()).limit(limit)

        res = await db.execute(stmt)
        records = res.scalars().all()

        snapshots = [
            MasteryHistorySnapshot(
                id=r.id,
                topic=r.topic,
                mastery_score=r.mastery_score,
                mastery_level=r.mastery_level,
                trigger_event=r.trigger_event,
                recorded_at=r.recorded_at,
            )
            for r in records
        ]
        return MasteryHistoryResponse(history=snapshots)

    # --------------------------------------------------------------------------
    # Practice Session Execution
    # --------------------------------------------------------------------------
    async def get_practice_question(
        self,
        db: AsyncSession,
        question_id: uuid.UUID,
    ) -> QuestionPublicResponse:
        """Resolves a practice challenge with public-only test cases for interactive coding."""
        stmt = (
            select(Question)
            .options(selectinload(Question.test_cases))
            .where(Question.id == question_id, Question.is_archived == False)  # noqa: E712
        )
        res = await db.execute(stmt)
        q = res.scalar_one_or_none()
        if not q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Practice question not found or is archived.",
            )

        samples = [
            TestCasePublicResponse(
                id=tc.id,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                explanation=tc.explanation,
                marks=tc.marks,
                display_order=tc.display_order,
            )
            for tc in sorted(q.test_cases, key=lambda x: x.display_order)
            if not tc.is_hidden
        ]
        return QuestionPublicResponse(
            id=q.id,
            title=q.title,
            problem_description=q.problem_description,
            input_format=q.input_format,
            output_format=q.output_format,
            constraints=q.constraints,
            difficulty=q.difficulty,
            topic=q.topic,
            marks=q.marks,
            time_limit_seconds=q.time_limit_seconds,
            memory_limit_mb=q.memory_limit_mb,
            display_order=q.display_order,
            sample_test_cases=samples,
        )

    async def run_practice_sample(
        self,
        db: AsyncSession,
        user: User,
        question_id: uuid.UUID,
        language_id: uuid.UUID,
        source_code: str,
    ) -> SubmissionResponse:
        """Executes student code against public sample test cases without persisting formal score."""
        payload = SubmissionCreate(
            question_id=question_id,
            programming_language_id=language_id,
            source_code=source_code,
            assessment_id=None,
        )
        return await evaluation_service.evaluate_submission(
            db=db,
            user=user,
            data=payload,
            run_mode="SAMPLE_ONLY",
        )

    async def submit_practice_solution(
        self,
        db: AsyncSession,
        user: User,
        question_id: uuid.UUID,
        language_id: uuid.UUID,
        source_code: str,
    ) -> SubmissionResponse:
        """
        Executes full evaluation suite, persists Submission record, generates AST & AI feedback,
        and triggers immediate topic mastery recalculation and history snapshot.
        """
        payload = SubmissionCreate(
            question_id=question_id,
            programming_language_id=language_id,
            source_code=source_code,
            assessment_id=None,
        )
        eval_result = await evaluation_service.evaluate_submission(
            db=db,
            user=user,
            data=payload,
            run_mode="FULL",
        )

        # Trigger real-time mastery recalculation
        try:
            await self.calculate_topic_mastery(
                db=db,
                user_id=user.id,
                persist=True,
                trigger_event="PRACTICE_SUBMISSION",
            )
        except Exception as e:
            logger.error("Failed to update mastery on practice submission: %s", e)

        return eval_result

    async def get_topics_catalog(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> TopicCatalogResponse:
        """Returns catalog of all syllabus topics with student mastery and question statistics."""
        mastery_list = await self.get_topic_mastery_list(db=db, user_id=user_id)
        mastery_map = {m.topic: m for m in mastery_list.topics}

        stmt = (
            select(Question.topic, func.count(Question.id))
            .where(Question.is_archived == False, Question.assessment_id.is_(None))
            .group_by(Question.topic)
        )
        res = await db.execute(stmt)
        q_count_map = {row[0]: row[1] for row in res.all()}

        items = []
        known_topics = list(TOPIC_DESCRIPTIONS.keys())
        all_topics = known_topics + [t for t in q_count_map.keys() if t not in known_topics]

        for topic in all_topics:
            count = q_count_map.get(topic, 0)
            if count == 0 and topic not in TOPIC_DESCRIPTIONS:
                continue
            desc = TOPIC_DESCRIPTIONS.get(topic, f"Master algorithmic challenges and key concepts in {topic}.")
            m = mastery_map.get(topic)
            items.append(
                TopicCatalogItem(
                    topic=topic,
                    description=desc,
                    question_count=count,
                    questions_solved=m.questions_solved if m else 0,
                    questions_attempted=m.questions_attempted if m else 0,
                    mastery_score=m.mastery_score if m else 0.0,
                    mastery_level=m.mastery_level if m else "BEGINNER",
                    confidence_level=m.confidence_level if m else "LOW",
                    recommended_difficulty=m.recommended_difficulty if m else "EASY",
                )
            )

        return TopicCatalogResponse(topics=items)

    async def get_topic_practice_details(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        topic_name: str,
    ) -> TopicPracticeDetailResponse:
        """Returns detailed topic view: available questions, solved state, mastery stats, and recommendations."""
        stmt = (
            select(Question)
            .options(selectinload(Question.test_cases))
            .where(
                Question.topic == topic_name,
                Question.is_archived == False,
                Question.assessment_id.is_(None),
            )
            .order_by(Question.display_order, Question.created_at.asc())
        )
        res = await db.execute(stmt)
        questions = res.scalars().all()

        q_ids = [q.id for q in questions]
        solved_set: Set[uuid.UUID] = set()
        attempts_map: Dict[uuid.UUID, int] = {}
        if q_ids:
            sub_stmt = (
                select(Submission.question_id, Submission.status)
                .where(Submission.user_id == user_id, Submission.question_id.in_(q_ids))
            )
            sub_res = await db.execute(sub_stmt)
            for row in sub_res.all():
                qid, sub_status = row[0], row[1]
                attempts_map[qid] = attempts_map.get(qid, 0) + 1
                if sub_status == "ACCEPTED":
                    solved_set.add(qid)

        mastery_list = await self.get_topic_mastery_list(db=db, user_id=user_id)
        m = next((item for item in mastery_list.topics if item.topic == topic_name), None)

        m_score = m.mastery_score if m else 0.0
        m_level = m.mastery_level if m else "BEGINNER"
        m_conf = m.confidence_level if m else "LOW"
        m_rec_diff = m.recommended_difficulty if m else "EASY"
        m_att = m.questions_attempted if m else 0
        m_solved = m.questions_solved if m else 0

        q_items = []
        for q in questions:
            sample_count = sum(1 for tc in q.test_cases if not tc.is_hidden)
            is_s = q.id in solved_set
            att_cnt = attempts_map.get(q.id, 0)
            q_items.append(
                TopicPracticeQuestionItem(
                    id=q.id,
                    title=q.title,
                    difficulty=q.difficulty,
                    marks=q.marks,
                    time_limit_seconds=q.time_limit_seconds,
                    memory_limit_mb=q.memory_limit_mb,
                    sample_test_case_count=sample_count,
                    is_solved=is_s,
                    attempts_count=att_cnt,
                    starter_code=q.starter_code,
                )
            )

        unsolved_rec = [q for q in q_items if not q.is_solved and q.difficulty.upper() == m_rec_diff.upper()]
        unsolved_any = [q for q in q_items if not q.is_solved]
        recommended_q = unsolved_rec[0] if unsolved_rec else (unsolved_any[0] if unsolved_any else (q_items[0] if q_items else None))

        desc = TOPIC_DESCRIPTIONS.get(topic_name, f"Master foundational and advanced challenges in {topic_name}.")

        return TopicPracticeDetailResponse(
            topic=topic_name,
            description=desc,
            mastery_score=m_score,
            mastery_level=m_level,
            confidence_level=m_conf,
            recommended_difficulty=m_rec_diff,
            questions_attempted=m_att,
            questions_solved=m_solved,
            total_questions=len(q_items),
            recommended_question=recommended_q,
            questions=q_items,
        )


adaptive_service = AdaptiveService()
