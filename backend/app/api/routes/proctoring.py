r"""
Proctoring API Endpoints
Project: Vedantu Online Coding Assessment Platform (Phase 7)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_instructor
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.proctoring_alert import ProctoringAlert
from app.models.proctoring_event import ProctoringEvent
from app.models.proctoring_session import ProctoringSession
from app.models.user import User
from app.schemas.proctoring import (
    AssessmentProctoringOverviewResponse,
    AttemptProctoringReportResponse,
    ProctoringAlertResponse,
    ProctoringAlertReviewRequest,
    ProctoringBatchEventsRequest,
    ProctoringEventCreate,
    ProctoringEventResponse,
    ProctoringHeartbeatRequest,
    ProctoringSessionConsentRequest,
    ProctoringSessionStartRequest,
    ProctoringSessionStartResponse,
    ProctoringSessionStatusResponse,
)
from app.services.proctoring_service import proctoring_service

router = APIRouter(prefix="/proctoring", tags=["Assessment Proctoring & Integrity"])


# ------------------------------------------------------------------------------
# Candidate Session Management Endpoints
# ------------------------------------------------------------------------------

@router.post(
    "/sessions/start",
    response_model=ProctoringSessionStartResponse,
    summary="Initialize or resume a proctoring session for an active attempt",
)
async def start_proctoring_session(
    payload: ProctoringSessionStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProctoringSessionStartResponse:
    """
    Candidate endpoint to initiate integrity monitoring for an in-progress attempt.
    Returns session ID, proctoring configuration, and privacy disclosure terms.
    """
    return await proctoring_service.start_session(
        assessment_id=payload.assessment_id,
        attempt_id=payload.attempt_id,
        user=current_user,
        db=db,
    )


@router.post(
    "/sessions/{session_id}/consent",
    summary="Record candidate consent to assessment integrity monitoring",
)
async def submit_proctoring_consent(
    session_id: uuid.UUID,
    payload: ProctoringSessionConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Records explicit candidate agreement before starting monitored examination."""
    return await proctoring_service.record_consent(
        session_id=session_id,
        consent=payload.consent,
        user=current_user,
        db=db,
    )


@router.post(
    "/sessions/{session_id}/events",
    response_model=List[ProctoringEventResponse],
    summary="Record browser focus, visibility, fullscreen, or camera status events",
)
async def record_proctoring_events(
    session_id: uuid.UUID,
    payload: ProctoringBatchEventsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProctoringEventResponse]:
    """
    Ingests candidate-side events (e.g. TAB_SWITCH, WINDOW_BLUR, FULLSCREEN_EXIT)
    and evaluates transparent rule-based suspicious activity thresholds.
    """
    return await proctoring_service.record_events(
        session_id=session_id,
        events_data=payload.events,
        user=current_user,
        db=db,
    )


