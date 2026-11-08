r"""
Proctoring Service & Rule-Based Suspicious Activity Engine
Project: Vedantu Online Coding Assessment Platform (Phase 7)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.proctoring_alert import ProctoringAlert
from app.models.proctoring_event import ProctoringEvent
from app.models.proctoring_session import ProctoringSession
from app.models.user import User
from app.schemas.proctoring import (
    DEFAULT_PROCTORING_CONFIG,
    PRIVACY_DISCLOSURE_TEXT,
    AssessmentProctoringOverviewResponse,
    AttemptProctoringReportResponse,
    CandidateProctoringSummary,
    ProctoringAlertResponse,
    ProctoringEventCreate,
    ProctoringEventResponse,
    ProctoringSessionStartResponse,
    ProctoringSessionStatusResponse,
)


def _get_effective_config(assessment: Assessment) -> Dict[str, Any]:
    """Merges assessment proctoring configuration with platform defaults."""
    config = dict(DEFAULT_PROCTORING_CONFIG)
    if assessment.proctoring_config and isinstance(assessment.proctoring_config, dict):
        config.update(assessment.proctoring_config)
    return config


class ProctoringService:
    """
    Orchestrates proctoring session lifecycles, event ingestion,
    transparent rule-based suspicious activity detection, and instructor auditing.
    """

    async def start_session(
        self,
        assessment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> ProctoringSessionStartResponse:
        """
        Initializes or resumes a proctoring session for a candidate's active assessment attempt.
        Validates attempt ownership and ensures the exam attempt is currently IN_PROGRESS.
        """
        # 1. Fetch attempt and assessment
        stmt = (
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.assessment))
            .where(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.assessment_id == assessment_id,
            )
        )
        res = await db.execute(stmt)
        attempt = res.scalar_one_or_none()

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment attempt not found.",
            )

        if attempt.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to start a proctoring session for this attempt.",
            )

        if attempt.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot initiate proctoring on an attempt with status: {attempt.status}.",
            )

        assessment = attempt.assessment
        monitoring_config = _get_effective_config(assessment)

        # 2. Check for existing session
        sess_stmt = select(ProctoringSession).where(
            ProctoringSession.assessment_attempt_id == attempt_id
        )
        sess_res = await db.execute(sess_stmt)
        session = sess_res.scalar_one_or_none()

        if not session:
            session = ProctoringSession(
                id=uuid.uuid4(),
                assessment_attempt_id=attempt_id,
                assessment_id=assessment_id,
                user_id=user.id,
                status="INITIALIZED",
                consent_given=False,
                monitoring_config=monitoring_config,
                started_at=None,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        return ProctoringSessionStartResponse(
            session_id=session.id,
            assessment_id=assessment_id,
            attempt_id=attempt_id,
            status=session.status,
            consent_given=session.consent_given,
            consent_required=not session.consent_given,
            monitoring_config=monitoring_config,
            privacy_notice=PRIVACY_DISCLOSURE_TEXT,
        )

    async def record_consent(
        self,
        session_id: uuid.UUID,
        consent: bool,
        user: User,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Records explicit candidate consent to the assessment integrity monitoring."""
        stmt = select(ProctoringSession).where(ProctoringSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found.",
            )

        if session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to this proctoring session.",
            )

        now = datetime.now(timezone.utc)
        session.consent_given = consent
        session.consent_timestamp = now
        if consent:
            session.status = "ACTIVE"
            if not session.started_at:
                session.started_at = now
            session.last_heartbeat_at = now

        await db.commit()
        await db.refresh(session)

        return {
            "session_id": session.id,
            "status": session.status,
            "consent_given": session.consent_given,
            "consent_timestamp": session.consent_timestamp,
        }

    async def record_events(
        self,
        session_id: uuid.UUID,
        events_data: List[ProctoringEventCreate],
        user: User,
        db: AsyncSession,
    ) -> List[ProctoringEventResponse]:
        """
        Records candidate-side proctoring events and triggers transparent
        rule-based suspicious activity evaluation.
        """
        # 1. Fetch session and active attempt
        stmt = (
            select(ProctoringSession)
            .options(selectinload(ProctoringSession.attempt))
            .where(ProctoringSession.id == session_id)
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found.",
            )

        if session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to this proctoring session.",
            )

        if session.status in ("ENDED", "TERMINATED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record events for a proctoring session that is {session.status}.",
            )

        if session.attempt.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record events for an attempt that is {session.attempt.status}.",
            )

        now = datetime.now(timezone.utc)
        created_events: List[ProctoringEvent] = []

        for item in events_data:
            rec_time = item.recorded_at or now
            event = ProctoringEvent(
                id=uuid.uuid4(),
                proctoring_session_id=session.id,
                assessment_attempt_id=session.assessment_attempt_id,
                assessment_id=session.assessment_id,
                user_id=user.id,
                event_type=item.event_type.strip().upper(),
                severity=item.severity.strip().upper() if item.severity else "LOW",
                event_metadata=item.event_metadata or {},
                recorded_at=rec_time,
                created_at=now,
            )
            db.add(event)
            created_events.append(event)

        session.last_heartbeat_at = now
        await db.commit()

        for ev in created_events:
            await db.refresh(ev)

        # 2. Run rule-based suspicious activity detection
        await self._evaluate_suspicious_activity(session, db)

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
            for ev in created_events
        ]

    async def _evaluate_suspicious_activity(
        self,
        session: ProctoringSession,
        db: AsyncSession,
    ) -> None:
        """
        Transparent rule-based detection engine.
        Evaluates event frequencies against configured thresholds,
        prevents duplicate alerts for the same pattern, and creates auditable alert records.
        """
        # Fetch all events recorded for this session
        ev_stmt = (
            select(ProctoringEvent)
            .where(ProctoringEvent.proctoring_session_id == session.id)
            .order_by(ProctoringEvent.recorded_at.asc())
        )
        ev_res = await db.execute(ev_stmt)
        events = ev_res.scalars().all()

        # Fetch existing alerts to prevent duplicate generation
        alert_stmt = select(ProctoringAlert).where(
            ProctoringAlert.proctoring_session_id == session.id
        )
        alert_res = await db.execute(alert_stmt)
        existing_alerts = alert_res.scalars().all()
        existing_categories: Set[Tuple[str, str]] = {
            (a.alert_category, a.severity) for a in existing_alerts
        }

        config = session.monitoring_config or DEFAULT_PROCTORING_CONFIG
        max_tab_warn = config.get("max_tab_switches_warning", 2)
        max_tab_alert = config.get("max_tab_switches_alert", 4)
        max_blur_secs = config.get("max_blur_seconds_alert", 60)
        max_fullscreen_exits = config.get("max_fullscreen_exits_alert", 3)
        require_fullscreen = config.get("require_fullscreen", True)

        now = datetime.now(timezone.utc)

        # ----------------------------------------------------------------------
        # Rule 1: Repeated Tab Switching
        # ----------------------------------------------------------------------
        tab_switch_events = [e for e in events if e.event_type in ("TAB_SWITCH", "PAGE_HIDDEN")]
        tab_count = len(tab_switch_events)

        if tab_count >= max_tab_alert:
            if ("REPEATED_TAB_SWITCHING", "HIGH") not in existing_categories:
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="REPEATED_TAB_SWITCHING",
                    severity="HIGH",
                    explanation=(
                        f"Candidate switched browser tabs or minimized assessment window {tab_count} times "
                        f"(Alert threshold: {max_tab_alert})."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in tab_switch_events[-5:]]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("REPEATED_TAB_SWITCHING", "HIGH"))
        elif tab_count >= max_tab_warn:
            if (
                ("REPEATED_TAB_SWITCHING", "MEDIUM") not in existing_categories
                and ("REPEATED_TAB_SWITCHING", "HIGH") not in existing_categories
            ):
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="REPEATED_TAB_SWITCHING",
                    severity="MEDIUM",
                    explanation=(
                        f"Candidate switched browser tabs {tab_count} times "
                        f"(Warning threshold: {max_tab_warn})."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in tab_switch_events]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("REPEATED_TAB_SWITCHING", "MEDIUM"))

        # ----------------------------------------------------------------------
        # Rule 2: Excessive Focus Loss / Window Blur
        # ----------------------------------------------------------------------
        blur_events = [e for e in events if e.event_type == "WINDOW_BLUR"]
        blur_count = len(blur_events)
        total_blur_duration = sum(
            float((e.event_metadata or {}).get("blur_duration_seconds", 0.0))
            for e in blur_events
        )

        if total_blur_duration >= max_blur_secs or blur_count >= 5:
            if ("EXCESSIVE_FOCUS_LOSS", "HIGH") not in existing_categories:
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="EXCESSIVE_FOCUS_LOSS",
                    severity="HIGH",
                    explanation=(
                        f"Candidate browser window lost focus {blur_count} times totaling "
                        f"{int(total_blur_duration)}s out of window focus (Threshold: {max_blur_secs}s)."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in blur_events[-5:]]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("EXCESSIVE_FOCUS_LOSS", "HIGH"))
        elif blur_count >= 3:
            if (
                ("EXCESSIVE_FOCUS_LOSS", "MEDIUM") not in existing_categories
                and ("EXCESSIVE_FOCUS_LOSS", "HIGH") not in existing_categories
            ):
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="EXCESSIVE_FOCUS_LOSS",
                    severity="MEDIUM",
                    explanation=(
                        f"Candidate browser window lost focus {blur_count} times during assessment."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in blur_events]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("EXCESSIVE_FOCUS_LOSS", "MEDIUM"))

        # ----------------------------------------------------------------------
        # Rule 3: Repeated Fullscreen Exits
        # ----------------------------------------------------------------------
        if require_fullscreen:
            fullscreen_exits = [e for e in events if e.event_type == "FULLSCREEN_EXIT"]
            fs_count = len(fullscreen_exits)
            if fs_count >= max_fullscreen_exits:
                if ("REPEATED_FULLSCREEN_EXIT", "HIGH") not in existing_categories:
                    alert = ProctoringAlert(
                        id=uuid.uuid4(),
                        proctoring_session_id=session.id,
                        assessment_attempt_id=session.assessment_attempt_id,
                        assessment_id=session.assessment_id,
                        user_id=session.user_id,
                        alert_category="REPEATED_FULLSCREEN_EXIT",
                        severity="HIGH",
                        explanation=(
                            f"Candidate exited required fullscreen examination mode {fs_count} times "
                            f"(Alert threshold: {max_fullscreen_exits})."
                        ),
                        related_event_ids={"event_ids": [str(e.id) for e in fullscreen_exits[-5:]]},
                        review_status="PENDING",
                        created_at=now,
                    )
                    db.add(alert)
                    existing_categories.add(("REPEATED_FULLSCREEN_EXIT", "HIGH"))
            elif fs_count >= 2:
                if (
                    ("REPEATED_FULLSCREEN_EXIT", "MEDIUM") not in existing_categories
                    and ("REPEATED_FULLSCREEN_EXIT", "HIGH") not in existing_categories
                ):
                    alert = ProctoringAlert(
                        id=uuid.uuid4(),
                        proctoring_session_id=session.id,
                        assessment_attempt_id=session.assessment_attempt_id,
                        assessment_id=session.assessment_id,
                        user_id=session.user_id,
                        alert_category="REPEATED_FULLSCREEN_EXIT",
                        severity="MEDIUM",
                        explanation=(
                            f"Candidate exited fullscreen examination mode {fs_count} times."
                        ),
                        related_event_ids={"event_ids": [str(e.id) for e in fullscreen_exits]},
                        review_status="PENDING",
                        created_at=now,
                    )
                    db.add(alert)
                    existing_categories.add(("REPEATED_FULLSCREEN_EXIT", "MEDIUM"))

        # ----------------------------------------------------------------------
        # Rule 4: Unexpected Navigation or Page Reload
        # ----------------------------------------------------------------------
        reload_events = [e for e in events if e.event_type == "PAGE_RELOADED"]
        reload_count = len(reload_events)
        if reload_count >= 2:
            severity = "HIGH" if reload_count >= 4 else "MEDIUM"
            if ("UNEXPECTED_NAVIGATION", severity) not in existing_categories:
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="UNEXPECTED_NAVIGATION",
                    severity=severity,
                    explanation=(
                        f"Candidate reloaded or navigated the examination page {reload_count} times."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in reload_events]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("UNEXPECTED_NAVIGATION", severity))

        # ----------------------------------------------------------------------
        # Rule 5: Multiple Suspicious Event Cluster
        # ----------------------------------------------------------------------
        suspicious_events = [
            e for e in events
            if e.event_type in ("TAB_SWITCH", "WINDOW_BLUR", "FULLSCREEN_EXIT", "PAGE_HIDDEN", "PAGE_RELOADED")
        ]
        if len(suspicious_events) >= 8:
            if ("MULTIPLE_SUSPICIOUS_EVENTS", "HIGH") not in existing_categories:
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="MULTIPLE_SUSPICIOUS_EVENTS",
                    severity="HIGH",
                    explanation=(
                        f"Candidate triggered {len(suspicious_events)} aggregate integrity events "
                        f"(tab switches, focus losses, and fullscreen exits) during this assessment."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in suspicious_events[-8:]]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("MULTIPLE_SUSPICIOUS_EVENTS", "HIGH"))

        # ----------------------------------------------------------------------
        # Rule 6: Camera Policy Event (Technical audit only)
        # ----------------------------------------------------------------------
        if config.get("enable_webcam", False):
            camera_denied_events = [
                e for e in events
                if e.event_type in ("CAMERA_PERMISSION_DENIED", "CAMERA_UNAVAILABLE", "CAMERA_INTERRUPTED")
            ]
            if camera_denied_events and ("CAMERA_POLICY_VIOLATION", "LOW") not in existing_categories:
                alert = ProctoringAlert(
                    id=uuid.uuid4(),
                    proctoring_session_id=session.id,
                    assessment_attempt_id=session.assessment_attempt_id,
                    assessment_id=session.assessment_id,
                    user_id=session.user_id,
                    alert_category="CAMERA_POLICY_VIOLATION",
                    severity="LOW",
                    explanation=(
                        "Candidate's camera permission was denied, unavailable, or interrupted. "
                        "Recorded as a technical policy notice for instructor audit."
                    ),
                    related_event_ids={"event_ids": [str(e.id) for e in camera_denied_events]},
                    review_status="PENDING",
                    created_at=now,
                )
                db.add(alert)
                existing_categories.add(("CAMERA_POLICY_VIOLATION", "LOW"))

        await db.commit()

    async def record_heartbeat(
        self,
        session_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Candidate keepalive heartbeat every 15-30s."""
        stmt = select(ProctoringSession).where(ProctoringSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found.",
            )

        if session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to this proctoring session.",
            )

        now = datetime.now(timezone.utc)
        session.last_heartbeat_at = now
        await db.commit()

        return {"session_id": session.id, "last_heartbeat_at": now, "status": session.status}

    async def end_session(
        self,
        session_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Gracefully terminates proctoring monitoring upon exam completion."""
        stmt = select(ProctoringSession).where(ProctoringSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found.",
            )

        if session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to this proctoring session.",
            )

        now = datetime.now(timezone.utc)
        session.status = "ENDED"
        session.ended_at = now
        await db.commit()

        return {"session_id": session.id, "status": "ENDED", "ended_at": now}

    async def get_session_status(
        self,
        session_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> ProctoringSessionStatusResponse:
        """Returns candidate-facing proctoring session telemetry."""
        stmt = (
            select(ProctoringSession)
            .options(
                selectinload(ProctoringSession.events),
                selectinload(ProctoringSession.alerts),
            )
            .where(ProctoringSession.id == session_id)
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring session not found.",
            )

        if session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to this proctoring session.",
            )

        return ProctoringSessionStatusResponse(
            session_id=session.id,
            assessment_id=session.assessment_id,
            attempt_id=session.assessment_attempt_id,
            status=session.status,
            consent_given=session.consent_given,
            monitoring_config=session.monitoring_config or DEFAULT_PROCTORING_CONFIG,
            total_events=len(session.events),
            alert_count=len(session.alerts),
            is_active=session.status == "ACTIVE",
        )

    # --------------------------------------------------------------------------
    # Instructor & Admin Auditing Endpoints
    # --------------------------------------------------------------------------

    async def get_assessment_overview(
        self,
        assessment_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> AssessmentProctoringOverviewResponse:
        """Aggregates proctoring statistics across all candidates for an assessment."""
        # 1. Verify assessment exists and user has access
        ass_stmt = select(Assessment).where(Assessment.id == assessment_id)
        ass_res = await db.execute(ass_stmt)
        assessment = ass_res.scalar_one_or_none()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found.",
            )

        user_role_names = {r.name.upper() for r in user.roles}
        if "ADMIN" not in user_role_names and assessment.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view proctoring data for this assessment.",
            )

        # 2. Fetch all attempts and proctoring sessions for this assessment
        att_stmt = (
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.user))
            .where(AssessmentAttempt.assessment_id == assessment_id)
        )
        att_res = await db.execute(att_stmt)
        attempts = att_res.scalars().all()

        sess_stmt = (
            select(ProctoringSession)
            .options(
                selectinload(ProctoringSession.events),
                selectinload(ProctoringSession.alerts),
            )
            .where(ProctoringSession.assessment_id == assessment_id)
        )
        sess_res = await db.execute(sess_stmt)
        sessions = {s.assessment_attempt_id: s for s in sess_res.scalars().all()}

        candidates_summary: List[CandidateProctoringSummary] = []
        total_alerts = 0
        high_severity_alerts = 0
        flagged_candidates = 0

        for att in attempts:
            sess = sessions.get(att.id)
            if sess:
                total_ev = len(sess.events)
                tab_switches = sum(1 for e in sess.events if e.event_type in ("TAB_SWITCH", "PAGE_HIDDEN"))
                fs_exits = sum(1 for e in sess.events if e.event_type == "FULLSCREEN_EXIT")
                blurs = sum(1 for e in sess.events if e.event_type == "WINDOW_BLUR")
                alerts_cnt = len(sess.alerts)
                high_cnt = sum(1 for a in sess.alerts if a.severity == "HIGH")

                total_alerts += alerts_cnt
                high_severity_alerts += high_cnt
                if alerts_cnt > 0:
                    flagged_candidates += 1

                review_stat = "PENDING"
                if sess.alerts:
                    if all(a.review_status == "CLEARED" for a in sess.alerts):
                        review_stat = "CLEARED"
                    elif any(a.review_status == "ESCALATED" for a in sess.alerts):
                        review_stat = "ESCALATED"
                    elif all(a.review_status in ("REVIEWED", "CLEARED") for a in sess.alerts):
                        review_stat = "REVIEWED"

                candidates_summary.append(
                    CandidateProctoringSummary(
                        user_id=att.user_id,
                        full_name=att.user.full_name,
                        email=att.user.email,
                        attempt_id=att.id,
                        attempt_status=att.status,
                        session_id=sess.id,
                        session_status=sess.status,
                        consent_given=sess.consent_given,
                        total_events=total_ev,
                        tab_switch_count=tab_switches,
                        fullscreen_exit_count=fs_exits,
                        window_blur_count=blurs,
                        total_alerts=alerts_cnt,
                        high_severity_alerts=high_cnt,
                        review_status=review_stat,
                        last_heartbeat_at=sess.last_heartbeat_at,
                    )
                )
            else:
                candidates_summary.append(
                    CandidateProctoringSummary(
                        user_id=att.user_id,
                        full_name=att.user.full_name,
                        email=att.user.email,
                        attempt_id=att.id,
                        attempt_status=att.status,
                        session_id=None,
                        session_status=None,
                        consent_given=False,
                        total_events=0,
                        tab_switch_count=0,
                        fullscreen_exit_count=0,
                        window_blur_count=0,
                        total_alerts=0,
                        high_severity_alerts=0,
                        review_status="N/A",
                        last_heartbeat_at=None,
                    )
                )

        return AssessmentProctoringOverviewResponse(
            assessment_id=assessment.id,
            title=assessment.title,
            total_candidates=len(attempts),
            monitored_sessions=len(sessions),
            flagged_candidates=flagged_candidates,
            total_alerts=total_alerts,
            high_severity_alerts=high_severity_alerts,
            monitoring_config=_get_effective_config(assessment),
            candidates=candidates_summary,
        )

    async def get_attempt_report(
        self,
        attempt_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> AttemptProctoringReportResponse:
        """Full proctoring audit report for a specific attempt."""
        stmt = (
            select(AssessmentAttempt)
            .options(
                selectinload(AssessmentAttempt.assessment),
                selectinload(AssessmentAttempt.user),
            )
            .where(AssessmentAttempt.id == attempt_id)
        )
        res = await db.execute(stmt)
        attempt = res.scalar_one_or_none()

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment attempt not found.",
            )

        # Authorization: Student can only view own completed attempt; instructor/admin can view if creator/admin
        user_role_names = {r.name.upper() for r in user.roles}
        is_staff = "ADMIN" in user_role_names or ("INSTRUCTOR" in user_role_names and attempt.assessment.created_by == user.id)
        is_owner_student = attempt.user_id == user.id

        if not is_staff and not is_owner_student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view proctoring records for this attempt.",
            )

        # Fetch session
        sess_stmt = (
            select(ProctoringSession)
            .options(
                selectinload(ProctoringSession.events),
                selectinload(ProctoringSession.alerts).selectinload(ProctoringAlert.reviewer),
            )
            .where(ProctoringSession.assessment_attempt_id == attempt_id)
        )
        sess_res = await db.execute(sess_stmt)
        session = sess_res.scalar_one_or_none()

        if not session:
            # Attempt exists but proctoring was not initiated
            return AttemptProctoringReportResponse(
                attempt_id=attempt.id,
                assessment_id=attempt.assessment_id,
                user_id=attempt.user_id,
                candidate_name=attempt.user.full_name,
                candidate_email=attempt.user.email,
                session_id=None,
                session_status=None,
                consent_given=False,
                consent_timestamp=None,
                started_at=None,
                ended_at=None,
                monitoring_config=_get_effective_config(attempt.assessment),
                event_summary={},
                alerts=[],
                events=[],
            )

        event_summary: Dict[str, int] = {}
        for ev in session.events:
            event_summary[ev.event_type] = event_summary.get(ev.event_type, 0) + 1

        alert_responses = [
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
            for a in session.alerts
        ]

        event_responses = [
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
            for ev in session.events
        ]

        return AttemptProctoringReportResponse(
            attempt_id=attempt.id,
            assessment_id=attempt.assessment_id,
            user_id=attempt.user_id,
            candidate_name=attempt.user.full_name,
            candidate_email=attempt.user.email,
            session_id=session.id,
            session_status=session.status,
            consent_given=session.consent_given,
            consent_timestamp=session.consent_timestamp,
            started_at=session.started_at,
            ended_at=session.ended_at,
            monitoring_config=session.monitoring_config or DEFAULT_PROCTORING_CONFIG,
            event_summary=event_summary,
            alerts=alert_responses,
            events=event_responses,
        )

    async def review_alert(
        self,
        alert_id: uuid.UUID,
        review_status: str,
        review_notes: Optional[str],
        user: User,
        db: AsyncSession,
    ) -> ProctoringAlertResponse:
        """
        Updates review status on a proctoring alert with instructor audit trail.
        Allowed statuses: PENDING, REVIEWED, CLEARED, ESCALATED.
        """
        valid_statuses = {"PENDING", "REVIEWED", "CLEARED", "ESCALATED"}
        clean_status = review_status.strip().upper()
        if clean_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid review status: '{review_status}'. Must be one of {valid_statuses}.",
            )

        stmt = (
            select(ProctoringAlert)
            .options(
                selectinload(ProctoringAlert.reviewer),
                selectinload(ProctoringAlert.session).selectinload(ProctoringSession.assessment),
            )
            .where(ProctoringAlert.id == alert_id)
        )
        res = await db.execute(stmt)
        alert = res.scalar_one_or_none()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proctoring alert not found.",
            )

        # Authorization: Must be admin or instructor of this assessment
        user_role_names = {r.name.upper() for r in user.roles}
        if "ADMIN" not in user_role_names and alert.session.assessment.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to review alerts for this assessment.",
            )

        now = datetime.now(timezone.utc)
        alert.review_status = clean_status
        alert.reviewed_by = user.id
        alert.review_notes = review_notes
        alert.reviewed_at = now

        await db.commit()
        await db.refresh(alert)

        return ProctoringAlertResponse(
            id=alert.id,
            proctoring_session_id=alert.proctoring_session_id,
            assessment_attempt_id=alert.assessment_attempt_id,
            assessment_id=alert.assessment_id,
            user_id=alert.user_id,
            alert_category=alert.alert_category,
            severity=alert.severity,
            explanation=alert.explanation,
            related_event_ids=alert.related_event_ids,
            review_status=alert.review_status,
            reviewed_by=alert.reviewed_by,
            reviewer_name=user.full_name,
            review_notes=alert.review_notes,
            created_at=alert.created_at,
            reviewed_at=alert.reviewed_at,
        )


proctoring_service = ProctoringService()
