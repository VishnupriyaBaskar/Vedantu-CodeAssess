r"""
Student Assessment Workflow API Endpoints
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New

Handles candidate exam listing, instructions, timing and grace periods, draft autosaving,
sample test runs, full code evaluations, and exam completion.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_candidate import AssessmentCandidate
from app.models.code_draft import CodeDraft
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.submission import Submission
from app.models.submission_evaluation import SubmissionEvaluation
from app.models.user import User
from app.schemas.assessment import AssessmentPublicResponse
from app.schemas.question import QuestionPublicResponse, TestCasePublicResponse
from app.schemas.submission import (
    AIFeedbackResponse,
    AssessmentStartResponse,
    AssessmentSubmitResponse,
    CodeDraftResponse,
    CodeDraftSave,
    StaticAnalysisResponse,
    SubmissionCreate,
    SubmissionEvaluationResponse,
    SubmissionResponse,
)
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/student", tags=["Student Assessments"])


def _to_public_question(q: Question) -> QuestionPublicResponse:
    """Isolates confidential test cases and returns ONLY public sample test cases."""
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


@router.get(
    "/languages",
    summary="List active programming languages for editor runtime selection",
)
async def list_languages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns active languages supported on the platform for code execution."""
    stmt = (
        select(ProgrammingLanguage)
        .where(ProgrammingLanguage.is_active == True)  # noqa: E712
        .order_by(ProgrammingLanguage.name)
    )
    result = await db.execute(stmt)
    languages = result.scalars().all()
    return [
        {
            "id": lang.id,
            "name": lang.name,
            "version": lang.version,
            "judge0_language_id": lang.judge0_language_id,
        }
        for lang in languages
    ]


@router.get(
    "/assessments",
    response_model=List[AssessmentPublicResponse],
    summary="List available published assessments for the authenticated student",
)
async def list_student_assessments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AssessmentPublicResponse]:
    """Lists published assessments enrolled for the student with attempt status."""
    # Find enrolled assessment IDs
    c_stmt = select(AssessmentCandidate.assessment_id).where(
        AssessmentCandidate.user_id == current_user.id
    )
    c_res = await db.execute(c_stmt)
    enrolled_ids = set(c_res.scalars().all())

    # Query published assessments
    stmt = (
        select(Assessment)
        .options(
            selectinload(Assessment.questions),
            selectinload(Assessment.candidates),
        )
        .where(Assessment.status.in_(["PUBLISHED", "IN_PROGRESS"]))
        .order_by(Assessment.created_at.desc())
    )
    result = await db.execute(stmt)
    assessments = result.scalars().all()

    # Query candidate's attempts
    att_stmt = select(AssessmentAttempt).where(AssessmentAttempt.user_id == current_user.id)
    att_res = await db.execute(att_stmt)
    user_attempts = {att.assessment_id: att for att in att_res.scalars().all()}

    output = []
    for a in assessments:
        # Exclude empty assessments without questions from candidate examination view
        if not a.questions or len(a.questions) == 0:
            continue

        # Include if enrolled or if user has already started an attempt
        if a.id in enrolled_ids or a.id in user_attempts or not a.candidates:
            attempt = user_attempts.get(a.id)
            has_attempted = attempt is not None
            attempt_status = attempt.status if attempt else None

            # Parse allowed languages
            if a.allowed_languages == "ALL_ACTIVE":
                langs = ["Python 3", "Java"]
            else:
                langs = [x.strip() for x in a.allowed_languages.split(",") if x.strip()]

            output.append(
                AssessmentPublicResponse(
                    id=a.id,
                    title=a.title,
                    description=a.description,
                    instructions=a.instructions,
                    duration_minutes=a.duration_minutes,
                    total_marks=a.total_marks,
                    passing_marks=a.passing_marks,
                    difficulty=a.difficulty,
                    status=a.status,
                    allowed_languages=langs,
                    start_time=a.start_time,
                    end_time=a.end_time,
                    question_count=len(a.questions),
                    has_attempted=has_attempted,
                    attempt_status=attempt_status,
                    proctoring_config=a.proctoring_config,
                )
            )

    return output


