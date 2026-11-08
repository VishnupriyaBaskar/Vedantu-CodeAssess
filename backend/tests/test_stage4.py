r"""
Comprehensive Test Suite for Stage 4: Question Bank, Assessment Orchestration & Code Evaluation
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New

Verifies:
1. Question Bank CRUD, topic/difficulty filtering, sample vs hidden test case isolation.
2. Assessment creation, question association, publishing validations, candidate enrollment.
3. Student Assessment lifecycle: starting attempt, server timer, draft autosaving.
4. Judge0 evaluation: ACCEPTED, WRONG_ANSWER, TIME_LIMIT_EXCEEDED, COMPILATION_ERROR, RUNTIME_ERROR.
5. Deterministic scoring engine: partial marks, percentage, pass/fail threshold calculation.
"""

from datetime import datetime, timedelta, timezone
import sys
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_candidate import AssessmentCandidate
from app.models.code_draft import CodeDraft
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.role import Role, UserRole
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User


# ------------------------------------------------------------------------------
# Test Fixtures & Helpers
# ------------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_user_with_role(role_name: str) -> tuple[User, str]:
    """Helper to provision a user with a specific role and return user and auth token."""
    suffix = uuid.uuid4().hex[:8]
    email = f"{role_name.lower()}_{suffix}@vedantu-test.com"

    async with async_session_factory() as session:
        async with session.begin():
            # Check or create role
            stmt_role = select(Role).where(Role.name == role_name)
            role = (await session.execute(stmt_role)).scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=f"Role {role_name}")
                session.add(role)
                await session.flush()

            # Create user
            user = User(
                full_name=f"Stage4 {role_name} User",
                email=email,
                password_hash=hash_password("SecurePassword123!"),
                status="ACTIVE",
            )
            session.add(user)
            await session.flush()

            # Assign role
            user_role = UserRole(user_id=user.id, role_id=role.id)
            session.add(user_role)

        stmt_load = select(User).options(selectinload(User.roles)).where(User.id == user.id)
        loaded_user = (await session.execute(stmt_load)).scalar_one()

    token, _, _ = create_access_token(
        subject=str(loaded_user.id),
        roles=[role_name],
        extra_claims={"email": loaded_user.email},
    )
    return loaded_user, token


async def get_test_programming_languages():
    """Retrieve Python 3 and Java language models from database."""
    async with async_session_factory() as session:
        stmt = select(ProgrammingLanguage).where(ProgrammingLanguage.is_active == True)
        result = await session.execute(stmt)
        langs = result.scalars().all()
        py_lang = next((l for l in langs if "python" in l.name.lower()), None)
        java_lang = next((l for l in langs if "java" in l.name.lower()), None)
        return py_lang, java_lang


