r"""
Test Suite for Stage 5: AI-Powered Code Evaluation & Static Code Analysis
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New

Verifies:
1. Python AST static analysis (complexity, naming, bare except, deep nesting, syntax errors).
2. Java lexical/structural static analysis (complexity, naming, empty catch, redundant booleans, System.gc).
3. Mock AI provider deterministic evaluation.
4. Gemini/External AI provider missing key handling & failure resilience.
5. Evaluation storage and scoring isolation (authoritative Judge0 score remains unaltered).
6. Submission ownership enforcement and RBAC on evaluation retrieval endpoint.
7. Confidentiality contract: hidden test case data is never leaked or transmitted to AI evaluator.
"""

from datetime import datetime, timezone
import sys
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
from app.models.assessment_candidate import AssessmentCandidate
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.role import Role, UserRole
from app.models.submission import Submission
from app.models.submission_evaluation import SubmissionEvaluation
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.submission import SubmissionCreate
from app.services.ai_evaluation import (
    AIEvaluationRequest,
    GeminiAIProvider,
    MockAIProvider,
    ai_evaluation_service,
)
from app.services.evaluation_service import evaluation_service
from app.services.static_analysis import (
    analyze_code,
    analyze_java_code,
    analyze_python_code,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_user_with_role(role_name: str) -> tuple[User, str]:
    """Helper to provision a user with a specific role and return user and auth token."""
    suffix = uuid.uuid4().hex[:8]
    email = f"stage5_{role_name.lower()}_{suffix}@vedantu-test.com"

    async with async_session_factory() as session:
        async with session.begin():
            stmt_role = select(Role).where(Role.name == role_name)
            role = (await session.execute(stmt_role)).scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=f"Role {role_name}")
                session.add(role)
                await session.flush()

            user = User(
                full_name=f"Stage5 {role_name} User",
                email=email,
                password_hash=hash_password("SecurePassword123!"),
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
        roles=[role_name],
        extra_claims={"email": loaded_user.email},
    )
    return loaded_user, token


# ------------------------------------------------------------------------------
# 1. Static Code Analysis Tests (Python 3 & Java)
# ------------------------------------------------------------------------------

def test_python_static_analysis_clean_code():
    """Verify clean Python code yields high maintainability score and no smell warnings."""
    clean_code = """
def calculate_sum(a: int, b: int) -> int:
    # Compute sum of two integers
    return a + b
"""
    result = analyze_python_code(clean_code)
    assert result.language == "Python 3"
    assert result.cyclomatic_complexity >= 1
    assert result.max_nesting_depth >= 1
    assert result.maintainability_score >= 90.0
    # No error or warning findings
    warnings = [f for f in result.findings if f.severity in ("WARNING", "ERROR")]
    assert len(warnings) == 0


def test_python_static_analysis_detects_smells():
    """Verify Python analyzer flags bare except, wildcard import, naming issues, and deep nesting."""
    smelly_code = """
from math import *

def SolveProblem(val):
    try:
        if val > 0:
            while val > 10:
                for i in range(val):
                    if i % 2 == 0:
                        pass
    except:
        return 0
"""
    result = analyze_python_code(smelly_code)
    finding_codes = {f.code for f in result.findings}
    assert "PY_WILDCARD_IMPORT" in finding_codes
    assert "PY_BARE_EXCEPT" in finding_codes
    assert "PY_NAMING_FUNCTION" in finding_codes
    assert "PY_DEEP_NESTING" in finding_codes
    assert result.maintainability_score < 90.0


def test_python_static_analysis_syntax_error_resilience():
    """Verify syntax error is reported cleanly without throwing unhandled exceptions."""
    broken_code = "def broken_func(a, b\n    return a +"
    result = analyze_python_code(broken_code)
    assert result.language == "Python 3"
    assert any(f.code == "PY_SYNTAX_ERROR" for f in result.findings)
    assert result.maintainability_score <= 30.0


