r"""
Code Evaluation and Assessment Scoring Engine Service
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New

Handles code evaluation via Judge0 CE, deterministic grading formulas, test case isolation,
outbox/concurrency safe persistence, and candidate assessment scoring.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_candidate import AssessmentCandidate
from app.models.code_draft import CodeDraft
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.submission import Submission
from app.models.submission_evaluation import SubmissionEvaluation
from app.models.submission_test_case_result import SubmissionTestCaseResult
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.submission import (
    AIFeedbackResponse,
    AssessmentSubmitResponse,
    StaticAnalysisResponse,
    StaticFindingResponse,
    SubmissionCreate,
    SubmissionEvaluationResponse,
    SubmissionResponse,
    TestCaseResultPublic,
)
from app.services.ai_evaluation import AIEvaluationRequest, ai_evaluation_service
from app.services.judge0_service import (
    ExecutionResult,
    Judge0ConnectionError,
    Judge0Error,
    Judge0TimeoutError,
    judge0_service,
)
from app.services.static_analysis import analyze_code

logger = logging.getLogger("evaluation_service")


# ------------------------------------------------------------------------------
# Status Mapping Helpers
# ------------------------------------------------------------------------------
def map_judge0_status_id(status_id: int) -> str:
    """Map Judge0 status code to canonical platform evaluation status."""
    if status_id == 3:
        return "ACCEPTED"
    elif status_id == 4:
        return "WRONG_ANSWER"
    elif status_id == 5:
        return "TIME_LIMIT_EXCEEDED"
    elif status_id == 6:
        return "COMPILATION_ERROR"
    elif 7 <= status_id <= 12:
        return "RUNTIME_ERROR"
    elif status_id in (13, 14):
        return "INTERNAL_ERROR"
    return "UNKNOWN_ERROR"


class EvaluationService:
    """
    Core Evaluation and Scoring Engine.
    Coordinates sandbox execution, test case isolation, score calculation,
    and exam lifecycle state transitions.
    """

    async def get_active_language(
        self,
        db: AsyncSession,
        language_id: uuid.UUID,
    ) -> ProgrammingLanguage:
        """Resolve active programming language by ID."""
        stmt = select(ProgrammingLanguage).where(
            ProgrammingLanguage.id == language_id,
            ProgrammingLanguage.is_active == True,  # noqa: E712
        )
        result = await db.execute(stmt)
        lang = result.scalar_one_or_none()
        if not lang:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected programming language is invalid or inactive.",
            )
        return lang

    async def validate_assessment_timing(
        self,
        db: AsyncSession,
        assessment: Assessment,
        user_id: uuid.UUID,
    ) -> Tuple[AssessmentAttempt, int]:
        """
        Server-authoritative assessment timing and attempt validation.
        Enforces a 15-second grace period for network latency.
        Returns the active AssessmentAttempt and remaining seconds.
        """
        # Fetch attempt with row lock
        stmt = (
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.user_id == user_id,
            )
            .with_for_update()
        )
        result = await db.execute(stmt)
        attempt = result.scalar_one_or_none()

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No assessment attempt found. You must start the assessment first.",
            )

        if attempt.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment attempt is already submitted and finalized.",
            )

        now = datetime.now(timezone.utc)
        elapsed_seconds = (now - attempt.started_at).total_seconds()
        total_allowed_seconds = (assessment.duration_minutes * 60) + 15  # 15s grace period
        remaining_seconds = int(total_allowed_seconds - elapsed_seconds)

        if remaining_seconds <= 0:
            # Assessment has expired
            attempt.status = "COMPLETED"
            attempt.submitted_at = now
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assessment duration and grace period have expired.",
            )

        return attempt, max(0, remaining_seconds - 15)

    def validate_allowed_language(
        self,
        assessment: Assessment,
        language: ProgrammingLanguage,
    ) -> None:
        """Verify the programming language is permitted by the assessment."""
        allowed_str = assessment.allowed_languages.strip()
        if allowed_str == "ALL_ACTIVE":
            return

        allowed_list = [item.strip().lower() for item in allowed_str.split(",") if item.strip()]
        if language.name.strip().lower() not in allowed_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language '{language.name}' is not allowed for this assessment. Allowed: {assessment.allowed_languages}",
            )

    async def evaluate_single_test_case(
        self,
        source_code: str,
        judge0_language_id: int,
        test_case: TestCase,
        time_limit_seconds: float,
        memory_limit_mb: int,
    ) -> Dict[str, any]:
        """Execute source code against a single test case in Judge0 sandbox."""
        try:
            exec_res = await judge0_service.execute_and_wait(
                source_code=source_code,
                language_id=judge0_language_id,
                stdin=test_case.input_data,
                expected_output=test_case.expected_output,
                cpu_time_limit=time_limit_seconds,
                memory_limit=memory_limit_mb * 1024,
                max_poll_seconds=12.0,
            )

            status_str = map_judge0_status_id(exec_res.status.id)
            error_msg = None
            if status_str == "COMPILATION_ERROR":
                error_msg = exec_res.compile_output or "Compilation failed."
            elif status_str == "RUNTIME_ERROR":
                error_msg = exec_res.stderr or exec_res.message or "Runtime exception occurred."
            elif status_str == "TIME_LIMIT_EXCEEDED":
                error_msg = f"Time Limit Exceeded ({time_limit_seconds}s limit)."
            elif status_str == "INTERNAL_ERROR":
                error_msg = "Sandbox internal error. Candidate not penalized."

            marks_awarded = float(test_case.marks) if status_str == "ACCEPTED" else 0.0

            return {
                "test_case_id": test_case.id,
                "status": status_str,
                "is_sample": not test_case.is_hidden,
                "execution_time": exec_res.time,
                "memory_usage": exec_res.memory,
                "marks_awarded": marks_awarded,
                "error_message": error_msg,
                "sample_input": test_case.input_data if not test_case.is_hidden else None,
                "sample_expected": test_case.expected_output if not test_case.is_hidden else None,
                "raw_result": exec_res,
            }

        except (Judge0ConnectionError, Judge0TimeoutError, Judge0Error) as e:
            logger.error("Judge0 sandbox failure on test case %s: %s", test_case.id, e)
            return {
                "test_case_id": test_case.id,
                "status": "INTERNAL_ERROR",
                "is_sample": not test_case.is_hidden,
                "execution_time": None,
                "memory_usage": None,
                "marks_awarded": 0.0,
                "error_message": "Sandbox execution unavailable or timed out.",
                "sample_input": test_case.input_data if not test_case.is_hidden else None,
                "sample_expected": test_case.expected_output if not test_case.is_hidden else None,
                "raw_result": None,
            }

    async def evaluate_submission(
        self,
        db: AsyncSession,
        user: User,
        data: SubmissionCreate,
        run_mode: str = "FULL",  # "FULL" or "SAMPLE_ONLY"
    ) -> SubmissionResponse:
        """
        Evaluate student code submission:
        - If run_mode == "SAMPLE_ONLY", tests only public sample cases without persisting formal score.
        - If run_mode == "FULL", tests all test cases, computes partial marks, persists Submission
          and SubmissionTestCaseResult records, updates CodeDraft, and returns sanitized result.
        """
        # 1. Resolve Language
        language = await self.get_active_language(db, data.programming_language_id)

        # 2. Resolve Assessment and validate timing if applicable
        assessment: Optional[Assessment] = None
        if data.assessment_id:
            stmt = select(Assessment).where(Assessment.id == data.assessment_id)
            result = await db.execute(stmt)
            assessment = result.scalar_one_or_none()
            if not assessment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assessment not found.",
                )
            if assessment.status not in ("PUBLISHED", "IN_PROGRESS"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assessment is not open for submission (status: {assessment.status}).",
                )
            self.validate_allowed_language(assessment, language)
            await self.validate_assessment_timing(db, assessment, user.id)

        # 3. Resolve Question
        q_stmt = (
            select(Question)
            .options(selectinload(Question.test_cases))
            .where(Question.id == data.question_id, Question.is_archived == False)  # noqa: E712
        )
        q_result = await db.execute(q_stmt)
        question = q_result.scalar_one_or_none()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found or has been archived.",
            )

        if assessment and question.assessment_id and question.assessment_id != assessment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to the specified assessment.",
            )

        # 4. Filter Test Cases according to run_mode
        all_test_cases = sorted(question.test_cases, key=lambda tc: tc.display_order)
        if run_mode == "SAMPLE_ONLY":
            eval_test_cases = [tc for tc in all_test_cases if not tc.is_hidden]
            if not eval_test_cases:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No public sample test cases configured for this question.",
                )
        else:
            eval_test_cases = all_test_cases

        if not eval_test_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No test cases available for evaluation.",
            )

        # 5. Execute Test Cases
        results_list: List[Dict[str, any]] = []
        compilation_failed = False
        compilation_error_msg = ""
        max_time = 0.0
        max_memory = 0

        for idx, tc in enumerate(eval_test_cases):
            if compilation_failed:
                # Short-circuit on compilation error: mark remaining test cases as failed with 0 marks
                results_list.append({
                    "test_case_id": tc.id,
                    "status": "COMPILATION_ERROR",
                    "is_sample": not tc.is_hidden,
                    "execution_time": None,
                    "memory_usage": None,
                    "marks_awarded": 0.0,
                    "error_message": compilation_error_msg or "Compilation failed.",
                    "sample_input": tc.input_data if not tc.is_hidden else None,
                    "sample_expected": tc.expected_output if not tc.is_hidden else None,
                    "raw_result": None,
                })
                continue

            tc_result = await self.evaluate_single_test_case(
                source_code=data.source_code,
                judge0_language_id=language.judge0_language_id,
                test_case=tc,
                time_limit_seconds=question.time_limit_seconds,
                memory_limit_mb=question.memory_limit_mb,
            )

            results_list.append(tc_result)

            if tc_result["execution_time"] and tc_result["execution_time"] > max_time:
                max_time = tc_result["execution_time"]
            if tc_result["memory_usage"] and tc_result["memory_usage"] > max_memory:
                max_memory = tc_result["memory_usage"]

            if tc_result["status"] == "COMPILATION_ERROR":
                compilation_failed = True
                compilation_error_msg = tc_result.get("error_message") or "Compilation failed."

        # 6. Compute Deterministic Scoring
        passed_count = sum(1 for r in results_list if r["status"] == "ACCEPTED")
        total_eval_count = len(results_list)

        total_tc_marks = sum(tc.marks for tc in eval_test_cases)
        total_tc_marks_effective = total_tc_marks if total_tc_marks > 0 else 1
        awarded_tc_marks = sum(r["marks_awarded"] for r in results_list)

        # Proportional question score
        question_score = round((awarded_tc_marks / total_tc_marks_effective) * question.marks, 2)

        # Submission overall status
        if passed_count == total_eval_count:
            overall_status = "ACCEPTED"
        elif compilation_failed:
            overall_status = "COMPILATION_ERROR"
        else:
            # First non-accepted status as dominant failure
            first_fail = next((r["status"] for r in results_list if r["status"] != "ACCEPTED"), "WRONG_ANSWER")
            overall_status = first_fail

        now = datetime.now(timezone.utc)

        # 7. Persistence for FULL evaluation mode
        submission_id = uuid.uuid4()
        if run_mode == "FULL":
            db_submission = Submission(
                id=submission_id,
                user_id=user.id,
                assessment_id=data.assessment_id,
                question_id=data.question_id,
                programming_language_id=data.programming_language_id,
                source_code=data.source_code,
                status=overall_status,
                execution_time=max_time if max_time > 0 else None,
                memory_usage=max_memory if max_memory > 0 else None,
                score=question_score,
                judge0_token=None,
                created_at=now,
            )
            db.add(db_submission)

            for r in results_list:
                tr = SubmissionTestCaseResult(
                    id=uuid.uuid4(),
                    submission_id=submission_id,
                    test_case_id=r["test_case_id"],
                    status=r["status"],
                    execution_time=r["execution_time"],
                    memory_usage=r["memory_usage"],
                    marks_awarded=r["marks_awarded"],
                    error_message=r["error_message"],
                    is_sample=r["is_sample"],
                    created_at=now,
                )
                db.add(tr)

            # Update or save code draft
            if data.assessment_id:
                draft_stmt = select(CodeDraft).where(
                    CodeDraft.user_id == user.id,
                    CodeDraft.assessment_id == data.assessment_id,
                    CodeDraft.question_id == data.question_id,
                )
                draft_res = await db.execute(draft_stmt)
                existing_draft = draft_res.scalar_one_or_none()
                if existing_draft:
                    existing_draft.source_code = data.source_code
                    existing_draft.programming_language_id = data.programming_language_id
                    existing_draft.updated_at = now
                else:
                    new_draft = CodeDraft(
                        user_id=user.id,
                        assessment_id=data.assessment_id,
                        question_id=data.question_id,
                        programming_language_id=data.programming_language_id,
                        source_code=data.source_code,
                        updated_at=now,
                    )
                    db.add(new_draft)

            await db.commit()

            # Trigger real-time adaptive topic mastery tracking (Phase 6)
            try:
                from app.services.adaptive_service import adaptive_service
                await adaptive_service.calculate_topic_mastery(
                    db=db,
                    user_id=user.id,
                    persist=True,
                    trigger_event="ASSESSMENT_SUBMISSION" if data.assessment_id else "PRACTICE_SUBMISSION",
                )
            except Exception as adapt_err:
                logger.error("Failed to update adaptive mastery on submission: %s", adapt_err)

        # 7b. Qualitative Review (Static Analysis & AI Code Evaluation - Stage 5)
        eval_resp: Optional[SubmissionEvaluationResponse] = None
        if run_mode == "FULL":
            try:
                # 1. Run safe static analysis without code execution
                static_res = analyze_code(language.name, data.source_code)
                static_dict = static_res.model_dump()

                # 2. Run AI qualitative review (guaranteed confidential: no hidden test cases)
                ai_req = AIEvaluationRequest(
                    problem_title=question.title,
                    problem_description=question.problem_description,
                    constraints=question.constraints,
                    language_name=language.name,
                    source_code=data.source_code,
                    execution_status=overall_status,
                    score=question_score,
                    total_test_cases=total_eval_count,
                    passed_test_cases=passed_count,
                )
                ai_res = await ai_evaluation_service.evaluate_code(ai_req)
                ai_dict = ai_res.feedback.model_dump() if ai_res.feedback else None

                # 3. Persist evaluation record
                eval_id = uuid.uuid4()
                db_eval = SubmissionEvaluation(
                    id=eval_id,
                    submission_id=submission_id,
                    static_analysis=static_dict,
                    ai_feedback=ai_dict,
                    ai_provider=ai_res.provider_name,
                    ai_status=ai_res.status,
                    created_at=now,
                )
                db.add(db_eval)
                await db.commit()

                eval_resp = SubmissionEvaluationResponse(
                    id=eval_id,
                    submission_id=submission_id,
                    static_analysis=StaticAnalysisResponse(**static_dict) if static_dict else None,
                    ai_feedback=AIFeedbackResponse(**ai_dict) if ai_dict else None,
                    ai_provider=ai_res.provider_name,
                    ai_status=ai_res.status,
                    created_at=now,
                )
            except Exception as eval_err:
                logger.exception("Qualitative evaluation failed for submission %s: %s", submission_id, eval_err)

        # 8. Build Sanitized Response
        public_results = [
            TestCaseResultPublic(
                test_case_id=r["test_case_id"],
                status=r["status"],
                is_sample=r["is_sample"],
                execution_time=r["execution_time"],
                memory_usage=r["memory_usage"],
                marks_awarded=r["marks_awarded"],
                error_message=r["error_message"],
                sample_input=r["sample_input"],
                sample_expected=r["sample_expected"],
            )
            for r in results_list
        ]

        return SubmissionResponse(
            id=submission_id,
            user_id=user.id,
            assessment_id=data.assessment_id,
            question_id=data.question_id,
            programming_language_id=data.programming_language_id,
            status=overall_status,
            score=question_score,
            total_test_cases=total_eval_count,
            passed_test_cases=passed_count,
            execution_time=max_time if max_time > 0 else None,
            memory_usage=max_memory if max_memory > 0 else None,
            created_at=now,
            test_case_results=public_results,
            evaluation=eval_resp,
        )

    async def finalize_assessment_attempt(
        self,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        user: User,
    ) -> AssessmentSubmitResponse:
        """
        Finalize and grade an assessment attempt:
        - Locks attempt row to prevent concurrency double-submission.
        - Calculates total score based on the highest score per question.
        - Computes final percentage and pass/fail determination.
        - Transitions attempt status to COMPLETED.
        """
        # Fetch assessment
        stmt = (
            select(Assessment)
            .options(selectinload(Assessment.questions))
            .where(Assessment.id == assessment_id)
        )
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found.",
            )

        # Lock attempt row
        att_stmt = (
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id == user.id,
            )
            .with_for_update()
        )
        att_res = await db.execute(att_stmt)
        attempt = att_res.scalar_one_or_none()

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment attempt does not exist.",
            )

        now = datetime.now(timezone.utc)

        # If already completed, return existing final scores
        if attempt.status == "COMPLETED":
            return AssessmentSubmitResponse(
                attempt_id=attempt.id,
                assessment_id=assessment.id,
                status=attempt.status,
                submitted_at=attempt.submitted_at or now,
                total_score=attempt.total_score,
                total_possible_marks=assessment.total_marks,
                percentage=attempt.percentage,
                is_passed=attempt.is_passed,
                submissions=[],
            )

        # Query highest score per question for this assessment and user
        sub_stmt = (
            select(
                Submission.question_id,
                func.max(Submission.score).label("max_score"),
            )
            .where(
                Submission.assessment_id == assessment_id,
                Submission.user_id == user.id,
            )
            .group_by(Submission.question_id)
        )
        sub_res = await db.execute(sub_stmt)
        best_scores = {row.question_id: float(row.max_score) for row in sub_res.all()}

        # Total score is the sum of best scores across all questions in the assessment
        total_score = round(sum(best_scores.get(q.id, 0.0) for q in assessment.questions), 2)
        total_possible = assessment.total_marks if assessment.total_marks > 0 else 100
        percentage = round((total_score / total_possible) * 100.0, 2)
        is_passed = total_score >= float(assessment.passing_marks)

        # Update attempt
        attempt.status = "COMPLETED"
        attempt.submitted_at = now
        attempt.total_score = total_score
        attempt.percentage = percentage
        attempt.is_passed = is_passed

        await db.commit()

        # Trigger real-time adaptive topic mastery tracking (Phase 6)
        try:
            from app.services.adaptive_service import adaptive_service
            await adaptive_service.calculate_topic_mastery(
                db=db,
                user_id=user.id,
                persist=True,
                trigger_event="ASSESSMENT_COMPLETION",
            )
        except Exception as adapt_err:
            logger.error("Failed to update adaptive mastery on attempt finalization: %s", adapt_err)

        # Cleanly terminate any active proctoring session (Phase 7)
        try:
            from app.models.proctoring_session import ProctoringSession
            ps_stmt = select(ProctoringSession).where(
                ProctoringSession.assessment_attempt_id == attempt.id
            )
            ps_res = await db.execute(ps_stmt)
            active_ps = ps_res.scalar_one_or_none()
            if active_ps and active_ps.status in ("INITIALIZED", "ACTIVE"):
                active_ps.status = "ENDED"
                active_ps.ended_at = now
                await db.commit()
        except Exception as proc_err:
            logger.error("Failed to cleanly end proctoring session on attempt finalization: %s", proc_err)

        return AssessmentSubmitResponse(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            status=attempt.status,
            submitted_at=now,
            total_score=total_score,
            total_possible_marks=assessment.total_marks,
            percentage=percentage,
            is_passed=is_passed,
            submissions=[],
        )


# Singleton instance
evaluation_service = EvaluationService()
