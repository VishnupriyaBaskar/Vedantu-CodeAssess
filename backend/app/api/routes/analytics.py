r"""
Analytics & Instructor Reporting API Router
Project: Vedantu Online Coding Assessment Platform (Phase 8)
Workspace: E:\VedantuCodingPlatform_New

Provides live instructor dashboards, assessment performance analysis,
cohort-level distributions, student audit trails, and RFC 4180 CSV exports.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_instructor
from app.core.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    AssessmentAnalyticsResponse,
    CandidatePerformanceDetailResponse,
    CohortAnalyticsResponse,
    InstructorOverviewKPIs,
    QuestionPerformanceItem,
)
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Instructor Reporting"])


@router.get(
    "/instructor/overview",
    response_model=InstructorOverviewKPIs,
    summary="Get high-level instructor overview KPIs (Instructor/Admin)",
)
async def get_instructor_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> InstructorOverviewKPIs:
    """Returns live aggregated KPIs for the instructor management dashboard."""
    return await analytics_service.get_instructor_overview(db, current_user)


@router.get(
    "/instructor/assessments/{assessment_id}",
    response_model=AssessmentAnalyticsResponse,
    summary="Get detailed performance analytics for a specific assessment (Instructor/Admin)",
)
async def get_assessment_analytics(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> AssessmentAnalyticsResponse:
    """Returns assessment-level scores, distributions, topic/difficulty breakdown, and proctoring stats."""
    return await analytics_service.get_assessment_analytics(
        assessment_id, db, current_user
    )


@router.get(
    "/instructor/cohort",
    response_model=CohortAnalyticsResponse,
    summary="Get cohort-level performance insights and distributions (Instructor/Admin)",
)
async def get_cohort_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> CohortAnalyticsResponse:
    """Returns cohort distributions, mastery proficiencies, top performers, and at-risk candidates."""
    return await analytics_service.get_cohort_analytics(db, current_user)


@router.get(
    "/instructor/candidates/{candidate_id}",
    response_model=CandidatePerformanceDetailResponse,
    summary="Get comprehensive candidate performance audit report (Instructor/Admin)",
)
async def get_candidate_report(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> CandidatePerformanceDetailResponse:
    """Returns candidate summary, topic mastery, difficulty breakdown, and safe submission history."""
    return await analytics_service.get_candidate_report(
        candidate_id, db, current_user
    )


@router.get(
    "/instructor/questions",
    response_model=list[QuestionPerformanceItem],
    summary="Get Question Bank quality and performance indicators (Instructor/Admin)",
)
async def get_questions_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> list[QuestionPerformanceItem]:
    """Returns question bank quality metrics: attempts, solved count, success rate, and test case distributions."""
    return await analytics_service.get_questions_performance(db, current_user)


@router.get(
    "/instructor/assessments/{assessment_id}/export",
    summary="Export assessment candidate results to CSV (Instructor/Admin)",
)
async def export_assessment_results_csv(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Generates RFC 4180 compliant CSV export for assessment candidate performance."""
    csv_data = await analytics_service.export_assessment_results_csv(
        assessment_id, db, current_user
    )
    filename = f"assessment_{assessment_id}_results.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/instructor/candidates/{candidate_id}/export",
    summary="Export individual candidate report to CSV (Instructor/Admin)",
)
async def export_candidate_report_csv(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Generates RFC 4180 compliant CSV export for candidate mastery and submission history."""
    csv_data = await analytics_service.export_candidate_report_csv(
        candidate_id, db, current_user
    )
    filename = f"candidate_{candidate_id}_report.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/instructor/questions/export",
    summary="Export question bank quality indicators to CSV (Instructor/Admin)",
)
async def export_questions_performance_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Generates RFC 4180 compliant CSV export for question bank performance and test case distributions."""
    csv_data = await analytics_service.export_questions_performance_csv(
        db, current_user
    )
    filename = "question_bank_performance.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