# ------------------------------------------------------------------------------
# 1. Question Bank & Test Case Isolation Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_question_with_sample_and_hidden_test_cases():
    """Verify instructors can author questions with both public sample and confidential hidden test cases."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    headers = {"Authorization": f"Bearer {instructor_token}"}
    transport = ASGITransport(app=app)

    payload = {
        "title": "Sum of Two Numbers",
        "problem_description": "Given two integers a and b, output their sum.",
        "input_format": "Two space-separated integers",
        "output_format": "Single integer representing sum",
        "constraints": "-10^9 <= a, b <= 10^9",
        "difficulty": "EASY",
        "topic": "Basic Math",
        "marks": 10,
        "time_limit_seconds": 2.0,
        "memory_limit_mb": 256,
        "display_order": 1,
        "test_cases": [
            {
                "input_data": "3 5",
                "expected_output": "8",
                "explanation": "3 + 5 = 8",
                "marks": 4,
                "display_order": 1,
                "is_hidden": False,  # Public sample
            },
            {
                "input_data": "100 200",
                "expected_output": "300",
                "explanation": None,
                "marks": 6,
                "display_order": 2,
                "is_hidden": True,  # Confidential hidden
            },
        ],
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"{settings.API_V1_STR}/questions", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Sum of Two Numbers"
        assert len(data["test_cases"]) == 2
        assert data["test_cases"][0]["is_hidden"] is False
        assert data["test_cases"][1]["is_hidden"] is True


@pytest.mark.anyio
async def test_question_test_case_confidentiality_isolation():
    """Verify that student users CANNOT receive hidden test case inputs or expected outputs."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    _, student_token = await create_user_with_role("STUDENT")
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}
    stud_headers = {"Authorization": f"Bearer {student_token}"}
    transport = ASGITransport(app=app)

    # 1. Instructor creates question with hidden test case
    payload = {
        "title": "Secret Encryption Key",
        "problem_description": "Validate the confidential secret key.",
        "difficulty": "MEDIUM",
        "topic": "Security",
        "marks": 20,
        "time_limit_seconds": 2.0,
        "memory_limit_mb": 256,
        "display_order": 1,
        "test_cases": [
            {
                "input_data": "public_sample_input",
                "expected_output": "public_sample_output",
                "marks": 5,
                "display_order": 1,
                "is_hidden": False,
            },
            {
                "input_data": "CONFIDENTIAL_HIDDEN_SECRET_INPUT_999",
                "expected_output": "CONFIDENTIAL_HIDDEN_OUTPUT_999",
                "marks": 15,
                "display_order": 2,
                "is_hidden": True,
            },
        ],
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(f"{settings.API_V1_STR}/questions", json=payload, headers=inst_headers)
        assert create_res.status_code == 201
        q_id = create_res.json()["id"]

        # 2. Student fetches question by ID
        student_get_res = await ac.get(f"{settings.API_V1_STR}/questions/{q_id}", headers=stud_headers)
        assert student_get_res.status_code == 200
        student_data = student_get_res.json()

        # Check that hidden test case is NOT present anywhere in student payload
        raw_text = student_get_res.text
        assert "CONFIDENTIAL_HIDDEN_SECRET_INPUT_999" not in raw_text
        assert "CONFIDENTIAL_HIDDEN_OUTPUT_999" not in raw_text

        # Student response only contains sample_test_cases
        assert "sample_test_cases" in student_data
        assert "test_cases" not in student_data
        assert len(student_data["sample_test_cases"]) == 1
        assert student_data["sample_test_cases"][0]["input_data"] == "public_sample_input"


@pytest.mark.anyio
async def test_question_archive_soft_delete():
    """Verify question archiving hides question from active bank without breaking DB integrity."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    headers = {"Authorization": f"Bearer {instructor_token}"}
    transport = ASGITransport(app=app)

    payload = {
        "title": "Temporary Question To Archive",
        "problem_description": "To be archived.",
        "difficulty": "EASY",
        "topic": "Temp",
        "marks": 10,
        "test_cases": [],
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(f"{settings.API_V1_STR}/questions", json=payload, headers=headers)
        q_id = create_res.json()["id"]

        # Archive
        del_res = await ac.delete(f"{settings.API_V1_STR}/questions/{q_id}", headers=headers)
        assert del_res.status_code == 200
        assert "archived successfully" in del_res.json()["detail"].lower()

        # Verify list default excludes archived
        list_res = await ac.get(f"{settings.API_V1_STR}/questions?is_archived=false", headers=headers)
        active_ids = [q["id"] for q in list_res.json()]
        assert q_id not in active_ids


# ------------------------------------------------------------------------------
# 2. Assessment Management & Publishing Lifecycle Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_assessment_create_and_publish_validation():
    """Verify assessment creation and that publishing without questions is blocked."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    headers = {"Authorization": f"Bearer {instructor_token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create empty assessment (no questions)
        ass_payload = {
            "title": "Sprint 4 Assessment - Python & Java",
            "description": "Evaluation for Stage 4",
            "duration_minutes": 90,
            "total_marks": 100,
            "passing_marks": 40,
            "difficulty": "MEDIUM",
            "allowed_languages": "Python 3,Java",
        }
        res = await ac.post(f"{settings.API_V1_STR}/assessments", json=ass_payload, headers=headers)
        assert res.status_code == 201
        ass_id = res.json()["id"]
        assert res.json()["status"] == "DRAFT"

        # 2. Attempt to publish empty assessment -> should fail with 400
        pub_fail = await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=headers)
        assert pub_fail.status_code == 400
        assert "at least one question must be attached" in pub_fail.json()["detail"].lower()

        # 3. Create a question and attach it
        q_payload = {
            "title": "Attached Exam Question",
            "problem_description": "Valid attached question.",
            "difficulty": "MEDIUM",
            "topic": "Algorithms",
            "marks": 50,
            "assessment_id": ass_id,
            "test_cases": [
                {
                    "input_data": "10",
                    "expected_output": "20",
                    "marks": 50,
                    "display_order": 1,
                    "is_hidden": False,
                }
            ],
        }
        q_res = await ac.post(f"{settings.API_V1_STR}/questions", json=q_payload, headers=headers)
        assert q_res.status_code == 201

        # 4. Now publishing should succeed
        pub_success = await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=headers)
        assert pub_success.status_code == 200
        assert pub_success.json()["status"] == "PUBLISHED"


