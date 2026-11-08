r"""
Database Foundation Test Suite
Project: Vedantu Online Coding Assessment Platform (Stage 2.6)
Workspace: E:\VedantuCodingPlatform_New

Comprehensive test suite verifying PostgreSQL 16 connectivity, SQLAlchemy 2.0 ORM
domain models, UUID primary keys, foreign key constraints, cascading deletions,
unique constraints, and session transaction lifecycles.
"""

import sys
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import (
    async_engine,
    async_session_factory,
    check_database_connection,
    get_db,
)
from app.models.user import User
from app.models.role import Role, UserRole
from app.models.assessment import Assessment
from app.models.question import Question
from app.models.programming_language import ProgrammingLanguage
from app.models.test_case import TestCase
from app.models.submission import Submission


@pytest.fixture
async def db_session():
    """Provides an isolated async database session with automatic rollback."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.mark.anyio
async def test_database_connectivity_live():
    """Verify live async connectivity to the PostgreSQL container."""
    is_connected = await check_database_connection()
    assert is_connected is True, "Failed to connect to PostgreSQL container"


@pytest.mark.anyio
async def test_fastapi_get_db_dependency():
    """Verify FastAPI get_db dependency yields a healthy session and manages lifecycle."""
    generator = get_db()
    session = await anext(generator)
    assert session is not None
    assert session.is_active is True

    # Closing generator verifies commit/close lifecycle
    try:
        await anext(generator)
    except StopAsyncIteration:
        pass


@pytest.mark.anyio
async def test_user_creation_and_uuid_generation(db_session):
    """Verify User model creation, UUID primary key assignment, and UTC timestamps."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        full_name="Test Student",
        email=f"student_{unique_suffix}@vedantu.com",
        password_hash="argon2id$mock_hash_for_testing",
        status="ACTIVE",
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.status == "ACTIVE"