def test_java_static_analysis_clean_code():
    """Verify standard Java class passes analysis with high score."""
    clean_code = """
public class Solution {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
    result = analyze_java_code(clean_code)
    assert result.language == "Java"
    assert result.cyclomatic_complexity >= 1
    assert result.maintainability_score >= 90.0
    assert len([f for f in result.findings if f.severity in ("WARNING", "ERROR")]) == 0


def test_java_static_analysis_detects_smells():
    """Verify Java analyzer flags empty catch, redundant boolean, System.gc, and PascalCase violation."""
    smelly_code = """
public class badClassName {
    public void executeLogic(boolean isValid) {
        if (isValid == true) {
            System.gc();
        }
        try {
            int x = 10 / 0;
        } catch (Exception e) {
        }
    }
}
"""
    result = analyze_java_code(smelly_code)
    finding_codes = {f.code for f in result.findings}
    assert "JAVA_NAMING_CLASS" in finding_codes
    assert "JAVA_REDUNDANT_BOOLEAN" in finding_codes
    assert "JAVA_SYSTEM_GC" in finding_codes
    assert "JAVA_EMPTY_CATCH" in finding_codes
    assert result.maintainability_score < 90.0


def test_static_analysis_dispatcher():
    """Verify dispatcher routes correctly by language name."""
    res_py = analyze_code("Python 3", "def add(a, b): return a + b")
    assert res_py.language == "Python 3"

    res_java = analyze_code("Java (OpenJDK 17)", "public class Main {}")
    assert res_java.language == "Java"


# ------------------------------------------------------------------------------
# 2. AI Code Evaluation Providers Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_mock_ai_provider_deterministic_evaluation():
    """Verify MockAIProvider returns high-quality structured feedback offline without cost."""
    provider = MockAIProvider()
    request = AIEvaluationRequest(
        problem_title="Two Sum",
        problem_description="Find two elements that sum to target.",
        constraints="2 <= N <= 10^5",
        language_name="Python 3",
        source_code="""
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
""",
        execution_status="ACCEPTED",
        score=20.0,
        total_test_cases=5,
        passed_test_cases=5,
    )

    result = await provider.evaluate_code(request)
    assert result.provider_name == "mock"
    assert result.status == "COMPLETED"
    assert result.feedback is not None
    assert "Hash" in result.feedback.logical_approach or "hash" in result.feedback.logical_approach
    assert result.feedback.estimated_time_complexity == "O(N)"
    assert result.feedback.estimated_space_complexity == "O(N)"
    assert len(result.feedback.improvement_suggestions) > 0


@pytest.mark.anyio
async def test_gemini_provider_missing_api_key():
    """Verify Gemini provider reports UNAVAILABLE when API key is empty."""
    provider = GeminiAIProvider(api_key="")
    request = AIEvaluationRequest(
        problem_title="Sample Problem",
        problem_description="Sample Description",
        language_name="Python 3",
        source_code="print('hello')",
        execution_status="ACCEPTED",
        score=10.0,
        total_test_cases=1,
        passed_test_cases=1,
    )

    result = await provider.evaluate_code(request)
    assert result.status == "UNAVAILABLE"
    assert "not configured" in (result.error_message or "").lower()
    assert result.feedback is None


@pytest.mark.anyio
async def test_gemini_provider_network_failure_resilience():
    """Verify Gemini provider gracefully handles network failure without raising an unhandled exception."""
    # Invalid endpoint / timeout simulated with tiny timeout
    provider = GeminiAIProvider(api_key="fake_key_for_testing", timeout_seconds=0.001)
    request = AIEvaluationRequest(
        problem_title="Sample Problem",
        problem_description="Sample Description",
        language_name="Python 3",
        source_code="print('hello')",
        execution_status="ACCEPTED",
        score=10.0,
        total_test_cases=1,
        passed_test_cases=1,
    )

    result = await provider.evaluate_code(request)
    assert result.status == "FAILED"
    assert result.error_message is not None


# ------------------------------------------------------------------------------
# 3. Confidentiality Contract & Scoring Isolation Tests
# ------------------------------------------------------------------------------

def test_confidentiality_contract_excludes_hidden_test_cases():
    """Ensure confidential hidden testcase data is structurally excluded from AI requests."""
    fields = AIEvaluationRequest.model_fields.keys()
    assert "hidden_test_cases" not in fields
    assert "test_case_inputs" not in fields
    assert "test_case_expected_outputs" not in fields


@pytest.mark.anyio
async def test_submission_evaluation_persistence_and_scoring_isolation():
    """
    Verify full submission creates Submission and SubmissionEvaluation records in DB,
    and qualitative evaluation does NOT alter deterministic test-case score.
    """
    student, student_token = await create_user_with_role("STUDENT")
    instructor, _ = await create_user_with_role("INSTRUCTOR")

    async with async_session_factory() as session:
        async with session.begin():
            # Resolve Python language
            stmt_lang = select(ProgrammingLanguage).where(ProgrammingLanguage.name.ilike("%python%"))
            py_lang = (await session.execute(stmt_lang)).scalars().first()

            # Create assessment
            assessment = Assessment(
                title=f"Stage 5 Eval Assessment {uuid.uuid4().hex[:6]}",
                duration_minutes=30,
                total_marks=20,
                passing_marks=10,
                difficulty="MEDIUM",
                allowed_languages="ALL_ACTIVE",
                status="PUBLISHED",
                created_by=instructor.id,
            )
            session.add(assessment)
            await session.flush()

            # Create question with 1 sample and 1 hidden test case
            question = Question(
                assessment_id=assessment.id,
                title="Stage 5 Reversal Challenge",
                problem_description="Reverse the input string.",
                difficulty="MEDIUM",
                topic="Strings",
                marks=20,
                display_order=1,
            )
            session.add(question)
            await session.flush()

            tc_sample = TestCase(
                question_id=question.id,
                input_data="abc\n",
                expected_output="cba",
                marks=10,
                is_hidden=False,
                display_order=1,
            )
            tc_hidden = TestCase(
                question_id=question.id,
                input_data="secret_hidden_input\n",
                expected_output="tupni_neddih_terces",
                marks=10,
                is_hidden=True,
                display_order=2,
            )
            session.add_all([tc_sample, tc_hidden])

            # Assign student and start attempt
            cand = AssessmentCandidate(assessment_id=assessment.id, user_id=student.id)
            attempt = AssessmentAttempt(
                assessment_id=assessment.id,
                user_id=student.id,
                status="IN_PROGRESS",
                started_at=datetime.now(timezone.utc),
            )
            session.add_all([cand, attempt])

    # Student submits solution
    solution_code = """