@pytest.mark.anyio
async def test_assessment_candidate_assignment():
    """Verify instructors can enroll student candidates into assessments."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    student1, _ = await create_user_with_role("STUDENT")
    student2, _ = await create_user_with_role("STUDENT")
    headers = {"Authorization": f"Bearer {instructor_token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ass_payload = {
            "title": "Candidate Enrollment Exam",
            "duration_minutes": 60,
            "total_marks": 50,
            "passing_marks": 25,
        }
        res = await ac.post(f"{settings.API_V1_STR}/assessments", json=ass_payload, headers=headers)
        ass_id = res.json()["id"]

        # Assign candidates
        assign_res = await ac.post(
            f"{settings.API_V1_STR}/assessments/{ass_id}/candidates",
            json={"user_ids": [str(student1.id), str(student2.id)]},
            headers=headers,
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["enrolled_count"] == 2


# ------------------------------------------------------------------------------
# 3. Student Assessment Workflow & Timer Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_student_start_assessment_and_draft_autosave():
    """Verify student starts exam, receives server-calculated timer, and autosaves code drafts."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    student, student_token = await create_user_with_role("STUDENT")
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}
    stud_headers = {"Authorization": f"Bearer {student_token}"}
    transport = ASGITransport(app=app)
    py_lang, _ = await get_test_programming_languages()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Setup published assessment with a question
        ass_res = await ac.post(
            f"{settings.API_V1_STR}/assessments",
            json={"title": "Draft Autosave Exam", "duration_minutes": 60, "total_marks": 50, "passing_marks": 20},
            headers=inst_headers,
        )
        ass_id = ass_res.json()["id"]

        q_res = await ac.post(
            f"{settings.API_V1_STR}/questions",
            json={
                "title": "Solve Factorial",
                "problem_description": "Compute N factorial.",
                "difficulty": "EASY",
                "topic": "Math",
                "marks": 50,
                "assessment_id": ass_id,
                "test_cases": [
                    {"input_data": "5", "expected_output": "120", "marks": 50, "display_order": 1, "is_hidden": False}
                ],
            },
            headers=inst_headers,
        )
        q_id = q_res.json()["id"]

        # Publish assessment
        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=inst_headers)

        # Enroll candidate
        await ac.post(
            f"{settings.API_V1_STR}/assessments/{ass_id}/candidates",
            json={"user_ids": [str(student.id)]},
            headers=inst_headers,
        )

        # 2. Student starts assessment
        start_res = await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/start", headers=stud_headers)
        assert start_res.status_code == 200
        start_data = start_res.json()
        assert start_data["status"] == "IN_PROGRESS"
        assert start_data["duration_minutes"] == 60
        assert 3500 <= start_data["remaining_seconds"] <= 3600
        assert len(start_data["questions"]) == 1

        # 3. Student autosaves code draft
        draft_code = "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n"
        draft_res = await ac.post(
            f"{settings.API_V1_STR}/student/assessments/{ass_id}/drafts",
            json={
                "question_id": q_id,
                "programming_language_id": str(py_lang.id),
                "source_code": draft_code,
            },
            headers=stud_headers,
        )
        assert draft_res.status_code == 200
        assert draft_res.json()["source_code"] == draft_code

        # 4. Student resumes assessment and verifies draft is restored
        resume_res = await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/start", headers=stud_headers)
        assert resume_res.status_code == 200
        assert resume_res.json()["drafts"][str(q_id)] == draft_code