@pytest.mark.anyio
async def test_user_email_uniqueness_constraint(db_session):
    """Verify duplicate user email addresses are rejected with IntegrityError."""
    unique_email = f"duplicate_{uuid.uuid4().hex[:8]}@vedantu.com"

    user1 = User(
        full_name="User One",
        email=unique_email,
        password_hash="hash_1",
    )
    db_session.add(user1)
    await db_session.flush()

    user2 = User(
        full_name="User Two",
        email=unique_email,
        password_hash="hash_2",
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.anyio
async def test_role_and_user_role_assignment(db_session):
    """Verify Role creation, UserRole linking, and compound unique constraint."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        full_name="Instructor Candidate",
        email=f"inst_{suffix}@vedantu.com",
        password_hash="hash_instructor",
    )
    role = Role(
        name=f"TEST_ROLE_{suffix}",
        description="Temporary test role",
    )
    db_session.add_all([user, role])
    await db_session.flush()

    # Link user to role
    user_role = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(user_role)
    await db_session.flush()

    assert user_role.id is not None
    assert user_role.user_id == user.id
    assert user_role.role_id == role.id

    # Duplicate link must violate uq_user_roles_user_role
    duplicate_link = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(duplicate_link)
    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.anyio
async def test_seeded_programming_languages_exist(db_session):
    """Verify seeded Python 3 and Java runtimes exist with accurate Judge0 IDs."""
    stmt_py = select(ProgrammingLanguage).where(ProgrammingLanguage.judge0_language_id == 71)
    res_py = await db_session.execute(stmt_py)
    python_lang = res_py.scalar_one_or_none()
    assert python_lang is not None, "Python 3 runtime (ID 71) missing"
    assert python_lang.name == "Python 3"
    assert python_lang.is_active is True

    stmt_java = select(ProgrammingLanguage).where(ProgrammingLanguage.judge0_language_id == 62)
    res_java = await db_session.execute(stmt_java)
    java_lang = res_java.scalar_one_or_none()
    assert java_lang is not None, "Java runtime (ID 62) missing"
    assert java_lang.name == "Java"
    assert java_lang.is_active is True


@pytest.mark.anyio
async def test_assessment_question_testcase_hierarchy_and_cascade(db_session):
    """
    Verify parent-child hierarchy:
    Assessment -> Questions -> TestCases,
    and verify CASCADE deletion cleans up child questions and test cases.
    """
    suffix = uuid.uuid4().hex[:8]
    creator = User(
        full_name="Assessment Author",
        email=f"author_{suffix}@vedantu.com",
        password_hash="hash_author",
    )
    db_session.add(creator)
    await db_session.flush()

    # Create Assessment
    assessment = Assessment(
        title=f"Data Structures Test {suffix}",
        description="Comprehensive evaluation of trees and graphs",
        duration_minutes=90,
        total_marks=100,
        difficulty="HARD",
        status="DRAFT",
        created_by=creator.id,
    )
    db_session.add(assessment)
    await db_session.flush()

    # Create Question
    question = Question(
        assessment_id=assessment.id,
        title="Invert Binary Tree",
        problem_description="Given the root of a binary tree, invert the tree and return its root.",
        difficulty="EASY",
        marks=20,
        display_order=1,
    )
    db_session.add(question)
    await db_session.flush()

    # Create Public and Hidden TestCases
    sample_tc = TestCase(
        question_id=question.id,
        input_data="[4,2,7,1,3,6,9]",
        expected_output="[4,7,2,9,6,3,1]",
        is_hidden=False,
        marks=5,
        display_order=1,
    )
    hidden_tc = TestCase(
        question_id=question.id,
        input_data="[]",
        expected_output="[]",
        is_hidden=True,
        marks=15,
        display_order=2,
    )
    db_session.add_all([sample_tc, hidden_tc])
    await db_session.flush()

    question_id = question.id
    assessment_id = assessment.id

    # Verify entities exist
    stmt_tc = select(TestCase).where(TestCase.question_id == question_id)
    tcs = (await db_session.execute(stmt_tc)).scalars().all()
    assert len(tcs) == 2

    # Cascade deletion: Deleting the assessment must cascade and delete questions & test cases
    await db_session.delete(assessment)
    await db_session.flush()

    # Verify Question was deleted
    q_check = (await db_session.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    assert q_check is None

    # Verify TestCases were deleted
    tc_check = (await db_session.execute(select(TestCase).where(TestCase.question_id == question_id))).scalars().all()
    assert len(tc_check) == 0


@pytest.mark.anyio
async def test_submission_and_restrict_cascades(db_session):
    """
    Verify Submission entity creation, default status, relationships,
    and verify ON DELETE RESTRICT prevents deleting referenced Users.
    """
    suffix = uuid.uuid4().hex[:8]

    # Create creator, assessment, question, and student
    creator = User(
        full_name="Assessment Instructor",
        email=f"inst_{suffix}@vedantu.com",
        password_hash="hash_inst",
    )
    student = User(
        full_name="Candidate Student",
        email=f"student_{suffix}@vedantu.com",
        password_hash="hash_student",
    )
    db_session.add_all([creator, student])
    await db_session.flush()

    assessment = Assessment(
        title=f"Python Contest {suffix}",
        duration_minutes=60,
        total_marks=50,
        created_by=creator.id,
    )
    db_session.add(assessment)
    await db_session.flush()

    question = Question(
        assessment_id=assessment.id,
        title="Sum of Two Integers",
        problem_description="Calculate sum without + operator",
        marks=50,
    )
    db_session.add(question)
    await db_session.flush()

    # Fetch Python language
    stmt_lang = select(ProgrammingLanguage).where(ProgrammingLanguage.judge0_language_id == 71)
    py_lang = (await db_session.execute(stmt_lang)).scalar_one()

    # Create submission
    submission = Submission(
        user_id=student.id,
        question_id=question.id,
        programming_language_id=py_lang.id,
        source_code="def solve(a, b): return a + b",
        status="PENDING",
        score=0.0,
    )
    db_session.add(submission)
    await db_session.flush()

    assert submission.id is not None
    assert submission.status == "PENDING"
    assert submission.created_at is not None

    # Deleting student must fail due to ON DELETE RESTRICT
    await db_session.delete(student)
    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()
