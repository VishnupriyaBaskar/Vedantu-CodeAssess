r"""
Analytics & Instructor Reporting Service
Project: Vedantu Online Coding Assessment Platform (Phase 8)
Workspace: E:\VedantuCodingPlatform_New

Aggregates real-time KPIs, cohort distributions, candidate performance audit reports,
question bank quality metrics, and RFC 4180 compliant CSV exports with strict candidate isolation.
"""

import csv
from datetime import datetime, timezone
import io
import logging
from typing import Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_candidate import AssessmentCandidate
from app.models.proctoring_alert import ProctoringAlert
from app.models.proctoring_event import ProctoringEvent
from app.models.proctoring_session import ProctoringSession
from app.models.question import Question
from app.models.role import Role, UserRole
from app.models.student_topic_mastery import StudentTopicMastery
from app.models.submission import Submission
from app.models.submission_test_case_result import SubmissionTestCaseResult
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.adaptive import DifficultyBreakdownItem, TopicMasteryItem
from app.schemas.analytics import (
    AssessmentAnalyticsResponse,
    CandidatePerformanceDetailResponse,
    CandidateSubmissionSummaryItem,
    CandidateSummaryItem,
    CohortAnalyticsResponse,
    DifficultyPerformanceItem,
    InstructorOverviewKPIs,
    QuestionPerformanceItem,
    ScoreBucket,
    TopicPerformanceItem,
)

logger = logging.getLogger("analytics_service")