@router.get(
    "/assessments/{assessment_id}/instructions",
    summary="Get pre-exam instructions and guidelines",
)
async def get_assessment_instructions(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns assessment overview and rules prior to candidate initiating timer."""
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

    # Check attempt status
    att_stmt = select(AssessmentAttempt).where(
        AssessmentAttempt.assessment_id == assessment_id,
        AssessmentAttempt.user_id == current_user.id,
    )
    att_res = await db.execute(att_stmt)
    attempt = att_res.scalar_one_or_none()

    return {
        "assessment_id": assessment.id,
        "title": assessment.title,
        "description": assessment.description,
        "instructions": assessment.instructions or "Read each question carefully. Write clean, optimal code that handles edge cases.",
        "duration_minutes": assessment.duration_minutes,
        "total_marks": assessment.total_marks,
        "passing_marks": assessment.passing_marks,
        "question_count": len(assessment.questions),
        "allowed_languages": assessment.allowed_languages,
        "attempt_status": attempt.status if attempt else None,
        "started_at": attempt.started_at if attempt else None,
    }


@router.post(
    "/assessments/{assessment_id}/start",
    response_model=AssessmentStartResponse,
    summary="Start or resume an assessment attempt (Enforces server-authoritative timer)",
)
async def start_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentStartResponse:
    """
    Initializes or resumes an examination attempt session:
    - Enforces one attempt per student.
    - Calculates exact remaining time server-side with 15-second network grace.
    - Hydrates public questions with sample test cases (hidden test cases are strictly excluded).
    - Restores student autosaved code drafts.
    """
    stmt = (
        select(Assessment)
        .options(selectinload(Assessment.questions).selectinload(Question.test_cases))
        .where(Assessment.id == assessment_id)
    )
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
            detail=f"Assessment is not active (current status: {assessment.status}).",
        )

    # Find or create attempt
    att_stmt = (
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.user_id == current_user.id,
        )
        .with_for_update()
    )
    att_res = await db.execute(att_stmt)
    attempt = att_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if attempt is None:
        attempt = AssessmentAttempt(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            user_id=current_user.id,
            status="IN_PROGRESS",
            started_at=now,
        )
        db.add(attempt)
        await db.commit()
    elif attempt.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted and finalized this assessment.",
        )

    # Compute remaining time server-side
    elapsed_seconds = (now - attempt.started_at).total_seconds()
    total_allowed_seconds = (assessment.duration_minutes * 60) + 15
    remaining_seconds = int(total_allowed_seconds - elapsed_seconds)

    if remaining_seconds <= 0:
        attempt.status = "COMPLETED"
        attempt.submitted_at = now
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assessment duration and grace period have expired.",
        )

    # Fetch candidate's drafts
    drafts_stmt = select(CodeDraft).where(
        CodeDraft.user_id == current_user.id,
        CodeDraft.assessment_id == assessment_id,
    )
    drafts_res = await db.execute(drafts_stmt)
    drafts_dict = {str(d.question_id): d.source_code for d in drafts_res.scalars().all()}

    # Parse allowed languages
    if assessment.allowed_languages == "ALL_ACTIVE":
        langs = ["Python 3", "Java"]
    else:
        langs = [x.strip() for x in assessment.allowed_languages.split(",") if x.strip()]

    # Isolate questions
    public_questions = [
        _to_public_question(q)
        for q in sorted(assessment.questions, key=lambda x: x.display_order)
        if not q.is_archived
    ]

    return AssessmentStartResponse(
        attempt_id=attempt.id,
        assessment_id=assessment.id,
        title=assessment.title,
        instructions=assessment.instructions,
        started_at=attempt.started_at,
        duration_minutes=assessment.duration_minutes,
        remaining_seconds=max(0, remaining_seconds - 15),
        status=attempt.status,
        allowed_languages=langs,
        questions=public_questions,
        drafts=drafts_dict,
        proctoring_config=assessment.proctoring_config,
    )


@router.post(
    "/assessments/{assessment_id}/drafts",
    response_model=CodeDraftResponse,
    summary="Autosave code draft for a question during active assessment",
)
async def save_code_draft(
    assessment_id: uuid.UUID,
    data: CodeDraftSave,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CodeDraftResponse:
    """Persists intermediate candidate code progress in real time."""
    # Validate assessment timing
    stmt = select(Assessment).where(Assessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    await evaluation_service.validate_assessment_timing(db, assessment, current_user.id)

    now = datetime.now(timezone.utc)
    draft_stmt = select(CodeDraft).where(
        CodeDraft.user_id == current_user.id,
        CodeDraft.assessment_id == assessment_id,
        CodeDraft.question_id == data.question_id,
    )
    draft_res = await db.execute(draft_stmt)
    existing_draft = draft_res.scalar_one_or_none()

    if existing_draft:
        existing_draft.source_code = data.source_code
        existing_draft.programming_language_id = data.programming_language_id
        existing_draft.updated_at = now
    else:
        existing_draft = CodeDraft(
            id=uuid.uuid4(),
            user_id=current_user.id,
            assessment_id=assessment_id,
            question_id=data.question_id,
            programming_language_id=data.programming_language_id,
            source_code=data.source_code,
            updated_at=now,
        )
        db.add(existing_draft)

    await db.commit()

    return CodeDraftResponse(
        question_id=existing_draft.question_id,
        programming_language_id=existing_draft.programming_language_id,
        source_code=existing_draft.source_code,
        updated_at=existing_draft.updated_at,
    )


@router.post(
    "/assessments/{assessment_id}/run-sample",
    response_model=SubmissionResponse,
    summary="Run code against public sample test cases (No gradebook persistence)",
)
async def run_sample_code(
    assessment_id: uuid.UUID,
    data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionResponse:
    """Executes candidate code against public sample cases only, returning immediate test outputs."""
    data.assessment_id = assessment_id
    return await evaluation_service.evaluate_submission(
        db=db,
        user=current_user,
        data=data,
        run_mode="SAMPLE_ONLY",
    )


@router.post(
    "/assessments/{assessment_id}/submit-code",
    response_model=SubmissionResponse,
    summary="Submit solution for full evaluation against sample and hidden test cases",
)
async def submit_question_solution(
    assessment_id: uuid.UUID,
    data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionResponse:
    """
    Evaluates candidate solution against all test cases (sample and confidential hidden).
    Persists formal submission and updates score.
    Hidden test case inputs and expected outputs are strictly excluded from output.
    """
    data.assessment_id = assessment_id
    return await evaluation_service.evaluate_submission(
        db=db,
        user=current_user,
        data=data,
        run_mode="FULL",
    )


@router.post(
    "/assessments/{assessment_id}/finish",
    response_model=AssessmentSubmitResponse,
    summary="Finalize and submit the complete assessment examination",
)
async def finish_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentSubmitResponse:
    """
    Locks attempt session, calculates aggregate score from best submissions,
    determines pass/fail outcome, and transitions attempt status to COMPLETED.
    """
    return await evaluation_service.finalize_assessment_attempt(
        db=db,
        assessment_id=assessment_id,
        user=current_user,
    )


@router.get(
    "/assessments/{assessment_id}/result",
    response_model=AssessmentSubmitResponse,
    summary="View candidate's final assessment result and score summary",
)
async def get_my_assessment_result(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentSubmitResponse:
    """Returns candidate's own final grade, score breakdown, and pass/fail determination."""
    stmt = select(Assessment).where(Assessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    att_stmt = select(AssessmentAttempt).where(
        AssessmentAttempt.assessment_id == assessment_id,
        AssessmentAttempt.user_id == current_user.id,
    )
    att_res = await db.execute(att_stmt)
    attempt = att_res.scalar_one_or_none()

    if not attempt or attempt.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment has not been completed or finalized yet.",
        )

    now = datetime.now(timezone.utc)
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


@router.get(
    "/submissions/{submission_id}/evaluation",
    response_model=SubmissionEvaluationResponse,
    summary="Get qualitative static analysis and AI feedback for a submission",
)
async def get_submission_evaluation(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionEvaluationResponse:
    """
    Retrieves static analysis findings and AI feedback for a student submission.
    Strictly verifies ownership:
    - Students can only view evaluations of their own submissions.
    - Instructors and Admins can view any submission evaluation.
    """
    stmt = (
        select(Submission)
        .options(selectinload(Submission.evaluation))
        .where(Submission.id == submission_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    # Ownership & RBAC check
    user_roles = {r.name.upper() for r in current_user.roles}
    is_privileged = bool(user_roles & {"ADMIN", "INSTRUCTOR"})

    if submission.user_id != current_user.id and not is_privileged:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another candidate's evaluation.",
        )

    eval_record = submission.evaluation
    if not eval_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation has not been generated for this submission.",
        )

    static_data = eval_record.static_analysis
    ai_data = eval_record.ai_feedback

    return SubmissionEvaluationResponse(
        id=eval_record.id,
        submission_id=eval_record.submission_id,
        static_analysis=StaticAnalysisResponse(**static_data) if static_data else None,
        ai_feedback=AIFeedbackResponse(**ai_data) if ai_data else None,
        ai_provider=eval_record.ai_provider,
        ai_status=eval_record.ai_status,
        created_at=eval_record.created_at,
    )
