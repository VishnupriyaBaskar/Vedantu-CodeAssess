r"""
Assessment Orchestration API Endpoints (Instructor & Admin)
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New

Handles Assessment creation, question curation, status lifecycle (DRAFT -> PUBLISHED -> ARCHIVED),
candidate enrollment, and cohort result analytics.
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_instructor
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_candidate import AssessmentCandidate
from app.models.question import Question
from app.models.user import User
from app.schemas.assessment import (
    AssessmentAdminResponse,
    AssessmentCandidateAssign,
    AssessmentCreate,
    AssessmentUpdate,
)
from app.schemas.question import QuestionAdminResponse, TestCaseAdminResponse

router = APIRouter(prefix="/assessments", tags=["Assessments Management"])


def _to_admin_assessment_response(a: Assessment, candidate_count: int = 0) -> AssessmentAdminResponse:
    """Helper to convert Assessment ORM entity to AssessmentAdminResponse."""
    questions_admin = []
    if a.questions:
        for q in sorted(a.questions, key=lambda x: x.display_order):
            tcs = [
                TestCaseAdminResponse(
                    id=tc.id,
                    question_id=tc.question_id,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    explanation=tc.explanation,
                    marks=tc.marks,
                    display_order=tc.display_order,
                    is_hidden=tc.is_hidden,
                )
                for tc in sorted(q.test_cases, key=lambda x: x.display_order)
            ]
            questions_admin.append(
                QuestionAdminResponse(
                    id=q.id,
                    assessment_id=q.assessment_id,
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
                    is_archived=q.is_archived,
                    created_by=q.created_by,
                    test_cases=tcs,
                    created_at=q.created_at,
                    updated_at=q.updated_at,
                )
            )

    return AssessmentAdminResponse(
        id=a.id,
        title=a.title,
        description=a.description,
        instructions=a.instructions,
        duration_minutes=a.duration_minutes,
        total_marks=a.total_marks,
        passing_marks=a.passing_marks,
        difficulty=a.difficulty,
        allowed_languages=a.allowed_languages,
        proctoring_config=a.proctoring_config,
        status=a.status,
        created_by=a.created_by,
        start_time=a.start_time,
        end_time=a.end_time,
        questions=questions_admin,
        candidate_count=candidate_count,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.post(
    "",
    response_model=AssessmentAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coding assessment (Instructor/Admin)",
)
async def create_assessment(
    data: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> AssessmentAdminResponse:
    """Creates a new assessment in DRAFT status and optionally attaches selected questions."""
    assessment_id = uuid.uuid4()
    assessment = Assessment(
        id=assessment_id,
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        duration_minutes=data.duration_minutes,
        total_marks=data.total_marks,
        passing_marks=data.passing_marks,
        difficulty=data.difficulty,
        allowed_languages=data.allowed_languages,
        proctoring_config=data.proctoring_config,
        status="DRAFT",
        created_by=current_user.id,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(assessment)

    if data.question_ids:
        # Associate questions with this assessment
        stmt = select(Question).where(Question.id.in_(data.question_ids))
        result = await db.execute(stmt)
        questions = result.scalars().all()
        for idx, q in enumerate(questions):
            q.assessment_id = assessment_id
            q.display_order = idx + 1

    await db.commit()

    # Re-fetch with loaded questions and test cases
    stmt = (
        select(Assessment)
        .options(selectinload(Assessment.questions).selectinload(Question.test_cases))
        .where(Assessment.id == assessment_id)
    )
    res = await db.execute(stmt)
    created_a = res.scalar_one()
    return _to_admin_assessment_response(created_a, candidate_count=0)


@router.get(
    "",
    response_model=List[AssessmentAdminResponse],
    summary="List assessments with status filters (Instructor/Admin)",
)
async def list_assessments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (DRAFT, PUBLISHED, etc.)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> List[AssessmentAdminResponse]:
    """Lists assessments ordered by creation timestamp."""
    query = (
        select(Assessment)
        .options(selectinload(Assessment.questions).selectinload(Question.test_cases))
        .order_by(Assessment.created_at.desc())
    )

    if status_filter:
        query = query.where(Assessment.status == status_filter)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    assessments = result.scalars().all()

    # Fetch candidate counts in bulk
    a_ids = [a.id for a in assessments]
    candidate_counts = {}
    if a_ids:
        c_stmt = (
            select(AssessmentCandidate.assessment_id, func.count(AssessmentCandidate.id))
            .where(AssessmentCandidate.assessment_id.in_(a_ids))
            .group_by(AssessmentCandidate.assessment_id)
        )
        c_res = await db.execute(c_stmt)
        for row in c_res.all():
            candidate_counts[row[0]] = row[1]

    return [_to_admin_assessment_response(a, candidate_counts.get(a.id, 0)) for a in assessments]


@router.get(
    "/{assessment_id}",
    response_model=AssessmentAdminResponse,
    summary="Get assessment details by ID (Instructor/Admin)",
)
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> AssessmentAdminResponse:
    """Fetch complete assessment details including questions, test cases, and enrolled candidates count."""
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

    # Candidate count
    c_stmt = select(func.count(AssessmentCandidate.id)).where(AssessmentCandidate.assessment_id == assessment_id)
    c_res = await db.execute(c_stmt)
    cand_count = c_res.scalar() or 0

    return _to_admin_assessment_response(assessment, cand_count)


@router.put(
    "/{assessment_id}",
    response_model=AssessmentAdminResponse,
    summary="Update assessment configuration (Instructor/Admin)",
)
async def update_assessment(
    assessment_id: uuid.UUID,
    data: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> AssessmentAdminResponse:
    """Updates assessment metadata and attached questions."""
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

    update_dict = data.model_dump(exclude_unset=True)
    q_ids = update_dict.pop("question_ids", None)

    for field, value in update_dict.items():
        setattr(assessment, field, value)

    if q_ids is not None:
        # Re-link questions
        # First reset existing questions that were linked to this assessment
        reset_stmt = select(Question).where(Question.assessment_id == assessment_id)
        reset_res = await db.execute(reset_stmt)
        for old_q in reset_res.scalars().all():
            old_q.assessment_id = None

        if q_ids:
            new_q_stmt = select(Question).where(Question.id.in_(q_ids))
            new_q_res = await db.execute(new_q_stmt)
            for idx, q in enumerate(new_q_res.scalars().all()):
                q.assessment_id = assessment_id
                q.display_order = idx + 1

    await db.commit()

    # Re-fetch
    refetch_stmt = (
        select(Assessment)
        .options(selectinload(Assessment.questions).selectinload(Question.test_cases))
        .where(Assessment.id == assessment_id)
    )
    refetch_res = await db.execute(refetch_stmt)
    updated_a = refetch_res.scalar_one()

    c_stmt = select(func.count(AssessmentCandidate.id)).where(AssessmentCandidate.assessment_id == assessment_id)
    c_res = await db.execute(c_stmt)
    cand_count = c_res.scalar() or 0

    return _to_admin_assessment_response(updated_a, cand_count)


@router.post(
    "/{assessment_id}/publish",
    response_model=AssessmentAdminResponse,
    summary="Publish assessment for candidate participation (Instructor/Admin)",
)
async def publish_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> AssessmentAdminResponse:
    """
    Transitions assessment status from DRAFT to PUBLISHED.
    Validates that at least one question with valid test cases is attached.
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

    if not assessment.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish assessment: at least one question must be attached.",
        )

    # Check that each question has at least one test case
    for q in assessment.questions:
        if not q.test_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot publish assessment: question '{q.title}' has no test cases configured.",
            )

    assessment.status = "PUBLISHED"
    await db.commit()

    refetch_stmt = (
        select(Assessment)
        .options(selectinload(Assessment.questions).selectinload(Question.test_cases))
        .where(Assessment.id == assessment_id)
    )
    refetch_res = await db.execute(refetch_stmt)
    published_a = refetch_res.scalar_one()

    c_stmt = select(func.count(AssessmentCandidate.id)).where(AssessmentCandidate.assessment_id == assessment_id)
    c_res = await db.execute(c_stmt)
    cand_count = c_res.scalar() or 0

    return _to_admin_assessment_response(published_a, cand_count)