# ------------------------------------------------------------------------------
# 4. Code Evaluation & Judge0 Live Sandbox Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_judge0_python_evaluation_accepted_and_scoring():
    """Verify live Python evaluation passes sample and hidden test cases, awarding 100% marks."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    student, student_token = await create_user_with_role("STUDENT")
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}
    stud_headers = {"Authorization": f"Bearer {student_token}"}
    transport = ASGITransport(app=app)
    py_lang, _ = await get_test_programming_languages()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create assessment and question
        ass_res = await ac.post(
            f"{settings.API_V1_STR}/assessments",
            json={"title": "Python Evaluation Exam", "duration_minutes": 60, "total_marks": 30, "passing_marks": 15},
            headers=inst_headers,
        )
        ass_id = ass_res.json()["id"]

        q_res = await ac.post(
            f"{settings.API_V1_STR}/questions",
            json={
                "title": "Reverse Words in String",
                "problem_description": "Print reversed line.",
                "difficulty": "EASY",
                "topic": "Strings",
                "marks": 30,
                "assessment_id": ass_id,
                "test_cases": [
                    {"input_data": "hello world\n", "expected_output": "world hello\n", "marks": 10, "display_order": 1, "is_hidden": False},
                    {"input_data": "vedantu platform\n", "expected_output": "platform vedantu\n", "marks": 20, "display_order": 2, "is_hidden": True},
                ],
            },
            headers=inst_headers,
        )
        q_id = q_res.json()["id"]

        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/candidates", json={"user_ids": [str(student.id)]}, headers=inst_headers)

        # Start exam
        await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/start", headers=stud_headers)

        # Correct solution in Python
        valid_python_code = """import sys
lines = sys.stdin.read().split()
if lines:
    print(' '.join(reversed(lines)))
"""
        eval_res = await ac.post(
            f"{settings.API_V1_STR}/student/assessments/{ass_id}/submit-code",
            json={
                "question_id": q_id,
                "programming_language_id": str(py_lang.id),
                "source_code": valid_python_code,
            },
            headers=stud_headers,
        )
        assert eval_res.status_code == 200
        data = eval_res.json()
        assert data["status"] == "ACCEPTED"
        assert data["score"] == 30.0
        assert data["passed_test_cases"] == 2
        assert data["total_test_cases"] == 2


@pytest.mark.anyio
async def test_judge0_compilation_error_short_circuits():
    """Verify syntax/compilation error stops evaluation and awards 0 marks without crashing."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    student, student_token = await create_user_with_role("STUDENT")
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}
    stud_headers = {"Authorization": f"Bearer {student_token}"}
    transport = ASGITransport(app=app)
    _, java_lang = await get_test_programming_languages()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ass_res = await ac.post(
            f"{settings.API_V1_STR}/assessments",
            json={"title": "Compilation Error Exam", "duration_minutes": 60, "total_marks": 20, "passing_marks": 10},
            headers=inst_headers,
        )
        ass_id = ass_res.json()["id"]

        q_res = await ac.post(
            f"{settings.API_V1_STR}/questions",
            json={
                "title": "Java Syntax Test",
                "problem_description": "Test compilation error behavior.",
                "difficulty": "EASY",
                "topic": "Java",
                "marks": 20,
                "assessment_id": ass_id,
                "test_cases": [
                    {"input_data": "1", "expected_output": "1", "marks": 10, "display_order": 1, "is_hidden": False},
                    {"input_data": "2", "expected_output": "2", "marks": 10, "display_order": 2, "is_hidden": True},
                ],
            },
            headers=inst_headers,
        )
        q_id = q_res.json()["id"]

        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/candidates", json={"user_ids": [str(student.id)]}, headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/start", headers=stud_headers)

        # Invalid Java code that won't compile
        broken_java_code = "public class Main { this is completely invalid syntax }"

        eval_res = await ac.post(
            f"{settings.API_V1_STR}/student/assessments/{ass_id}/submit-code",
            json={
                "question_id": q_id,
                "programming_language_id": str(java_lang.id),
                "source_code": broken_java_code,
            },
            headers=stud_headers,
        )
        assert eval_res.status_code == 200
        data = eval_res.json()
        assert data["status"] == "COMPILATION_ERROR"
        assert data["score"] == 0.0
        assert data["passed_test_cases"] == 0


