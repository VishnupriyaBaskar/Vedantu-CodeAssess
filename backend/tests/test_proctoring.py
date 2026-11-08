r"""
Test Suite for Phase 7: Advanced Proctoring with Privacy Safeguards
Project: Vedantu Online Coding Assessment Platform (Phase 7)
Workspace: E:\VedantuCodingPlatform_New

Verifies:
1. Proctoring session creation, defaults, and configuration hydration.
2. Candidate consent recording and status transition (INITIALIZED -> ACTIVE).
3. Candidate data isolation and ownership enforcement (cross-user access rejected).
4. Rejection of events on completed or invalid attempts.
5. Event ingestion (tab switch, window blur/focus, fullscreen, technical camera events) and heartbeats.
6. Rule-based suspicious activity detection (repeated tab switching, window blur, fullscreen exits).
7. Duplicate alert prevention and severity escalation.
8. Camera policy violation advisory logging without automated disqualification.
9. Instructor and admin cohort proctoring overview, events list, and alerts list.
10. Instructor alert review workflow (PENDING -> REVIEWED -> CLEARED / ESCALATED).
11. Clean session termination.
"""

from datetime import datetime, timezone
import sys
from typing import Optional, Tuple
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import async_session_factory
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.proctoring_alert import ProctoringAlert
from app.models.proctoring_event import ProctoringEvent
from app.models.proctoring_session import ProctoringSession
from app.models.role import Role, UserRole
from app.models.user import User


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _create_test_user(email_prefix: str, role_name: str) -> tuple[User, str]:
    """Helper to provision test user with specified role and return (user, token)."""
    clean_role = role_name.upper()
    suffix = uuid.uuid4().hex[:8]
    email = f"{email_prefix}_{suffix}@vedantu-test.com"

    async with async_session_factory() as session:
        async with session.begin():
            stmt_role = select(Role).where(Role.name == clean_role)
            role = (await session.execute(stmt_role)).scalar_one_or_none()
            if not role:
                role = Role(name=clean_role, description=f"Role {clean_role}")
                session.add(role)
                await session.flush()

            user = User(
                full_name=f"Test {clean_role.capitalize()} User",
                email=email,
                password_hash=hash_password("SecurePass123!"),
                status="ACTIVE",
            )
            session.add(user)
            await session.flush()

            user_role = UserRole(user_id=user.id, role_id=role.id)
            session.add(user_role)

        stmt_load = select(User).options(selectinload(User.roles)).where(User.id == user.id)
        loaded_user = (await session.execute(stmt_load)).scalar_one()

    token, _, _ = create_access_token(
        subject=str(loaded_user.id),
        roles=[clean_role],
        extra_claims={"email": loaded_user.email},
    )
    return loaded_user, token


async def _create_test_assessment(instructor: User, proctoring_config: Optional[dict] = None) -> Assessment:
    """Helper to provision test assessment."""
    async with async_session_factory() as session:
        ass_id = uuid.uuid4()
        assessment = Assessment(
            id=ass_id,
            title=f"Proctoring Assessment {ass_id.hex[:6]}",
            description="Testing proctoring engine",
            instructions="Strict proctored test",
            duration_minutes=60,
            total_marks=100,
            passing_marks=40,
            difficulty="MEDIUM",
            status="PUBLISHED",
            allowed_languages="ALL_ACTIVE",
            created_by=instructor.id,
            proctoring_config=proctoring_config,
        )
        session.add(assessment)
        await session.commit()
        await session.refresh(assessment)
        return assessment


async def _create_test_attempt(assessment: Assessment, student: User, status_str: str = "IN_PROGRESS") -> AssessmentAttempt:
    """Helper to provision test attempt."""
    async with async_session_factory() as session:
        att_id = uuid.uuid4()
        attempt = AssessmentAttempt(
            id=att_id,
            assessment_id=assessment.id,
            user_id=student.id,
            status=status_str,
            started_at=datetime.now(timezone.utc),
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
        return attempt


# ------------------------------------------------------------------------------
# Test 1: Proctoring Session Start & Defaults
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_proctoring_session_start_and_defaults():
    instructor, _ = await _create_test_user("inst_proc", "instructor")
    student, student_token = await _create_test_user("stud_proc", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "INITIALIZED"
        assert data["consent_given"] is False
        assert data["consent_required"] is True
        assert "privacy_notice" in data
        assert data["monitoring_config"]["require_fullscreen"] is True
        assert data["monitoring_config"]["enable_webcam"] is False


# ------------------------------------------------------------------------------
# Test 2: Consent Submission
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_proctoring_session_consent():
    instructor, _ = await _create_test_user("inst_proc2", "instructor")
    student, student_token = await _create_test_user("stud_proc2", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Start session
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]

        # 2. Record consent
        consent_res = await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert consent_res.status_code == 200
        c_data = consent_res.json()
        assert c_data["status"] == "ACTIVE"
        assert c_data["consent_given"] is True
        assert c_data["consent_timestamp"] is not None


# ------------------------------------------------------------------------------
# Test 3: Candidate Data Isolation
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_candidate_data_isolation():
    instructor, _ = await _create_test_user("inst_proc3", "instructor")
    student_a, student_a_token = await _create_test_user("stud_a", "student")
    student_b, student_b_token = await _create_test_user("stud_b", "student")
    assessment = await _create_test_assessment(instructor)
    attempt_a = await _create_test_attempt(assessment, student_a)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Student A starts session
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt_a.id)},
            headers={"Authorization": f"Bearer {student_a_token}"},
        )
        session_id = start_res.json()["session_id"]

        # Student B attempts to start/resume Student A's attempt -> 403
        bad_start = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt_a.id)},
            headers={"Authorization": f"Bearer {student_b_token}"},
        )
        assert bad_start.status_code == 403

        # Student B attempts to post events to Student A's session -> 403
        bad_event = await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={"events": [{"event_type": "TAB_SWITCH"}]},
            headers={"Authorization": f"Bearer {student_b_token}"},
        )
        assert bad_event.status_code == 403