@router.post(
    "/sessions/{session_id}/heartbeat",
    summary="Candidate client keepalive heartbeat ping",
)
async def record_proctoring_heartbeat(
    session_id: uuid.UUID,
    payload: Optional[ProctoringHeartbeatRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Periodic heartbeat from browser client confirming active monitoring connection."""
    return await proctoring_service.record_heartbeat(
        session_id=session_id,
        user=current_user,
        db=db,
    )


@router.post(
    "/sessions/{session_id}/end",
    summary="Cleanly end proctoring session upon assessment submission",
)
async def end_proctoring_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Gracefully terminates active proctoring monitoring."""
    return await proctoring_service.end_session(
        session_id=session_id,
        user=current_user,
        db=db,
    )


@router.get(
    "/sessions/{session_id}/status",
    response_model=ProctoringSessionStatusResponse,
    summary="Get candidate-facing proctoring session telemetry and status",
)
async def get_session_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProctoringSessionStatusResponse:
    """Returns candidate's monitoring status, connection state, and event counters."""
    return await proctoring_service.get_session_status(
        session_id=session_id,
        user=current_user,
        db=db,
    )


# ------------------------------------------------------------------------------
# Instructor & Admin Auditing Endpoints
# ------------------------------------------------------------------------------

@router.get(
    "/assessments/{assessment_id}/overview",
    response_model=AssessmentProctoringOverviewResponse,
    summary="Get cohort proctoring overview and candidate audit summaries",
)
async def get_assessment_proctoring_overview(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> AssessmentProctoringOverviewResponse:
    """Returns assessment-level proctoring statistics, flagged candidates, and telemetry."""
    return await proctoring_service.get_assessment_overview(
        assessment_id=assessment_id,
        user=current_user,
        db=db,
    )


@router.get(
    "/assessments/{assessment_id}/events",
    response_model=List[ProctoringEventResponse],
    summary="Get filterable proctoring events for an assessment",
)
async def get_assessment_events(
    assessment_id: uuid.UUID,
    candidate_id: Optional[uuid.UUID] = Query(None, description="Filter by candidate user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> List[ProctoringEventResponse]:
    """Allows instructors and admins to inspect raw proctoring events."""
    # Authorization check
    ass_stmt = select(Assessment).where(Assessment.id == assessment_id)
    ass_res = await db.execute(ass_stmt)
    assessment = ass_res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    user_role_names = {r.name.upper() for r in current_user.roles}
    if "ADMIN" not in user_role_names and assessment.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view events for this assessment.",
        )

    stmt = select(ProctoringEvent).where(ProctoringEvent.assessment_id == assessment_id)
    if candidate_id:
        stmt = stmt.where(ProctoringEvent.user_id == candidate_id)
    if event_type:
        stmt = stmt.where(ProctoringEvent.event_type == event_type.strip().upper())
    if severity:
        stmt = stmt.where(ProctoringEvent.severity == severity.strip().upper())

    stmt = stmt.order_by(ProctoringEvent.recorded_at.desc()).limit(500)
    res = await db.execute(stmt)
    events = res.scalars().all()

    return [
        ProctoringEventResponse(
            id=ev.id,
            proctoring_session_id=ev.proctoring_session_id,
            assessment_attempt_id=ev.assessment_attempt_id,
            assessment_id=ev.assessment_id,
            user_id=ev.user_id,
            event_type=ev.event_type,
            severity=ev.severity,
            event_metadata=ev.event_metadata,
            recorded_at=ev.recorded_at,
            created_at=ev.created_at,
        )
        for ev in events
    ]


@router.get(
    "/assessments/{assessment_id}/alerts",
    response_model=List[ProctoringAlertResponse],
    summary="Get suspicious activity alerts for an assessment",
)
async def get_assessment_alerts(
    assessment_id: uuid.UUID,
    review_status: Optional[str] = Query(None, description="Filter by review status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> List[ProctoringAlertResponse]:
    """Returns suspicious activity alerts generated for an assessment."""
    ass_stmt = select(Assessment).where(Assessment.id == assessment_id)
    ass_res = await db.execute(ass_stmt)
    assessment = ass_res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    user_role_names = {r.name.upper() for r in current_user.roles}
    if "ADMIN" not in user_role_names and assessment.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view alerts for this assessment.",
        )

    stmt = (
        select(ProctoringAlert)
        .options(selectinload(ProctoringAlert.reviewer))
        .where(ProctoringAlert.assessment_id == assessment_id)
    )
    if review_status:
        stmt = stmt.where(ProctoringAlert.review_status == review_status.strip().upper())
    if severity:
        stmt = stmt.where(ProctoringAlert.severity == severity.strip().upper())

    stmt = stmt.order_by(ProctoringAlert.created_at.desc())
    res = await db.execute(stmt)
    alerts = res.scalars().all()

    return [
        ProctoringAlertResponse(
            id=a.id,
            proctoring_session_id=a.proctoring_session_id,
            assessment_attempt_id=a.assessment_attempt_id,
            assessment_id=a.assessment_id,
            user_id=a.user_id,
            alert_category=a.alert_category,
            severity=a.severity,
            explanation=a.explanation,
            related_event_ids=a.related_event_ids,
            review_status=a.review_status,
            reviewed_by=a.reviewed_by,
            reviewer_name=a.reviewer.full_name if a.reviewer else None,
            review_notes=a.review_notes,
            created_at=a.created_at,
            reviewed_at=a.reviewed_at,
        )
        for a in alerts
    ]


@router.get(
    "/attempts/{attempt_id}/report",
    response_model=AttemptProctoringReportResponse,
    summary="Get detailed proctoring audit report for an assessment attempt",
)
async def get_attempt_proctoring_report(
    attempt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttemptProctoringReportResponse:
    """
    Returns full proctoring audit report with event summaries, alerts,
    and event timelines. Accessible by authorized instructors, admins, or the candidate themselves.
    """
    return await proctoring_service.get_attempt_report(
        attempt_id=attempt_id,
        user=current_user,
        db=db,
    )


@router.patch(
    "/alerts/{alert_id}/review",
    response_model=ProctoringAlertResponse,
    summary="Instructor review and resolution of a suspicious activity alert",
)
async def review_proctoring_alert(
    alert_id: uuid.UUID,
    payload: ProctoringAlertReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> ProctoringAlertResponse:
    """Allows authorized instructors to update alert review status with audit notes."""
    return await proctoring_service.review_alert(
        alert_id=alert_id,
        review_status=payload.review_status,
        review_notes=payload.review_notes,
        user=current_user,
        db=db,
    )
