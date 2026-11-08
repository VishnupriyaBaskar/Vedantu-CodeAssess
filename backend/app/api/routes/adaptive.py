r"""
Adaptive Assessment Engine API Routes
Project: Vedantu Online Coding Assessment Platform (Phase 6)
Workspace: E:\VedantuCodingPlatform_New

Exposes authenticated endpoints for:
- Student topic-wise performance metrics
- Deterministic topic mastery scoring and confidence tiers
- Strengths and weaknesses identification
- Intelligent question recommendations with explainable reasons
- Dynamic adaptive difficulty levels
- Longitudinal mastery progression history
- Interactive practice challenge execution & solution submissions
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_student
from app.core.database import get_db
from app.models.user import User
from app.schemas.adaptive import (
    MasteryHistoryResponse,
    PracticeSubmissionRequest,
    QuestionRecommendationListResponse,
    StrengthsAndWeaknessesResponse,
    StudentPerformanceResponse,
    TopicCatalogResponse,
    TopicMasteryListResponse,
    TopicPracticeDetailResponse,
)
from app.schemas.question import QuestionPublicResponse
from app.schemas.submission import SubmissionResponse
from app.services.adaptive_service import adaptive_service

router = APIRouter(prefix="/adaptive", tags=["Adaptive Learning & Recommendations"])


def resolve_target_user_id(
    current_user: User,
    requested_user_id: Optional[uuid.UUID],
) -> uuid.UUID:
    """
    Enforces student isolation and authorization boundaries:
    - Students can access only their own metrics.
    - Instructors and Admins may inspect designated candidate IDs or themselves.
    """
    user_roles = {r.name for r in current_user.roles}
    is_staff = bool(user_roles.intersection({"INSTRUCTOR", "ADMIN"}))

    if requested_user_id is None:
        return current_user.id

    if not is_staff and requested_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Students may only access their own performance analytics.",
        )

    return requested_user_id


@router.get(
    "/performance",
    response_model=StudentPerformanceResponse,
    summary="Get comprehensive student performance metrics",
)
async def get_student_performance(
    user_id: Optional[uuid.UUID] = Query(None, description="Candidate ID (staff-only override)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Returns total questions attempted, solved, submission accuracy, and difficulty breakdown."""
    target_id = resolve_target_user_id(current_user, user_id)
    return await adaptive_service.get_performance_metrics(db=db, user_id=target_id)


@router.get(
    "/mastery",
    response_model=TopicMasteryListResponse,
    summary="Get topic-wise mastery levels and overall score",
)
async def get_topic_mastery(
    user_id: Optional[uuid.UUID] = Query(None, description="Candidate ID (staff-only override)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Calculates and returns deterministic topic mastery scores, categories, confidence, and recommended difficulties."""
    target_id = resolve_target_user_id(current_user, user_id)
    return await adaptive_service.get_topic_mastery_list(db=db, user_id=target_id)


@router.get(
    "/strengths-weaknesses",
    response_model=StrengthsAndWeaknessesResponse,
    summary="Identify strong topics and topics requiring improvement",
)
async def get_strengths_and_weaknesses(
    user_id: Optional[uuid.UUID] = Query(None, description="Candidate ID (staff-only override)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Identifies strong topics, areas needing practice, improving topics, and unattempted topics."""
    target_id = resolve_target_user_id(current_user, user_id)
    return await adaptive_service.get_strengths_and_weaknesses(db=db, user_id=target_id)


@router.get(
    "/recommendations",
    response_model=QuestionRecommendationListResponse,
    summary="Get intelligent question recommendations with reasons",
)
async def get_recommended_questions(
    limit: int = Query(6, ge=1, le=20, description="Maximum recommendations to return"),
    user_id: Optional[uuid.UUID] = Query(None, description="Candidate ID (staff-only override)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    Returns curated, uncompleted coding questions matched to current topic mastery
    and dynamic difficulty, complete with transparent recommendation rationale.
    """
    target_id = resolve_target_user_id(current_user, user_id)
    return await adaptive_service.get_recommended_questions(db=db, user_id=target_id, limit=limit)


@router.get(
    "/history",
    response_model=MasteryHistoryResponse,
    summary="Get longitudinal topic mastery progression history",
)
async def get_mastery_history(
    topic: Optional[str] = Query(None, description="Optional topic filter"),
    limit: int = Query(50, ge=1, le=200, description="Max history snapshots to retrieve"),
    user_id: Optional[uuid.UUID] = Query(None, description="Candidate ID (staff-only override)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Returns longitudinal mastery progression snapshots over time."""
    target_id = resolve_target_user_id(current_user, user_id)
    return await adaptive_service.get_mastery_history(db=db, user_id=target_id, topic=topic, limit=limit)


@router.get(
    "/topics",
    response_model=TopicCatalogResponse,
    summary="Get full syllabus topic catalog with question counts and mastery",
)
async def get_topics_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Returns the official 18 syllabus topics with question counts, descriptions, and current student mastery."""
    return await adaptive_service.get_topics_catalog(db=db, user_id=current_user.id)


@router.get(
    "/topics/{topic_name}",
    response_model=TopicPracticeDetailResponse,
    summary="Get dedicated practice details and question list for a specific topic",
)
async def get_topic_practice_details(
    topic_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Returns all practice questions, student solved statuses, mastery, and recommended question for a topic."""
    return await adaptive_service.get_topic_practice_details(
        db=db,
        user_id=current_user.id,
        topic_name=topic_name,
    )


# ------------------------------------------------------------------------------
# Interactive Practice Challenge Execution Endpoints
# ------------------------------------------------------------------------------
@router.get(
    "/practice/{question_id}",
    response_model=QuestionPublicResponse,
    summary="Fetch practice problem details and sample test cases",
)
async def get_practice_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Fetches public problem statement and sample test cases for interactive practice."""
    return await adaptive_service.get_practice_question(db=db, question_id=question_id)


@router.post(
    "/practice/{question_id}/run-sample",
    response_model=SubmissionResponse,
    summary="Execute practice solution against public sample test cases",
)
async def run_practice_sample(
    question_id: uuid.UUID,
    data: PracticeSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Runs code against public sample cases only without formal score persistence."""
    return await adaptive_service.run_practice_sample(
        db=db,
        user=current_user,
        question_id=question_id,
        language_id=data.programming_language_id,
        source_code=data.source_code,
    )


@router.post(
    "/practice/{question_id}/submit",
    response_model=SubmissionResponse,
    summary="Submit practice solution for full test evaluation & real-time mastery update",
)
async def submit_practice_solution(
    question_id: uuid.UUID,
    data: PracticeSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """
    Evaluates solution across all test cases, persists Submission record, generates
    static & AI feedback, and immediately updates topic mastery and history snapshot.
    """
    return await adaptive_service.submit_practice_solution(
        db=db,
        user=current_user,
        question_id=question_id,
        language_id=data.programming_language_id,
        source_code=data.source_code,
    )
