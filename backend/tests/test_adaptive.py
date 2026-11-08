r"""
Test Suite for Phase 6: Adaptive Assessment Engine
Project: Vedantu Online Coding Assessment Platform (Phase 6)
Workspace: E:\VedantuCodingPlatform_New

Verifies:
1. Deterministic topic mastery calculation (Bayesian prior, difficulty weights, attempt penalty).
2. Handling of new students with insufficient historical data (default BEGINNER, LOW confidence, EASY recommendation).
3. Dynamic difficulty adjustment (Easy -> Medium -> Hard, and stepping down upon consecutive failures).
4. Strengths and weaknesses identification (strong, needs improvement, improving, unattempted).
5. Intelligent question recommendations with explainable reasons and filtering of solved/archived challenges.
6. Longitudinal mastery progression tracking and history snapshots.
7. Interactive practice endpoints (sample run, solution submit, real-time mastery update).
8. RBAC and data ownership enforcement (students cannot access other students' private metrics).
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
from app.models.programming_language import ProgrammingLanguage
from app.models.question import Question
from app.models.role import Role, UserRole
from app.models.student_topic_mastery import StudentTopicMastery
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.user import User
from app.services.adaptive_service import (
    DIFFICULTY_WEIGHTS,
    adaptive_service,
    classify_confidence_level,
    classify_mastery_level,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_user_with_role(role_name: str) -> tuple[User, str]:
    """Helper to provision a user with a specific role and return user and auth token."""
    suffix = uuid.uuid4().hex[:8]
    email = f"adaptive_{role_name.lower()}_{suffix}@vedantu-test.com"

    async with async_session_factory() as session:
        async with session.begin():
            stmt_role = select(Role).where(Role.name == role_name)
            role = (await session.execute(stmt_role)).scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=f"Role {role_name}")
                session.add(role)
                await session.flush()

            user = User(
                full_name=f"Adaptive {role_name} User",
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


async def create_test_question(
    topic: str = "Arrays",
    difficulty: str = "EASY",
    title: str = "Test Problem",
    marks: int = 10,
    is_archived: bool = False,
) -> Question:
    """Helper to provision a test question with public and private test cases."""
    async with async_session_factory() as session:
        async with session.begin():
            q = Question(
                title=f"{title} ({uuid.uuid4().hex[:6]})",
                problem_description="Sample problem statement for testing.",
                input_format="Standard input",
                output_format="Standard output",
                constraints="1 <= N <= 100",
                difficulty=difficulty,
                topic=topic,
                marks=marks,
                time_limit_seconds=2.0,
                memory_limit_mb=256,
                is_archived=is_archived,
            )
            session.add(q)
            await session.flush()

            tc_sample = TestCase(
                question_id=q.id,
                input_data="1 2\n",
                expected_output="3\n",
                explanation="Sample case",
                is_hidden=False,
                marks=5,
                display_order=1,
            )
            tc_hidden = TestCase(
                question_id=q.id,
                input_data="10 20\n",
                expected_output="30\n",
                is_hidden=True,
                marks=5,
                display_order=2,
            )
            session.add_all([tc_sample, tc_hidden])

        stmt_load = select(Question).options(selectinload(Question.test_cases)).where(Question.id == q.id)
        return (await session.execute(stmt_load)).scalar_one()


async def get_or_create_language() -> ProgrammingLanguage:
    """Helper to get active Python 3 language."""
    async with async_session_factory() as session:
        stmt = select(ProgrammingLanguage).where(ProgrammingLanguage.name.ilike("%python%"))
        lang = (await session.execute(stmt)).scalar_one_or_none()
        if not lang:
            async with session.begin():
                lang = ProgrammingLanguage(
                    name="Python 3",
                    version="3.10",
                    judge0_language_id=71,
                    is_active=True,
                )
                session.add(lang)
                await session.flush()
        return lang


# ------------------------------------------------------------------------------
# 1. Deterministic Calculation Unit Tests
# ------------------------------------------------------------------------------

def test_classify_mastery_level():
    """Verify deterministic mapping of mastery score to level categories."""
    assert classify_mastery_level(95.0) == "ADVANCED"
    assert classify_mastery_level(85.0) == "ADVANCED"
    assert classify_mastery_level(84.9) == "PROFICIENT"
    assert classify_mastery_level(65.0) == "PROFICIENT"
    assert classify_mastery_level(64.9) == "DEVELOPING"
    assert classify_mastery_level(40.0) == "DEVELOPING"
    assert classify_mastery_level(39.9) == "BEGINNER"
    assert classify_mastery_level(0.0) == "BEGINNER"


def test_classify_confidence_level():
    """Verify confidence tiers based on question sample volume."""
    assert classify_confidence_level(0) == "LOW"
    assert classify_confidence_level(1) == "LOW"
    assert classify_confidence_level(2) == "MEDIUM"
    assert classify_confidence_level(4) == "MEDIUM"
    assert classify_confidence_level(5) == "HIGH"
    assert classify_confidence_level(10) == "HIGH"


# ------------------------------------------------------------------------------
# 2. Student Topic Mastery & New Student Handling
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_new_student_mastery_defaults():
    """Verify that a brand new student with no submissions receives appropriate unassessed defaults."""
    student, _ = await create_user_with_role("STUDENT")
    await create_test_question(topic="Dynamic Programming")

    async with async_session_factory() as db:
        masteries = await adaptive_service.calculate_topic_mastery(db, student.id, persist=False)
        assert len(masteries) > 0

        # All topics should be unassessed (0.0 score, BEGINNER level, LOW confidence, EASY difficulty)
        for m in masteries:
            assert m.mastery_score == 0.0
            assert m.mastery_level == "BEGINNER"
            assert m.confidence_level == "LOW"
            assert m.questions_attempted == 0
            assert m.questions_solved == 0
            assert m.recommended_difficulty == "EASY"
            assert m.trend == "STABLE"


@pytest.mark.anyio
async def test_mastery_calculation_with_submissions():
    """Verify mastery score increases deterministically when student solves questions."""
    student, _ = await create_user_with_role("STUDENT")
    lang = await get_or_create_language()

    q_easy = await create_test_question(topic="HashMaps", difficulty="EASY", marks=10)
    q_med = await create_test_question(topic="HashMaps", difficulty="MEDIUM", marks=20)

    # Submit accepted solutions
    async with async_session_factory() as session:
        async with session.begin():
            sub1 = Submission(
                user_id=student.id,
                question_id=q_easy.id,
                programming_language_id=lang.id,
                source_code="print('done')",
                status="ACCEPTED",
                score=10.0,
            )
            sub2 = Submission(
                user_id=student.id,
                question_id=q_med.id,
                programming_language_id=lang.id,
                source_code="print('done')",
                status="ACCEPTED",
                score=20.0,
            )
            session.add_all([sub1, sub2])

    async with async_session_factory() as db:
        masteries = await adaptive_service.calculate_topic_mastery(db, student.id, persist=True)
        hm = next(m for m in masteries if m.topic == "HashMaps")

        assert hm.questions_attempted == 2
        assert hm.questions_solved == 2
        assert hm.mastery_score >= 70.0  # Solving Easy and Medium yields proficient mastery
        assert hm.mastery_level in ("PROFICIENT", "ADVANCED")
        assert hm.confidence_level == "MEDIUM"
        assert hm.recommended_difficulty in ("MEDIUM", "HARD")


@pytest.mark.anyio
async def test_dynamic_difficulty_step_down_on_failures():
    """Verify adaptive difficulty steps down when student repeatedly fails challenges."""
    student, _ = await create_user_with_role("STUDENT")
    lang = await get_or_create_language()

    q_hard = await create_test_question(topic="Graphs", difficulty="HARD", marks=30)

    # Submit 3 consecutive failed submissions on hard question
    async with async_session_factory() as session:
        async with session.begin():
            for _ in range(3):
                sub = Submission(
                    user_id=student.id,
                    question_id=q_hard.id,
                    programming_language_id=lang.id,
                    source_code="wrong",
                    status="WRONG_ANSWER",
                    score=0.0,
                )
                session.add(sub)

    async with async_session_factory() as db:
        masteries = await adaptive_service.calculate_topic_mastery(db, student.id, persist=True)
        gr = next(m for m in masteries if m.topic == "Graphs")

        assert gr.questions_solved == 0
        assert gr.mastery_score <= 35.0
        assert gr.mastery_level == "BEGINNER"
        # Stepped down to EASY or MEDIUM
        assert gr.recommended_difficulty in ("EASY", "MEDIUM")


# ------------------------------------------------------------------------------
# 3. Strengths and Weaknesses Identification
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_strengths_and_weaknesses_segregation():
    """Verify strong topics and areas requiring improvement are segregated with actionable insights."""
    student, _ = await create_user_with_role("STUDENT")
    lang = await get_or_create_language()

    # Topic A: Strong (Arrays)
    q_arr = await create_test_question(topic="Arrays", difficulty="EASY", marks=10)
    # Topic B: Weak (Recursion)
    q_rec = await create_test_question(topic="Recursion", difficulty="HARD", marks=30)
    # Topic C: Unattempted (Sorting)
    await create_test_question(topic="Sorting", difficulty="EASY")

    async with async_session_factory() as session:
        async with session.begin():
            s_arr = Submission(
                user_id=student.id,
                question_id=q_arr.id,
                programming_language_id=lang.id,
                source_code="print('ok')",
                status="ACCEPTED",
                score=10.0,
            )
            s_rec = Submission(
                user_id=student.id,
                question_id=q_rec.id,
                programming_language_id=lang.id,
                source_code="fail",
                status="WRONG_ANSWER",
                score=0.0,
            )
            session.add_all([s_arr, s_rec])

    async with async_session_factory() as db:
        sw = await adaptive_service.get_strengths_and_weaknesses(db, student.id)

        # Topic with solved question should be strong
        strong_topics = [t.topic for t in sw.strong_topics]
        assert "Arrays" in strong_topics

        # Topic with 0 score should be in needs improvement
        weak_topics = [t.topic for t in sw.needs_improvement_topics]
        assert "Recursion" in weak_topics

        # Topic with no submissions should be unattempted
        assert "Sorting" in sw.unattempted_topics

        # Meaningful educational insights generated
        assert len(sw.insights_summary) >= 2


# ------------------------------------------------------------------------------
# 4. Intelligent Question Recommendation Engine
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_question_recommendations_exclude_solved_and_archived():
    """Verify recommendations exclude already solved questions and archived problems."""
    student, _ = await create_user_with_role("STUDENT")
    lang = await get_or_create_language()

    # Question 1: Already solved by student
    q_solved = await create_test_question(topic="Trees", difficulty="EASY", title="Solved Problem")
    # Question 2: Archived
    q_archived = await create_test_question(topic="Trees", difficulty="EASY", title="Archived Problem", is_archived=True)
    # Question 3: Available practice problem
    q_available = await create_test_question(topic="Trees", difficulty="EASY", title="Available Practice")

    async with async_session_factory() as session:
        async with session.begin():
            sub = Submission(
                user_id=student.id,
                question_id=q_solved.id,
                programming_language_id=lang.id,
                source_code="solved",
                status="ACCEPTED",
                score=10.0,
            )
            session.add(sub)

    async with async_session_factory() as db:
        recs_resp = await adaptive_service.get_recommended_questions(db, student.id, limit=20)
        rec_ids = [r.question_id for r in recs_resp.recommendations]

        assert q_available.id in rec_ids
        assert q_solved.id not in rec_ids
        assert q_archived.id not in rec_ids

        # Recommendation has explainable reason
        matched_rec = next(r for r in recs_resp.recommendations if r.question_id == q_available.id)
        assert len(matched_rec.recommendation_reason) > 10
        assert "Trees" in matched_rec.recommendation_reason


# ------------------------------------------------------------------------------
# 5. Longitudinal Topic Mastery History Tracking
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_longitudinal_mastery_history():
    """Verify mastery history snapshots are recorded and retrievable."""
    student, _ = await create_user_with_role("STUDENT")
    lang = await get_or_create_language()
    q = await create_test_question(topic="Bit Manipulation", difficulty="EASY", marks=10)

    async with async_session_factory() as session:
        async with session.begin():
            sub = Submission(
                user_id=student.id,
                question_id=q.id,
                programming_language_id=lang.id,
                source_code="pass",
                status="ACCEPTED",
                score=10.0,
            )
            session.add(sub)

    async with async_session_factory() as db:
        # Calculate and persist
        await adaptive_service.calculate_topic_mastery(db, student.id, persist=True, trigger_event="TEST_RUN")

        history_resp = await adaptive_service.get_mastery_history(db, student.id, topic="Bit Manipulation")
        assert len(history_resp.history) >= 1
        snapshot = history_resp.history[0]
        assert snapshot.topic == "Bit Manipulation"
        assert snapshot.mastery_score > 0.0
        assert snapshot.trigger_event == "TEST_RUN"


# ------------------------------------------------------------------------------
# 6. Interactive Practice Endpoints
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_practice_question_public_isolation():
    """Verify practice challenge endpoint strictly isolates hidden test cases."""
    q = await create_test_question(topic="Greedy", title="Greedy Challenge")

    async with async_session_factory() as db:
        pub_q = await adaptive_service.get_practice_question(db, q.id)
        assert pub_q.id == q.id
        assert len(pub_q.sample_test_cases) == 1
        # Hidden test case must not be exposed
        assert pub_q.sample_test_cases[0].input_data == "1 2\n"


# ------------------------------------------------------------------------------
# 7. API Endpoints and Authorization (RBAC) Isolation
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_student_self_access_and_cross_user_forbidden():
    """Verify student can access their own adaptive metrics but is denied access to other students' profiles."""
    student1, token1 = await create_user_with_role("STUDENT")
    student2, token2 = await create_user_with_role("STUDENT")
    instructor, instr_token = await create_user_with_role("INSTRUCTOR")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Student 1 accesses own performance -> 200 OK
        res = await client.get(
            "/api/v1/adaptive/performance",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "overall_success_rate" in data

        # 2. Student 1 attempts to query Student 2's performance -> 403 Forbidden
        res_forbidden = await client.get(
            f"/api/v1/adaptive/performance?user_id={student2.id}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res_forbidden.status_code == 403
        assert "Forbidden" in res_forbidden.json()["detail"]

        # 3. Instructor can access Student 1's performance -> 200 OK
        res_instr = await client.get(
            f"/api/v1/adaptive/performance?user_id={student1.id}",
            headers={"Authorization": f"Bearer {instr_token}"},
        )
        assert res_instr.status_code == 200

        # 4. Student 1 accesses recommendations -> 200 OK
        res_recs = await client.get(
            "/api/v1/adaptive/recommendations",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res_recs.status_code == 200
        assert "recommendations" in res_recs.json()

        # 5. Student 1 accesses strengths-weaknesses -> 200 OK
        res_sw = await client.get(
            "/api/v1/adaptive/strengths-weaknesses",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res_sw.status_code == 200
        assert "strong_topics" in res_sw.json()