import sys

def reverse_string():
    raw = sys.stdin.read().strip()
    print(raw[::-1])

if __name__ == '__main__':
    reverse_string()
"""
    create_payload = SubmissionCreate(
        assessment_id=assessment.id,
        question_id=question.id,
        programming_language_id=py_lang.id,
        source_code=solution_code,
    )

    async with async_session_factory() as db:
        sub_resp = await evaluation_service.evaluate_submission(
            db=db,
            user=student,
            data=create_payload,
            run_mode="FULL",
        )

    # 1. Authoritative functional scoring verification
    assert sub_resp.status == "ACCEPTED"
    assert sub_resp.score == 20.0
    assert sub_resp.passed_test_cases == 2
    assert sub_resp.total_test_cases == 2

    # 2. Qualitative review verification
    assert sub_resp.evaluation is not None
    assert sub_resp.evaluation.static_analysis is not None
    assert sub_resp.evaluation.static_analysis.maintainability_score >= 80.0
    assert sub_resp.evaluation.ai_feedback is not None
    assert sub_resp.evaluation.ai_provider == "mock"
    assert sub_resp.evaluation.ai_status == "COMPLETED"

    # 3. Database persistence verification
    async with async_session_factory() as verify_session:
        stmt_eval = (
            select(SubmissionEvaluation)
            .where(SubmissionEvaluation.submission_id == sub_resp.id)
        )
        saved_eval = (await verify_session.execute(stmt_eval)).scalar_one_or_none()
        assert saved_eval is not None
        assert saved_eval.ai_provider == "mock"
        assert saved_eval.static_analysis["language"] == "Python 3"


# ------------------------------------------------------------------------------
# 4. Submission Evaluation Endpoint & Ownership RBAC Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_evaluation_endpoint_ownership_and_rbac():
    """
    Verify:
    1. Student owner can retrieve evaluation.
    2. Other students receive 403 Forbidden.
    3. Instructor can retrieve student evaluation.
    """
    student_a, token_a = await create_user_with_role("STUDENT")
    student_b, token_b = await create_user_with_role("STUDENT")
    instructor, token_inst = await create_user_with_role("INSTRUCTOR")

    # Seed submission and evaluation for student_a
    async with async_session_factory() as session:
        async with session.begin():
            stmt_lang = select(ProgrammingLanguage).where(ProgrammingLanguage.is_active == True)
            lang = (await session.execute(stmt_lang)).scalars().first()

            question = Question(
                title=f"Test Question {uuid.uuid4().hex[:6]}",
                problem_description="Test problem description",
                difficulty="EASY",
                topic="Logic",
                marks=10,
                display_order=1,
            )
            session.add(question)
            await session.flush()

            submission = Submission(
                id=uuid.uuid4(),
                user_id=student_a.id,
                question_id=question.id,
                programming_language_id=lang.id,
                source_code="print('student A code')",
                status="ACCEPTED",
                score=10.0,
                created_at=datetime.now(timezone.utc),
            )
            session.add(submission)
            await session.flush()

            eval_record = SubmissionEvaluation(
                id=uuid.uuid4(),
                submission_id=submission.id,
                static_analysis={
                    "language": "Python 3",
                    "lines_of_code": 1,
                    "cyclomatic_complexity": 1,
                    "max_nesting_depth": 1,
                    "maintainability_score": 95.0,
                    "findings": [],
                },
                ai_feedback={
                    "logical_approach": "Clean linear logic",
                    "readability": "Excellent",
                    "maintainability": "High",
                    "algorithmic_efficiency": "O(1) time and space",
                    "improvement_suggestions": ["Keep code concise"],
                },
                ai_provider="mock",
                ai_status="COMPLETED",
                created_at=datetime.now(timezone.utc),
            )
            session.add(eval_record)

    transport = ASGITransport(app=app)
    endpoint = f"/api/v1/student/submissions/{submission.id}/evaluation"

    # 1. Student A (owner) -> 200 OK
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_a = await client.get(endpoint, headers={"Authorization": f"Bearer {token_a}"})
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["submission_id"] == str(submission.id)
        assert data_a["ai_status"] == "COMPLETED"
        assert data_a["static_analysis"]["maintainability_score"] == 95.0

    # 2. Student B (unauthorized third-party) -> 403 Forbidden
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_b = await client.get(endpoint, headers={"Authorization": f"Bearer {token_b}"})
        assert res_b.status_code == 403
        assert "not authorized" in res_b.json()["detail"].lower()

    # 3. Instructor (privileged) -> 200 OK
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_inst = await client.get(endpoint, headers={"Authorization": f"Bearer {token_inst}"})
        assert res_inst.status_code == 200
        data_inst = res_inst.json()
        assert data_inst["submission_id"] == str(submission.id)


@pytest.mark.anyio
async def test_evaluation_endpoint_not_found():
    """Verify 404 is returned when submission does not exist."""
    _, token = await create_user_with_role("STUDENT")
    transport = ASGITransport(app=app)
    random_id = uuid.uuid4()
    endpoint = f"/api/v1/student/submissions/{random_id}/evaluation"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 404