@pytest.mark.anyio
async def test_judge0_runtime_error_handled_gracefully():
    """Verify runtime exception (ZeroDivisionError) is handled and recorded without crashing."""
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    student, student_token = await create_user_with_role("STUDENT")
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}
    stud_headers = {"Authorization": f"Bearer {student_token}"}
    transport = ASGITransport(app=app)
    py_lang, _ = await get_test_programming_languages()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ass_res = await ac.post(
            f"{settings.API_V1_STR}/assessments",
            json={"title": "Runtime Error Exam", "duration_minutes": 60, "total_marks": 20, "passing_marks": 10},
            headers=inst_headers,
        )
        ass_id = ass_res.json()["id"]

        q_res = await ac.post(
            f"{settings.API_V1_STR}/questions",
            json={
                "title": "Exception Test",
                "problem_description": "Code causes ZeroDivisionError.",
                "difficulty": "EASY",
                "topic": "Python",
                "marks": 20,
                "assessment_id": ass_id,
                "test_cases": [
                    {"input_data": "10", "expected_output": "10", "marks": 20, "display_order": 1, "is_hidden": False}
                ],
            },
            headers=inst_headers,
        )
        q_id = q_res.json()["id"]

        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/candidates", json={"user_ids": [str(student.id)]}, headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/start", headers=stud_headers)

        # Code that raises ZeroDivisionError
        crash_code = "print(10 / 0)\n"

        eval_res = await ac.post(
            f"{settings.API_V1_STR}/student/assessments/{ass_id}/submit-code",
            json={
                "question_id": q_id,
                "programming_language_id": str(py_lang.id),
                "source_code": crash_code,
            },
            headers=stud_headers,
        )
        assert eval_res.status_code == 200
        data = eval_res.json()
        assert data["status"] == "RUNTIME_ERROR"
        assert data["score"] == 0.0