class AnalyticsService:
    """
    Production-grade analytics aggregation service for instructors and administrators.
    """

    async def get_instructor_overview(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> InstructorOverviewKPIs:
        """
        Returns high-level operational KPIs for the instructor dashboard.
        """
        # 1. Total Candidates (users with STUDENT role)
        student_role_stmt = select(Role.id).where(Role.name == "STUDENT")
        role_res = await db.execute(student_role_stmt)
        student_role_id = role_res.scalar_one_or_none()

        if student_role_id:
            user_count_stmt = select(func.count(distinct(UserRole.user_id))).where(
                UserRole.role_id == student_role_id
            )
        else:
            user_count_stmt = select(func.count(User.id))
        total_candidates = (await db.execute(user_count_stmt)).scalar() or 0

        # 2. Total & Published Assessments
        total_assessments_stmt = select(func.count(Assessment.id))
        total_assessments = (await db.execute(total_assessments_stmt)).scalar() or 0

        published_stmt = select(func.count(Assessment.id)).where(
            Assessment.status == "PUBLISHED"
        )
        published_assessments = (await db.execute(published_stmt)).scalar() or 0

        # 3. Assessment Attempts (Completed vs Active)
        completed_stmt = select(func.count(AssessmentAttempt.id)).where(
            AssessmentAttempt.status == "COMPLETED"
        )
        completed_attempts = (await db.execute(completed_stmt)).scalar() or 0

        active_stmt = select(func.count(AssessmentAttempt.id)).where(
            AssessmentAttempt.status == "IN_PROGRESS"
        )
        active_attempts = (await db.execute(active_stmt)).scalar() or 0

        # 4. Average Score & Pass Rate of Completed Attempts
        score_avg_stmt = select(func.avg(AssessmentAttempt.percentage)).where(
            AssessmentAttempt.status == "COMPLETED"
        )
        avg_score_res = (await db.execute(score_avg_stmt)).scalar()
        average_score_pct = round(float(avg_score_res or 0.0), 2)

        passed_stmt = select(func.count(AssessmentAttempt.id)).where(
            AssessmentAttempt.status == "COMPLETED",
            AssessmentAttempt.is_passed.is_(True),
        )
        passed_count = (await db.execute(passed_stmt)).scalar() or 0
        pass_percentage = (
            round((passed_count / completed_attempts * 100.0), 2)
            if completed_attempts > 0
            else 0.0
        )

        total_started = completed_attempts + active_attempts
        completion_percentage = (
            round((completed_attempts / total_started * 100.0), 2)
            if total_started > 0
            else 0.0
        )

        # 5. Question Bank & Submissions Volume
        q_count_stmt = select(func.count(Question.id)).where(
            Question.is_archived.is_(False)
        )
        total_questions = (await db.execute(q_count_stmt)).scalar() or 0

        sub_count_stmt = select(func.count(Submission.id))
        total_submissions = (await db.execute(sub_count_stmt)).scalar() or 0

        return InstructorOverviewKPIs(
            total_candidates=total_candidates,
            total_assessments=total_assessments,
            published_assessments=published_assessments,
            completed_attempts=completed_attempts,
            active_attempts=active_attempts,
            average_score_pct=average_score_pct,
            pass_percentage=pass_percentage,
            completion_percentage=completion_percentage,
            total_questions=total_questions,
            total_submissions=total_submissions,
        )

    async def get_assessment_analytics(
        self,
        assessment_id: uuid.UUID,
        db: AsyncSession,
        current_user: User,
    ) -> AssessmentAnalyticsResponse:
        """
        Calculates detailed assessment analytics including candidate score distributions,
        topic/difficulty breakdowns, candidate ranking table, and proctoring metrics.
        """
        # Fetch Assessment
        stmt = (
            select(Assessment)
            .options(
                selectinload(Assessment.questions).selectinload(Question.test_cases),
                selectinload(Assessment.candidates),
            )
            .where(Assessment.id == assessment_id)
        )
        res = await db.execute(stmt)
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found.",
            )

        total_enrolled = len(assessment.candidates)

        # Fetch Attempts
        attempts_stmt = (
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.user))
            .where(AssessmentAttempt.assessment_id == assessment_id)
            .order_by(desc(AssessmentAttempt.percentage))
        )
        attempts = (await db.execute(attempts_stmt)).scalars().all()

        total_attempts = len(attempts)
        completed = [a for a in attempts if a.status == "COMPLETED"]
        active = [a for a in attempts if a.status == "IN_PROGRESS"]

        completed_count = len(completed)
        active_count = len(active)

        if completed_count > 0:
            scores = [a.total_score for a in completed]
            pcts = [a.percentage for a in completed]
            average_score = round(sum(scores) / completed_count, 2)
            average_score_pct = round(sum(pcts) / completed_count, 2)
            highest_score = round(max(scores), 2)
            lowest_score = round(min(scores), 2)
            pass_count = sum(1 for a in completed if a.is_passed)
            fail_count = completed_count - pass_count
            pass_percentage = round((pass_count / completed_count * 100.0), 2)
        else:
            average_score = 0.0
            average_score_pct = 0.0
            highest_score = 0.0
            lowest_score = 0.0
            pass_count = 0
            fail_count = 0
            pass_percentage = 0.0

        completion_percentage = (
            round((completed_count / total_attempts * 100.0), 2)
            if total_attempts > 0
            else 0.0
        )

        # Score distribution (5 standard buckets)
        buckets = [
            ("0-20%", 0.0, 20.0),
            ("21-40%", 20.0001, 40.0),
            ("41-60%", 40.0001, 60.0),
            ("61-80%", 60.0001, 80.0),
            ("81-100%", 80.0001, 100.0),
        ]
        score_distribution: List[ScoreBucket] = []
        for label, low, high in buckets:
            b_count = sum(1 for a in completed if low <= a.percentage <= high)
            b_pct = (
                round((b_count / completed_count * 100.0), 2)
                if completed_count > 0
                else 0.0
            )
            score_distribution.append(
                ScoreBucket(range_label=label, count=b_count, percentage=b_pct)
            )

        # Proctoring Metrics (Phase 7 integration)
        proctoring_sessions_stmt = select(func.count(ProctoringSession.id)).where(
            ProctoringSession.assessment_id == assessment_id
        )
        monitored_sessions = (await db.execute(proctoring_sessions_stmt)).scalar() or 0

        proctoring_events_stmt = select(func.count(ProctoringEvent.id)).where(
            ProctoringEvent.assessment_id == assessment_id
        )
        total_events = (await db.execute(proctoring_events_stmt)).scalar() or 0

        alerts_stmt = select(ProctoringAlert).where(
            ProctoringAlert.assessment_id == assessment_id
        )
        alerts = (await db.execute(alerts_stmt)).scalars().all()
        total_alerts = len(alerts)
        pending_alerts = sum(1 for a in alerts if a.review_status == "PENDING")
        high_severity_alerts = sum(1 for a in alerts if a.severity == "HIGH")

        alert_count_by_attempt: Dict[uuid.UUID, int] = {}
        for alert in alerts:
            alert_count_by_attempt[alert.assessment_attempt_id] = (
                alert_count_by_attempt.get(alert.assessment_attempt_id, 0) + 1
            )

        # Candidate Summaries
        candidate_items: List[CandidateSummaryItem] = []
        for attempt in attempts:
            user = attempt.user
            candidate_items.append(
                CandidateSummaryItem(
                    candidate_id=user.id if user else attempt.user_id,
                    full_name=user.full_name if user else "Candidate",
                    email=user.email if user else "",
                    attempt_id=attempt.id,
                    status=attempt.status,
                    score=attempt.total_score,
                    max_score=float(assessment.total_marks),
                    score_pct=attempt.percentage,
                    passed=attempt.is_passed,
                    started_at=attempt.started_at,
                    completed_at=attempt.submitted_at,
                    proctoring_alerts_count=alert_count_by_attempt.get(attempt.id, 0),
                )
            )

        # Topic & Difficulty breakdown
        # Aggregate submissions made in this assessment
        subs_stmt = select(Submission).where(Submission.assessment_id == assessment_id)
        subs = (await db.execute(subs_stmt)).scalars().all()
        subs_by_question: Dict[uuid.UUID, List[Submission]] = {}
        for s in subs:
            subs_by_question.setdefault(s.question_id, []).append(s)

        topic_stats: Dict[str, Dict[str, Any]] = {}
        diff_stats: Dict[str, Dict[str, Any]] = {}

        for q in assessment.questions:
            q_subs = subs_by_question.get(q.id, [])
            q_attempts = len(q_subs)
            q_avg_score = (
                (sum(s.score for s in q_subs) / q_attempts / q.marks * 100.0)
                if q_attempts > 0 and q.marks > 0
                else 0.0
            )

            # Topic
            t_data = topic_stats.setdefault(
                q.topic, {"questions": 0, "attempts": 0, "score_sum": 0.0}
            )
            t_data["questions"] += 1
            t_data["attempts"] += q_attempts
            t_data["score_sum"] += q_avg_score

            # Difficulty
            d_data = diff_stats.setdefault(
                q.difficulty, {"questions": 0, "attempts": 0, "score_sum": 0.0}
            )
            d_data["questions"] += 1
            d_data["attempts"] += q_attempts
            d_data["score_sum"] += q_avg_score

        topic_breakdown = [
            TopicPerformanceItem(
                topic=top,
                total_questions=val["questions"],
                total_attempts=val["attempts"],
                average_score_pct=round(val["score_sum"] / val["questions"], 2)
                if val["questions"] > 0
                else 0.0,
            )
            for top, val in sorted(topic_stats.items())
        ]

        difficulty_breakdown = [
            DifficultyPerformanceItem(
                difficulty=diff,
                total_questions=val["questions"],
                total_attempts=val["attempts"],
                average_score_pct=round(val["score_sum"] / val["questions"], 2)
                if val["questions"] > 0
                else 0.0,
            )
            for diff, val in sorted(diff_stats.items())
        ]

        return AssessmentAnalyticsResponse(
            assessment_id=assessment.id,
            title=assessment.title,
            passing_score=assessment.passing_marks,
            total_marks=assessment.total_marks,
            total_enrolled=total_enrolled,
            total_attempts=total_attempts,
            completed_attempts=completed_count,
            active_attempts=active_count,
            average_score=average_score,
            average_score_pct=average_score_pct,
            highest_score=highest_score,
            lowest_score=lowest_score,
            pass_count=pass_count,
            fail_count=fail_count,
            pass_percentage=pass_percentage,
            completion_percentage=completion_percentage,
            score_distribution=score_distribution,
            topic_breakdown=topic_breakdown,
            difficulty_breakdown=difficulty_breakdown,
            candidates=candidate_items,
            proctoring_monitored_sessions=monitored_sessions,
            proctoring_total_events=total_events,
            proctoring_total_alerts=total_alerts,
            proctoring_pending_alerts=pending_alerts,
            proctoring_high_severity_alerts=high_severity_alerts,
        )

    async def get_cohort_analytics(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> CohortAnalyticsResponse:
        """
        Aggregates cohort-level insights across students, assessing systemic strengths,
        weaknesses, frequently failed topics, score distribution, and outlier identification.
        """
        # Total Candidates
        student_role_stmt = select(Role.id).where(Role.name == "STUDENT")
        role_res = await db.execute(student_role_stmt)
        student_role_id = role_res.scalar_one_or_none()

        if student_role_id:
            user_count_stmt = select(func.count(distinct(UserRole.user_id))).where(
                UserRole.role_id == student_role_id
            )
        else:
            user_count_stmt = select(func.count(User.id))
        total_candidates = (await db.execute(user_count_stmt)).scalar() or 0

        # Active Candidates (who have submitted code or attempted an assessment)
        active_sub_users = select(Submission.user_id)
        active_att_users = select(AssessmentAttempt.user_id)
        active_combined = active_sub_users.union(active_att_users).subquery()
        active_candidates_stmt = select(func.count(distinct(active_combined.c.user_id)))
        active_candidates = (await db.execute(active_candidates_stmt)).scalar() or 0

        # Completed attempts and cohort mean
        completed_stmt = (
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.user))
            .where(AssessmentAttempt.status == "COMPLETED")
        )
        completed_attempts = (await db.execute(completed_stmt)).scalars().all()
        completed_count = len(completed_attempts)

        if completed_count > 0:
            avg_cohort_score = round(
                sum(a.percentage for a in completed_attempts) / completed_count, 2
            )
        else:
            avg_cohort_score = 0.0

        # Score distribution
        buckets = [
            ("0-20%", 0.0, 20.0),
            ("21-40%", 20.0001, 40.0),
            ("41-60%", 40.0001, 60.0),
            ("61-80%", 60.0001, 80.0),
            ("81-100%", 80.0001, 100.0),
        ]
        score_distribution: List[ScoreBucket] = []
        for label, low, high in buckets:
            b_count = sum(1 for a in completed_attempts if low <= a.percentage <= high)
            b_pct = (
                round((b_count / completed_count * 100.0), 2)
                if completed_count > 0
                else 0.0
            )
            score_distribution.append(
                ScoreBucket(range_label=label, count=b_count, percentage=b_pct)
            )

        # Topic proficiencies from Phase 6 StudentTopicMastery
        mastery_stmt = select(
            StudentTopicMastery.topic,
            func.count(distinct(StudentTopicMastery.user_id)),
            func.avg(StudentTopicMastery.mastery_score),
            func.sum(StudentTopicMastery.questions_attempted),
        ).group_by(StudentTopicMastery.topic)
        mastery_rows = (await db.execute(mastery_stmt)).all()

        topic_proficiencies: List[TopicPerformanceItem] = []
        frequently_failed_topics: List[str] = []

        for row in mastery_rows:
            topic_name = row[0]
            avg_mastery = round(float(row[2] or 0.0), 2)
            total_attempts_on_topic = int(row[3] or 0)
            topic_proficiencies.append(
                TopicPerformanceItem(
                    topic=topic_name,
                    total_questions=0,
                    total_attempts=total_attempts_on_topic,
                    average_score_pct=avg_mastery,
                )
            )
            if avg_mastery < 50.0:
                frequently_failed_topics.append(topic_name)

        topic_proficiencies.sort(key=lambda x: x.average_score_pct, reverse=True)
        frequently_failed_topics.sort()

        # Difficulty proficiencies from submissions
        diff_stmt = (
            select(
                Question.difficulty,
                func.count(Submission.id),
                func.avg(Submission.score),
                func.avg(Question.marks),
            )
            .join(Question, Submission.question_id == Question.id)
            .group_by(Question.difficulty)
        )
        diff_rows = (await db.execute(diff_stmt)).all()
        difficulty_proficiencies: List[DifficultyPerformanceItem] = []
        for row in diff_rows:
            diff_name = row[0]
            att_cnt = int(row[1] or 0)
            avg_sc = float(row[2] or 0.0)
            avg_mk = float(row[3] or 10.0)
            avg_pct = round((avg_sc / avg_mk * 100.0), 2) if avg_mk > 0 else 0.0
            difficulty_proficiencies.append(
                DifficultyPerformanceItem(
                    difficulty=diff_name,
                    total_questions=0,
                    total_attempts=att_cnt,
                    average_score_pct=avg_pct,
                )
            )
        difficulty_proficiencies.sort(key=lambda x: x.difficulty)

        # Candidate aggregate performance (for top performers & at-risk identification)
        user_attempts_map: Dict[uuid.UUID, List[AssessmentAttempt]] = {}
        for a in completed_attempts:
            user_attempts_map.setdefault(a.user_id, []).append(a)

        candidate_aggregates: List[Tuple[User, float, int]] = []
        for u_id, att_list in user_attempts_map.items():
            first_att = att_list[0]
            if first_att.user:
                mean_pct = sum(x.percentage for x in att_list) / len(att_list)
                candidate_aggregates.append((first_att.user, mean_pct, len(att_list)))

        candidate_aggregates.sort(key=lambda x: x[1], reverse=True)

        top_performers = [
            CandidateSummaryItem(
                candidate_id=u.id,
                full_name=u.full_name,
                email=u.email,
                score_pct=round(pct, 2),
                passed=pct >= 40.0,
            )
            for u, pct, _ in candidate_aggregates[:5]
        ]

        at_risk_candidates = [
            CandidateSummaryItem(
                candidate_id=u.id,
                full_name=u.full_name,
                email=u.email,
                score_pct=round(pct, 2),
                passed=False,
            )
            for u, pct, _ in reversed(candidate_aggregates)
            if pct < 40.0
        ][:5]

        return CohortAnalyticsResponse(
            total_candidates=total_candidates,
            active_candidates=active_candidates,
            completed_attempts=completed_count,
            average_cohort_score_pct=avg_cohort_score,
            topic_proficiencies=topic_proficiencies,
            difficulty_proficiencies=difficulty_proficiencies,
            frequently_failed_topics=frequently_failed_topics,
            score_distribution=score_distribution,
            top_performers=top_performers,
            at_risk_candidates=at_risk_candidates,
        )

    async def get_candidate_report(
        self,
        candidate_id: uuid.UUID,
        db: AsyncSession,
        current_user: User,
    ) -> CandidatePerformanceDetailResponse:
        """
        Generates an individual candidate's comprehensive performance audit report.
        Strictly isolated: hidden test cases are NEVER exposed.
        Reuses Phase 6 StudentTopicMastery to prevent score divergence.
        """
        # Verify Candidate
        candidate_stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == candidate_id)
        )
        res = await db.execute(candidate_stmt)
        candidate = res.scalar_one_or_none()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found.",
            )

        # Assessment Attempts
        attempts_stmt = (
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.assessment))
            .where(AssessmentAttempt.user_id == candidate_id)
            .order_by(desc(AssessmentAttempt.started_at))
        )
        attempts = (await db.execute(attempts_stmt)).scalars().all()
        attempted_count = len(attempts)
        completed = [a for a in attempts if a.status == "COMPLETED"]
        completed_count = len(completed)

        if completed_count > 0:
            avg_score_pct = round(
                sum(a.percentage for a in completed) / completed_count, 2
            )
            best_score_pct = round(max(a.percentage for a in completed), 2)
        else:
            avg_score_pct = 0.0
            best_score_pct = 0.0

        # Proctoring alert counts per attempt
        attempt_ids = [a.id for a in attempts]
        alert_count_by_attempt: Dict[uuid.UUID, int] = {}
        if attempt_ids:
            alerts_stmt = select(
                ProctoringAlert.assessment_attempt_id,
                func.count(ProctoringAlert.id),
            ).where(ProctoringAlert.assessment_attempt_id.in_(attempt_ids)).group_by(
                ProctoringAlert.assessment_attempt_id
            )
            for row in (await db.execute(alerts_stmt)).all():
                alert_count_by_attempt[row[0]] = int(row[1] or 0)

        attempt_items = [
            CandidateSummaryItem(
                candidate_id=candidate.id,
                full_name=candidate.full_name,
                email=candidate.email,
                attempt_id=a.id,
                status=a.status,
                score=a.total_score,
                max_score=float(a.assessment.total_marks) if a.assessment else 100.0,
                score_pct=a.percentage,
                passed=a.is_passed,
                started_at=a.started_at,
                completed_at=a.submitted_at,
                proctoring_alerts_count=alert_count_by_attempt.get(a.id, 0),
            )
            for a in attempts
        ]

        # Phase 6 Topic Mastery
        mastery_stmt = (
            select(StudentTopicMastery)
            .where(StudentTopicMastery.user_id == candidate_id)
            .order_by(desc(StudentTopicMastery.mastery_score))
        )
        mastery_records = (await db.execute(mastery_stmt)).scalars().all()

        topic_mastery_items: List[TopicMasteryItem] = []
        strengths: List[str] = []
        weaknesses: List[str] = []

        for m in mastery_records:
            succ_rate = (
                round((m.questions_solved / m.questions_attempted * 100.0), 2)
                if m.questions_attempted > 0
                else 0.0
            )
            topic_mastery_items.append(
                TopicMasteryItem(
                    topic=m.topic,
                    mastery_score=m.mastery_score,
                    mastery_level=m.mastery_level,
                    confidence_level=m.confidence_level,
                    questions_attempted=m.questions_attempted,
                    questions_solved=m.questions_solved,
                    total_submissions=m.total_submissions,
                    successful_submissions=m.successful_submissions,
                    success_rate=succ_rate,
                    best_score=m.best_score,
                    recommended_difficulty=m.recommended_difficulty,
                    trend=m.trend,
                    last_calculated_at=m.last_calculated_at,
                )
            )
            if m.mastery_score >= 70.0:
                strengths.append(m.topic)
            elif m.mastery_score < 50.0:
                weaknesses.append(m.topic)

        # Submissions & Difficulty Breakdown
        subs_stmt = (
            select(Submission)
            .options(
                selectinload(Submission.question),
                selectinload(Submission.programming_language),
                selectinload(Submission.test_case_results),
                selectinload(Submission.evaluation),
            )
            .where(Submission.user_id == candidate_id)
            .order_by(desc(Submission.created_at))
            .limit(100)
        )
        submissions = (await db.execute(subs_stmt)).scalars().all()

        diff_map: Dict[str, Dict[str, Any]] = {
            "EASY": {"attempted": set(), "solved": set()},
            "MEDIUM": {"attempted": set(), "solved": set()},
            "HARD": {"attempted": set(), "solved": set()},
        }

        submission_items: List[CandidateSubmissionSummaryItem] = []
        for sub in submissions:
            q = sub.question
            diff = q.difficulty.upper() if q else "MEDIUM"
            if diff in diff_map:
                diff_map[diff]["attempted"].add(sub.question_id)
                if sub.status == "ACCEPTED" or (q and sub.score >= q.marks):
                    diff_map[diff]["solved"].add(sub.question_id)

            passed_tests = sum(
                1 for tc in sub.test_case_results if tc.status == "PASSED"
            )
            total_tests = len(sub.test_case_results)

            static_warns = 0
            static_sum = None
            ai_score = None
            if sub.evaluation:
                if sub.evaluation.static_analysis:
                    static_warns = len(
                        sub.evaluation.static_analysis.get("findings", [])
                    )
                    static_sum = f"{static_warns} findings, complexity {sub.evaluation.static_analysis.get('cyclomatic_complexity', 'N/A')}"
                if sub.evaluation.ai_feedback:
                    ai_score = sub.evaluation.ai_feedback.get("code_quality_score")

            submission_items.append(
                CandidateSubmissionSummaryItem(
                    submission_id=sub.id,
                    question_id=sub.question_id,
                    question_title=q.title if q else "Question",
                    topic=q.topic if q else "General",
                    difficulty=diff,
                    language=sub.programming_language.name
                    if sub.programming_language
                    else "Unknown",
                    status=sub.status,
                    execution_time_ms=int(sub.execution_time * 1000)
                    if sub.execution_time
                    else None,
                    memory_kb=sub.memory_usage,
                    test_cases_passed=passed_tests,
                    total_test_cases=total_tests,
                    score=int(sub.score),
                    max_score=q.marks if q else 10,
                    static_warnings_count=static_warns,
                    static_summary=static_sum,
                    ai_quality_score=ai_score,
                    submitted_at=sub.created_at,
                )
            )

        difficulty_breakdown = {
            diff_key: DifficultyBreakdownItem(
                attempted=len(diff_map[diff_key]["attempted"]),
                solved=len(diff_map[diff_key]["solved"]),
                success_rate=round(
                    len(diff_map[diff_key]["solved"])
                    / len(diff_map[diff_key]["attempted"])
                    * 100.0,
                    2,
                )
                if diff_map[diff_key]["attempted"]
                else 0.0,
            )
            for diff_key in ["EASY", "MEDIUM", "HARD"]
        }

        return CandidatePerformanceDetailResponse(
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            joined_at=candidate.created_at,
            assessments_attempted=attempted_count,
            assessments_completed=completed_count,
            average_score_pct=avg_score_pct,
            best_score_pct=best_score_pct,
            topic_mastery=topic_mastery_items,
            strengths=strengths,
            weaknesses=weaknesses,
            difficulty_breakdown=difficulty_breakdown,
            submissions=submission_items,
            assessment_attempts=attempt_items,
        )

    async def get_questions_performance(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> List[QuestionPerformanceItem]:
        """
        Retrieves question bank items with aggregated quality metrics, success rates,
        and test case breakdown across sample, functional, and edge cases.
        """
        stmt = (
            select(Question)
            .options(
                selectinload(Question.test_cases),
                selectinload(Question.submissions),
            )
            .order_by(Question.display_order, desc(Question.created_at))
        )
        questions = (await db.execute(stmt)).scalars().all()

        items: List[QuestionPerformanceItem] = []
        for q in questions:
            total_attempts = len(q.submissions)
            solved_count = sum(
                1
                for s in q.submissions
                if s.status == "ACCEPTED" or s.score >= q.marks
            )
            success_rate = (
                round((solved_count / total_attempts * 100.0), 2)
                if total_attempts > 0
                else 0.0
            )
            avg_score = (
                round(sum(s.score for s in q.submissions) / total_attempts, 2)
                if total_attempts > 0
                else 0.0
            )

            sample_cnt = sum(
                1 for tc in q.test_cases if tc.category == "SAMPLE" or not tc.is_hidden
            )
            functional_cnt = sum(
                1
                for tc in q.test_cases
                if tc.category == "FUNCTIONAL" and tc.is_hidden
            )
            edge_cnt = sum(1 for tc in q.test_cases if tc.category == "EDGE_CASE")
            total_test_marks = sum(tc.marks for tc in q.test_cases)

            items.append(
                QuestionPerformanceItem(
                    question_id=q.id,
                    title=q.title,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    marks=q.marks,
                    tags=q.tags,
                    is_archived=q.is_archived,
                    total_attempts=total_attempts,
                    solved_count=solved_count,
                    success_rate=success_rate,
                    average_score=avg_score,
                    sample_test_count=sample_cnt,
                    functional_test_count=functional_cnt,
                    edge_test_count=edge_cnt,
                    total_test_marks=total_test_marks,
                    created_at=q.created_at,
                )
            )

        return items

    async def export_assessment_results_csv(
        self,
        assessment_id: uuid.UUID,
        db: AsyncSession,
        current_user: User,
    ) -> str:
        """
        Exports assessment candidate results in standard RFC 4180 CSV format.
        """
        analytics = await self.get_assessment_analytics(
            assessment_id, db, current_user
        )

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(
            [
                "Candidate ID",
                "Full Name",
                "Email",
                "Status",
                "Total Score",
                "Max Marks",
                "Percentage",
                "Passed",
                "Started At",
                "Completed At",
                "Proctoring Alerts",
            ]
        )

        for c in analytics.candidates:
            writer.writerow(
                [
                    str(c.candidate_id),
                    c.full_name,
                    c.email,
                    c.status or "NOT_STARTED",
                    f"{c.score:.2f}" if c.score is not None else "0.00",
                    f"{c.max_score:.2f}" if c.max_score is not None else "100.00",
                    f"{c.score_pct:.2f}%" if c.score_pct is not None else "0.00%",
                    "YES" if c.passed else "NO",
                    c.started_at.isoformat() if c.started_at else "",
                    c.completed_at.isoformat() if c.completed_at else "",
                    c.proctoring_alerts_count,
                ]
            )

        return output.getvalue()

    async def export_candidate_report_csv(
        self,
        candidate_id: uuid.UUID,
        db: AsyncSession,
        current_user: User,
    ) -> str:
        """
        Exports an individual candidate's report in CSV format.
        """
        report = await self.get_candidate_report(candidate_id, db, current_user)

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Section 1: Candidate Overview
        writer.writerow(["=== CANDIDATE OVERVIEW ==="])
        writer.writerow(["Candidate ID", str(report.candidate_id)])
        writer.writerow(["Full Name", report.full_name])
        writer.writerow(["Email", report.email])
        writer.writerow(["Joined At", report.joined_at.isoformat()])
        writer.writerow(["Assessments Attempted", report.assessments_attempted])
        writer.writerow(["Assessments Completed", report.assessments_completed])
        writer.writerow(["Average Score (%)", f"{report.average_score_pct:.2f}%"])
        writer.writerow(["Best Score (%)", f"{report.best_score_pct:.2f}%"])
        writer.writerow(["Strengths", ", ".join(report.strengths) or "None"])
        writer.writerow(["Weaknesses", ", ".join(report.weaknesses) or "None"])
        writer.writerow([])

        # Section 2: Topic Mastery
        writer.writerow(["=== TOPIC MASTERY ==="])
        writer.writerow(
            [
                "Topic",
                "Mastery Score",
                "Mastery Level",
                "Confidence",
                "Questions Attempted",
                "Questions Solved",
                "Success Rate",
                "Trend",
            ]
        )
        for tm in report.topic_mastery:
            writer.writerow(
                [
                    tm.topic,
                    f"{tm.mastery_score:.1f}",
                    tm.mastery_level,
                    tm.confidence_level,
                    tm.questions_attempted,
                    tm.questions_solved,
                    f"{tm.success_rate:.1f}%",
                    tm.trend,
                ]
            )
        writer.writerow([])

        # Section 3: Submissions
        writer.writerow(["=== CODE SUBMISSION HISTORY ==="])
        writer.writerow(
            [
                "Submission ID",
                "Question Title",
                "Topic",
                "Difficulty",
                "Language",
                "Status",
                "Score",
                "Max Score",
                "Test Cases Passed",
                "Total Test Cases",
                "Static Warnings",
                "AI Quality Score",
                "Submitted At",
            ]
        )
        for s in report.submissions:
            writer.writerow(
                [
                    str(s.submission_id),
                    s.question_title,
                    s.topic,
                    s.difficulty,
                    s.language,
                    s.status,
                    s.score,
                    s.max_score,
                    s.test_cases_passed,
                    s.total_test_cases,
                    s.static_warnings_count,
                    s.ai_quality_score if s.ai_quality_score is not None else "N/A",
                    s.submitted_at.isoformat(),
                ]
            )

        return output.getvalue()

    async def export_questions_performance_csv(
        self,
        db: AsyncSession,
        current_user: User,
    ) -> str:
        """
        Exports Question Bank quality metrics and test case distributions in CSV format.
        """
        questions = await self.get_questions_performance(db, current_user)

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(
            [
                "Question ID",
                "Title",
                "Topic",
                "Difficulty",
                "Marks",
                "Tags",
                "Archived",
                "Total Attempts",
                "Solved Count",
                "Success Rate (%)",
                "Average Score",
                "Sample Tests",
                "Functional Tests",
                "Edge Cases",
                "Total Test Marks",
                "Created At",
            ]
        )

        for q in questions:
            writer.writerow(
                [
                    str(q.question_id),
                    q.title,
                    q.topic,
                    q.difficulty,
                    q.marks,
                    q.tags or "",
                    "YES" if q.is_archived else "NO",
                    q.total_attempts,
                    q.solved_count,
                    f"{q.success_rate:.2f}%",
                    f"{q.average_score:.2f}",
                    q.sample_test_count,
                    q.functional_test_count,
                    q.edge_test_count,
                    q.total_test_marks,
                    q.created_at.isoformat(),
                ]
            )

        return output.getvalue()


analytics_service = AnalyticsService()