@router.post(
    "/{assessment_id}/candidates",
    summary="Enroll student candidates into assessment (Instructor/Admin)",
)
async def assign_candidates(
    assessment_id: uuid.UUID,
    data: AssessmentCandidateAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Enrolls candidate student UUIDs into the specified assessment."""
    stmt = select(Assessment).where(Assessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    # Validate that users exist and have STUDENT role
    u_stmt = select(User).options(selectinload(User.roles)).where(User.id.in_(data.user_ids))
    u_res = await db.execute(u_stmt)
    users = u_res.scalars().all()

    valid_user_ids = {u.id for u in users}
    missing_ids = set(data.user_ids) - valid_user_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Users not found: {[str(uid) for uid in missing_ids]}",
        )

    # Find already enrolled
    existing_stmt = select(AssessmentCandidate.user_id).where(
        AssessmentCandidate.assessment_id == assessment_id,
        AssessmentCandidate.user_id.in_(data.user_ids),
    )
    existing_res = await db.execute(existing_stmt)
    already_enrolled = set(existing_res.scalars().all())

    newly_enrolled = 0
    for uid in data.user_ids:
        if uid not in already_enrolled:
            ac = AssessmentCandidate(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                user_id=uid,
            )
            db.add(ac)
            newly_enrolled += 1

    await db.commit()
    return {
        "detail": f"Successfully enrolled {newly_enrolled} new candidates.",
        "enrolled_count": newly_enrolled,
        "already_enrolled_count": len(already_enrolled),
    }


@router.get(
    "/{assessment_id}/results",
    summary="Get cohort examination results for an assessment (Instructor/Admin)",
)
async def get_assessment_cohort_results(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Returns analytics and candidate attempt scores across the assessment cohort."""
    stmt = (
        select(AssessmentAttempt)
        .options(selectinload(AssessmentAttempt.user))
        .where(AssessmentAttempt.assessment_id == assessment_id)
        .order_by(AssessmentAttempt.total_score.desc())
    )
    result = await db.execute(stmt)
    attempts = result.scalars().all()

    cohort_results = []
    for att in attempts:
        cohort_results.append({
            "attempt_id": att.id,
            "user_id": att.user_id,
            "candidate_name": att.user.full_name if att.user else "Unknown",
            "candidate_email": att.user.email if att.user else "Unknown",
            "status": att.status,
            "started_at": att.started_at,
            "submitted_at": att.submitted_at,
            "total_score": att.total_score,
            "percentage": att.percentage,
            "is_passed": att.is_passed,
        })

    return {
        "assessment_id": assessment_id,
        "total_attempts": len(cohort_results),
        "results": cohort_results,
    }


@router.delete(
    "/{assessment_id}",
    summary="Archive an assessment (Instructor/Admin)",
)
async def archive_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Archives an assessment to preserve historical evaluation records."""
    stmt = select(Assessment).where(Assessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    assessment.status = "ARCHIVED"
    await db.commit()
    return {"detail": "Assessment archived successfully."}