# ------------------------------------------------------------------------------
# 5. Deterministic Scoring Engine & Assessment Finalization Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_deterministic_partial_marks_and_pass_fail_scoring():
    """
    Verify:
    1. Partial scoring formula: passed_tc_marks / total_tc_marks * question.marks.
    2. Final assessment grading aggregates best submission per question.
    3. Pass/Fail threshold correctly evaluated against passing_marks.
    """
    _, instructor_token = await create_user_with_role("INSTRUCTOR")
    student, student_token = await create_user_with_role("STUDENT")
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}
    stud_headers = {"Authorization": f"Bearer {student_token}"}
    transport = ASGITransport(app=app)
    py_lang, _ = await get_test_programming_languages()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create Assessment with total_marks=100, passing_marks=50
        ass_res = await ac.post(
            f"{settings.API_V1_STR}/assessments",
            json={
                "title": "Deterministic Scoring Final Exam",
                "duration_minutes": 60,
                "total_marks": 100,
                "passing_marks": 50,
            },
            headers=inst_headers,
        )
        ass_id = ass_res.json()["id"]

        # Question 1 (50 marks): Two test cases (10 marks, 10 marks)
        # Total TC marks = 20. If pass 1 TC, awarded (10/20)*50 = 25 marks.
        q1_res = await ac.post(
            f"{settings.API_V1_STR}/questions",
            json={
                "title": "Q1 - Conditional Filter",
                "problem_description": "Print positive numbers only.",
                "difficulty": "MEDIUM",
                "topic": "Logic",
                "marks": 50,
                "assessment_id": ass_id,
                "test_cases": [
                    {"input_data": "5", "expected_output": "5", "marks": 10, "display_order": 1, "is_hidden": False},
                    {"input_data": "-3", "expected_output": "NEGATIVE", "marks": 10, "display_order": 2, "is_hidden": True},
                ],
            },
            headers=inst_headers,
        )
        q1_id = q1_res.json()["id"]

        # Question 2 (50 marks): One test case (10 marks)
        q2_res = await ac.post(
            f"{settings.API_V1_STR}/questions",
            json={
                "title": "Q2 - Square Number",
                "problem_description": "Output square of integer.",
                "difficulty": "EASY",
                "topic": "Math",
                "marks": 50,
                "assessment_id": ass_id,
                "test_cases": [
                    {"input_data": "7", "expected_output": "49", "marks": 10, "display_order": 1, "is_hidden": False}
                ],
            },
            headers=inst_headers,
        )
        q2_id = q2_res.json()["id"]

        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/publish", headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/assessments/{ass_id}/candidates", json={"user_ids": [str(student.id)]}, headers=inst_headers)
        await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/start", headers=stud_headers)

        # Student submits Q1 code that passes ONLY test case 1 (prints "5" for everything)
        # Should award partial score: 25.0 out of 50.0 marks
        code_q1_partial = "import sys\nprint('5')\n"
        sub1_res = await ac.post(
            f"{settings.API_V1_STR}/student/assessments/{ass_id}/submit-code",
            json={
                "question_id": q1_id,
                "programming_language_id": str(py_lang.id),
                "source_code": code_q1_partial,
            },
            headers=stud_headers,
        )
        assert sub1_res.status_code == 200
        assert sub1_res.json()["score"] == 25.0
        assert sub1_res.json()["passed_test_cases"] == 1
        assert sub1_res.json()["status"] == "WRONG_ANSWER"

        # Student submits Q2 code that passes completely -> awards 50.0 out of 50.0 marks
        code_q2_full = "import sys\nn = int(sys.stdin.read().strip())\nprint(n * n)\n"
        sub2_res = await ac.post(
            f"{settings.API_V1_STR}/student/assessments/{ass_id}/submit-code",
            json={
                "question_id": q2_id,
                "programming_language_id": str(py_lang.id),
                "source_code": code_q2_full,
            },
            headers=stud_headers,
        )
        assert sub2_res.status_code == 200
        assert sub2_res.json()["score"] == 50.0
        assert sub2_res.json()["status"] == "ACCEPTED"

        # Student finishes examination
        finish_res = await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/finish", headers=stud_headers)
        assert finish_res.status_code == 200
        data = finish_res.json()

        # Total expected: 25.0 (Q1) + 50.0 (Q2) = 75.0 marks out of 100.0 (75.0%)
        # Passing marks = 50.0 -> is_passed must be True!
        assert data["total_score"] == 75.0
        assert data["percentage"] == 75.0
        assert data["is_passed"] is True
        assert data["status"] == "COMPLETED"

        # Idempotent re-submission check: calling finish again returns identical completed result
        finish_res_2 = await ac.post(f"{settings.API_V1_STR}/student/assessments/{ass_id}/finish", headers=stud_headers)
        assert finish_res_2.status_code == 200
        assert finish_res_2.json()["total_score"] == 75.0