# ------------------------------------------------------------------------------
# Test 4: Rejection on Completed or Non-Existent Attempt
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_reject_completed_or_invalid_attempt():
    instructor, _ = await _create_test_user("inst_proc4", "instructor")
    student, student_token = await _create_test_user("stud_proc4", "student")
    assessment = await _create_test_assessment(instructor)
    completed_attempt = await _create_test_attempt(assessment, student, status_str="COMPLETED")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Attempt is completed -> 400
        res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(completed_attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res.status_code == 400
        assert "COMPLETED" in res.json()["detail"]

        # Non-existent attempt -> 404
        bad_uuid = str(uuid.uuid4())
        res_404 = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": bad_uuid},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res_404.status_code == 404


# ------------------------------------------------------------------------------
# Test 5: Event Ingestion & Heartbeat
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_event_ingestion_and_heartbeat():
    instructor, _ = await _create_test_user("inst_proc5", "instructor")
    student, student_token = await _create_test_user("stud_proc5", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Ingest events
        event_res = await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={
                "events": [
                    {"event_type": "FULLSCREEN_ENTER", "severity": "LOW"},
                    {"event_type": "WINDOW_FOCUS", "severity": "LOW"},
                ]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert event_res.status_code == 200
        events = event_res.json()
        assert len(events) == 2
        assert events[0]["event_type"] == "FULLSCREEN_ENTER"

        # Heartbeat
        hb_res = await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/heartbeat",
            json={},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert hb_res.status_code == 200
        assert hb_res.json()["last_heartbeat_at"] is not None


# ------------------------------------------------------------------------------
# Test 6: Rule 1 - Repeated Tab Switching & Deduplication
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_rule_repeated_tab_switching_alerts():
    instructor, _ = await _create_test_user("inst_proc6", "instructor")
    student, student_token = await _create_test_user("stud_proc6", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # 2 Tab switches -> triggers MEDIUM alert
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={
                "events": [
                    {"event_type": "TAB_SWITCH"},
                    {"event_type": "TAB_SWITCH"},
                ]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Check status
        status_res = await ac.get(
            f"/api/v1/proctoring/sessions/{session_id}/status",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert status_res.status_code == 200
        assert status_res.json()["alert_count"] >= 1

        # 2 more Tab switches (total 4) -> triggers HIGH alert
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={
                "events": [
                    {"event_type": "TAB_SWITCH"},
                    {"event_type": "TAB_SWITCH"},
                ]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Verify alerts in database
        async with async_session_factory() as db:
            alerts = (
                await db.execute(
                    select(ProctoringAlert).where(ProctoringAlert.proctoring_session_id == uuid.UUID(session_id))
                )
            ).scalars().all()
            categories = [(a.alert_category, a.severity) for a in alerts]
            assert ("REPEATED_TAB_SWITCHING", "MEDIUM") in categories
            assert ("REPEATED_TAB_SWITCHING", "HIGH") in categories


# ------------------------------------------------------------------------------
# Test 7: Rule 2 & 3 - Excessive Focus Loss and Fullscreen Exits
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_rule_excessive_focus_loss_and_fullscreen_exits():
    instructor, _ = await _create_test_user("inst_proc7", "instructor")
    student, student_token = await _create_test_user("stud_proc7", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # 3 window blur events and 3 fullscreen exits
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={
                "events": [
                    {"event_type": "WINDOW_BLUR", "event_metadata": {"blur_duration_seconds": 15.0}},
                    {"event_type": "WINDOW_BLUR", "event_metadata": {"blur_duration_seconds": 20.0}},
                    {"event_type": "WINDOW_BLUR", "event_metadata": {"blur_duration_seconds": 10.0}},
                    {"event_type": "FULLSCREEN_EXIT"},
                    {"event_type": "FULLSCREEN_EXIT"},
                    {"event_type": "FULLSCREEN_EXIT"},
                ]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        async with async_session_factory() as db:
            alerts = (
                await db.execute(
                    select(ProctoringAlert).where(ProctoringAlert.proctoring_session_id == uuid.UUID(session_id))
                )
            ).scalars().all()
            categories = [a.alert_category for a in alerts]
            assert "EXCESSIVE_FOCUS_LOSS" in categories
            assert "REPEATED_FULLSCREEN_EXIT" in categories


# ------------------------------------------------------------------------------
# Test 8: Technical Camera Policy Alert
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_camera_policy_event_alert():
    instructor, _ = await _create_test_user("inst_proc8", "instructor")
    student, student_token = await _create_test_user("stud_proc8", "student")
    # Assessment with webcam configured
    assessment = await _create_test_assessment(instructor, proctoring_config={"enable_webcam": True})
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Candidate camera permission denied
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={
                "events": [
                    {"event_type": "CAMERA_PERMISSION_DENIED", "severity": "LOW"},
                ]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        async with async_session_factory() as db:
            alerts = (
                await db.execute(
                    select(ProctoringAlert).where(ProctoringAlert.proctoring_session_id == uuid.UUID(session_id))
                )
            ).scalars().all()
            cam_alert = next((a for a in alerts if a.alert_category == "CAMERA_POLICY_VIOLATION"), None)
            assert cam_alert is not None
            assert cam_alert.severity == "LOW"
            assert "technical policy notice" in cam_alert.explanation


# ------------------------------------------------------------------------------
# Test 9: Instructor & Admin Auditing Endpoints
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_instructor_and_admin_auditing_and_overview():
    instructor, instructor_token = await _create_test_user("inst_proc9", "instructor")
    student, student_token = await _create_test_user("stud_proc9", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Student initiates session and causes 1 event
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={"events": [{"event_type": "TAB_SWITCH"}]},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Instructor calls overview
        ov_res = await ac.get(
            f"/api/v1/proctoring/assessments/{assessment.id}/overview",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert ov_res.status_code == 200, ov_res.text
        ov_data = ov_res.json()
        assert ov_data["total_candidates"] == 1
        assert ov_data["monitored_sessions"] == 1
        assert len(ov_data["candidates"]) == 1
        assert ov_data["candidates"][0]["tab_switch_count"] == 1

        # Student trying to call instructor overview -> 403 Forbidden
        bad_ov = await ac.get(
            f"/api/v1/proctoring/assessments/{assessment.id}/overview",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert bad_ov.status_code == 403

        # Instructor fetches events
        events_res = await ac.get(
            f"/api/v1/proctoring/assessments/{assessment.id}/events",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert events_res.status_code == 200
        assert len(events_res.json()) >= 1


# ------------------------------------------------------------------------------
# Test 10: Alert Review Lifecycle (PENDING -> REVIEWED -> CLEARED)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_alert_review_lifecycle():
    instructor, instructor_token = await _create_test_user("inst_proc10", "instructor")
    student, student_token = await _create_test_user("stud_proc10", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Trigger an alert
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={
                "events": [
                    {"event_type": "TAB_SWITCH"},
                    {"event_type": "TAB_SWITCH"},
                ]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Fetch alerts
        alerts_res = await ac.get(
            f"/api/v1/proctoring/assessments/{assessment.id}/alerts",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert alerts_res.status_code == 200
        alerts = alerts_res.json()
        assert len(alerts) >= 1
        target_alert = alerts[0]
        alert_id = target_alert["id"]
        assert target_alert["review_status"] == "PENDING"

        # Instructor reviews alert
        rev_res = await ac.patch(
            f"/api/v1/proctoring/alerts/{alert_id}/review",
            json={"review_status": "REVIEWED", "review_notes": "Reviewed candidate timeline."},
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert rev_res.status_code == 200
        rev_data = rev_res.json()
        assert rev_data["review_status"] == "REVIEWED"
        assert rev_data["review_notes"] == "Reviewed candidate timeline."

        # Instructor clears alert
        clear_res = await ac.patch(
            f"/api/v1/proctoring/alerts/{alert_id}/review",
            json={"review_status": "CLEARED", "review_notes": "Confirmed non-suspicious context."},
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert clear_res.status_code == 200
        assert clear_res.json()["review_status"] == "CLEARED"


# ------------------------------------------------------------------------------
# Test 11: Clean Session End & Cleanup
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_proctoring_session_end_and_cleanup():
    instructor, _ = await _create_test_user("inst_proc11", "instructor")
    student, student_token = await _create_test_user("stud_proc11", "student")
    assessment = await _create_test_assessment(instructor)
    attempt = await _create_test_attempt(assessment, student)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        start_res = await ac.post(
            "/api/v1/proctoring/sessions/start",
            json={"assessment_id": str(assessment.id), "attempt_id": str(attempt.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        session_id = start_res.json()["session_id"]
        await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/consent",
            json={"consent": True},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # End session
        end_res = await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/end",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert end_res.status_code == 200
        assert end_res.json()["status"] == "ENDED"

        # Subsequent event submission should be rejected -> 400
        bad_post = await ac.post(
            f"/api/v1/proctoring/sessions/{session_id}/events",
            json={"events": [{"event_type": "TAB_SWITCH"}]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert bad_post.status_code == 400
        assert "ENDED" in bad_post.json()["detail"]
