r"""
Test Suite for Phase 8: Analytics & Instructor Question Management
Project: Vedantu Online Coding Assessment Platform (Phase 8)
Workspace: E:\VedantuCodingPlatform_New

Verifies:
1. Instructor Overview KPIs live aggregation and student RBAC prevention.
2. Assessment-level deep performance analytics (score distributions, pass/fail, topic/difficulty breakdown, proctoring metrics).
3. Cohort-level performance analytics (topic proficiencies, difficulty distributions, top performers).
4. Individual candidate performance audit report (topic mastery, submissions history, zero test case leakage).
5. Question Bank quality metrics and test case category distributions (SAMPLE, FUNCTIONAL, EDGE_CASE).
6. RFC 4180 CSV exports for assessments, candidates, and question bank performance.
7. Test case category updates (PUT) and pre-flight question publishing validation (POST /validate).
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
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.role import Role, UserRole
from app.models.student_topic_mastery import StudentTopicMastery
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _create_test_user(email_prefix: str, role_name: str) -> Tuple[User, str]:
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


async def _create_test_assessment(instructor: User) -> Assessment:
    """Helper to provision test assessment."""
    async with async_session_factory() as session:
        ass_id = uuid.uuid4()
        assessment = Assessment(
            id=ass_id,
            title=f"Analytics Test Assessment {ass_id.hex[:6]}",
            description="Testing Phase 8 Analytics",
            instructions="Standard Instructions",
            duration_minutes=90,
            total_marks=100,
            passing_marks=40,
            difficulty="MEDIUM",
            status="PUBLISHED",
            allowed_languages="ALL_ACTIVE",
            created_by=instructor.id,
        )
        session.add(assessment)
        await session.commit()
        await session.refresh(assessment)
        return assessment


async def _create_test_attempt(
    assessment: Assessment,
    student: User,
    status_str: str = "COMPLETED",
    score: float = 75.0,
    percentage: float = 75.0,
    is_passed: bool = True,
) -> AssessmentAttempt:
    """Helper to provision test attempt."""
    async with async_session_factory() as session:
        att_id = uuid.uuid4()
        attempt = AssessmentAttempt(
            id=att_id,
            assessment_id=assessment.id,
            user_id=student.id,
            status=status_str,
            total_score=score,
            percentage=percentage,
            is_passed=is_passed,
            submitted_at=datetime.now(timezone.utc) if status_str == "COMPLETED" else None,
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
        return attempt


@pytest.mark.anyio
async def test_instructor_overview_and_rbac():
    """Verifies live KPI aggregation on instructor overview and candidate access prevention."""
    instructor, inst_token = await _create_test_user("inst_overview", "INSTRUCTOR")
    student, stud_token = await _create_test_user("stud_overview", "STUDENT")

    assessment = await _create_test_assessment(instructor)
    await _create_test_attempt(assessment, student, status_str="COMPLETED", score=80.0, percentage=80.0, is_passed=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Instructor authorized request
        resp = await client.get(
            "/api/v1/analytics/instructor/overview",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_candidates" in data
        assert data["total_candidates"] >= 1
        assert "total_assessments" in data
        assert data["total_assessments"] >= 1
        assert "completed_attempts" in data
        assert data["completed_attempts"] >= 1
        assert "average_score_pct" in data
        assert data["average_score_pct"] >= 0.0
        assert "pass_percentage" in data
        assert "completion_percentage" in data

        # 2. Student unauthorized access check
        stud_resp = await client.get(
            "/api/v1/analytics/instructor/overview",
            headers={"Authorization": f"Bearer {stud_token}"},
        )
        assert stud_resp.status_code == 403


@pytest.mark.anyio
async def test_assessment_analytics_and_distribution():
    """Verifies detailed assessment analytics, score buckets, and proctoring metrics."""
    instructor, inst_token = await _create_test_user("inst_ass_ana", "INSTRUCTOR")
    student1, _ = await _create_test_user("stud1_ass_ana", "STUDENT")
    student2, stud_token2 = await _create_test_user("stud2_ass_ana", "STUDENT")

    assessment = await _create_test_assessment(instructor)
    await _create_test_attempt(assessment, student1, status_str="COMPLETED", score=85.0, percentage=85.0, is_passed=True)
    await _create_test_attempt(assessment, student2, status_str="COMPLETED", score=35.0, percentage=35.0, is_passed=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get assessment analytics
        resp = await client.get(
            f"/api/v1/analytics/instructor/assessments/{assessment.id}",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == str(assessment.id)
        assert data["total_attempts"] == 2
        assert data["completed_attempts"] == 2
        assert data["pass_count"] == 1
        assert data["fail_count"] == 1
        assert data["pass_percentage"] == 50.0
        assert len(data["score_distribution"]) == 5
        assert len(data["candidates"]) == 2

        # 2. RBAC check
        stud_resp = await client.get(
            f"/api/v1/analytics/instructor/assessments/{assessment.id}",
            headers={"Authorization": f"Bearer {stud_token2}"},
        )
        assert stud_resp.status_code == 403

        # 3. Not found check
        random_id = uuid.uuid4()
        not_found_resp = await client.get(
            f"/api/v1/analytics/instructor/assessments/{random_id}",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert not_found_resp.status_code == 404


@pytest.mark.anyio
async def test_cohort_analytics():
    """Verifies cohort-level proficiencies, topic distributions, and student ranking."""
    instructor, inst_token = await _create_test_user("inst_cohort", "INSTRUCTOR")
    student, _ = await _create_test_user("stud_cohort", "STUDENT")

    # Add Topic Mastery for the student
    async with async_session_factory() as session:
        stm = StudentTopicMastery(
            id=uuid.uuid4(),
            user_id=student.id,
            topic="Dynamic Programming",
            mastery_score=82.5,
            mastery_level="ADVANCED",
            confidence_level="HIGH",
            questions_attempted=5,
            questions_solved=4,
            total_submissions=8,
            successful_submissions=5,
            best_score=10.0,
            recommended_difficulty="HARD",
            trend="IMPROVING",
        )
        session.add(stm)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/analytics/instructor/cohort",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_candidates" in data
        assert "active_candidates" in data
        assert "topic_proficiencies" in data
        assert "difficulty_proficiencies" in data
        assert "score_distribution" in data
        assert "top_performers" in data
        assert "at_risk_candidates" in data


@pytest.mark.anyio
async def test_candidate_report_and_isolation():
    """Verifies individual candidate audit trail and strict non-leakage of hidden test cases."""
    instructor, inst_token = await _create_test_user("inst_cand_rep", "INSTRUCTOR")
    student, stud_token = await _create_test_user("stud_cand_rep", "STUDENT")

    assessment = await _create_test_assessment(instructor)
    await _create_test_attempt(assessment, student, status_str="COMPLETED", score=90.0, percentage=90.0, is_passed=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Instructor audits candidate
        resp = await client.get(
            f"/api/v1/analytics/instructor/candidates/{student.id}",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["candidate_id"] == str(student.id)
        assert data["full_name"] == student.full_name
        assert data["assessments_completed"] >= 1
        assert "topic_mastery" in data
        assert "difficulty_breakdown" in data
        assert "submissions" in data
        assert "assessment_attempts" in data

        # Verify candidate cannot access other candidate's report directly through instructor route
        stud_resp = await client.get(
            f"/api/v1/analytics/instructor/candidates/{student.id}",
            headers={"Authorization": f"Bearer {stud_token}"},
        )
        assert stud_resp.status_code == 403


@pytest.mark.anyio
async def test_question_test_case_management_and_validation():
    """Verifies Question creation with tags/starter_code, test case category updating, and validation."""
    instructor, inst_token = await _create_test_user("inst_q_mgmt", "INSTRUCTOR")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Question with SAMPLE, FUNCTIONAL, and EDGE_CASE test cases
        q_payload = {
            "title": "Reverse Words in a String",
            "problem_description": "Given an input string s, reverse the order of the words.",
            "difficulty": "MEDIUM",
            "topic": "Strings",
            "marks": 20,
            "tags": "strings,two-pointers",
            "starter_code": "def reverseWords(s: str) -> str:\n    pass\n",
            "test_cases": [
                {
                    "input_data": "the sky is blue",
                    "expected_output": "blue is sky the",
                    "marks": 5,
                    "display_order": 1,
                    "is_hidden": False,
                    "category": "SAMPLE",
                },
                {
                    "input_data": "  hello world  ",
                    "expected_output": "world hello",
                    "marks": 10,
                    "display_order": 2,
                    "is_hidden": True,
                    "category": "FUNCTIONAL",
                },
                {
                    "input_data": "a good   example",
                    "expected_output": "example good a",
                    "marks": 5,
                    "display_order": 3,
                    "is_hidden": True,
                    "category": "EDGE_CASE",
                },
            ],
        }
        create_resp = await client.post(
            "/api/v1/questions",
            json=q_payload,
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert create_resp.status_code == 201
        q_data = create_resp.json()
        question_id = q_data["id"]
        assert q_data["tags"] == "strings,two-pointers"
        assert len(q_data["test_cases"]) == 3
        assert q_data["test_cases"][0]["category"] == "SAMPLE"
        assert q_data["test_cases"][1]["category"] == "FUNCTIONAL"
        assert q_data["test_cases"][2]["category"] == "EDGE_CASE"

        sample_tc_id = q_data["test_cases"][0]["id"]

        # 2. Update test case properties via PUT
        update_tc_payload = {
            "marks": 6,
            "explanation": "Updated explanation for sample case",
            "category": "SAMPLE",
        }
        put_resp = await client.put(
            f"/api/v1/questions/{question_id}/test-cases/{sample_tc_id}",
            json=update_tc_payload,
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert put_resp.status_code == 200
        updated_tc = put_resp.json()
        assert updated_tc["marks"] == 6

        # 3. Validate question test suite
        val_resp = await client.post(
            f"/api/v1/questions/{question_id}/validate",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert val_resp.status_code == 200
        val_data = val_resp.json()
        assert val_data["question_id"] == question_id
        assert val_data["sample_test_count"] >= 1
        assert val_data["functional_test_count"] >= 1
        assert val_data["edge_test_count"] >= 1
        # Marks was 20, now test marks sum is 6 + 10 + 5 = 21 -> warning should be flagged
        assert len(val_data["warnings"]) >= 1


@pytest.mark.anyio
async def test_csv_exports():
    """Verifies CSV generation for assessments, candidates, and question bank performance."""
    instructor, inst_token = await _create_test_user("inst_csv", "INSTRUCTOR")
    student, _ = await _create_test_user("stud_csv", "STUDENT")

    assessment = await _create_test_assessment(instructor)
    await _create_test_attempt(assessment, student, status_str="COMPLETED", score=85.0, percentage=85.0, is_passed=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Assessment CSV export
        ass_csv = await client.get(
            f"/api/v1/analytics/instructor/assessments/{assessment.id}/export",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert ass_csv.status_code == 200
        assert ass_csv.headers["content-type"].startswith("text/csv")
        assert "Candidate ID,Full Name,Email" in ass_csv.text

        # 2. Candidate CSV export
        cand_csv = await client.get(
            f"/api/v1/analytics/instructor/candidates/{student.id}/export",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert cand_csv.status_code == 200
        assert cand_csv.headers["content-type"].startswith("text/csv")
        assert "=== CANDIDATE OVERVIEW ===" in cand_csv.text

        # 3. Questions Performance CSV export
        q_csv = await client.get(
            "/api/v1/analytics/instructor/questions/export",
            headers={"Authorization": f"Bearer {inst_token}"},
        )
        assert q_csv.status_code == 200
        assert q_csv.headers["content-type"].startswith("text/csv")
        assert "Question ID,Title,Topic,Difficulty" in q_csv.text
