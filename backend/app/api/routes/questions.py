r"""
Question Bank and Test Case API Endpoints
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New

Handles Question Bank CRUD, difficulty/topic categorization, test case management,
and strict test case isolation between candidates and instructors.
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state

from app.api.deps import get_current_user, require_instructor
from app.core.database import get_db
from app.models.question import Question
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.question import (
    QuestionAdminResponse,
    QuestionCreate,
    QuestionPublicResponse,
    QuestionUpdate,
    QuestionValidationResponse,
    TestCaseAdminResponse,
    TestCaseCreate,
    TestCasePublicResponse,
    TestCaseUpdate,
)

router = APIRouter(prefix="/questions", tags=["Question Bank"])


def _to_admin_response(q: Question) -> QuestionAdminResponse:
    """Helper to convert Question ORM entity to QuestionAdminResponse."""
    tc_admins = [
        TestCaseAdminResponse(
            id=tc.id,
            question_id=tc.question_id,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            explanation=tc.explanation,
            marks=tc.marks,
            display_order=tc.display_order,
            is_hidden=tc.is_hidden,
            category=tc.category or ("SAMPLE" if not tc.is_hidden else "FUNCTIONAL"),
        )
        for tc in sorted(q.test_cases, key=lambda x: x.display_order)
    ]

    state = instance_state(q)
    if "submissions" in state.dict and state.dict["submissions"]:
        subs = state.dict["submissions"]
        total_attempts = len(subs)
        solved_count = sum(
            1 for s in subs if s.status == "ACCEPTED" or s.score >= q.marks
        )
        success_rate = (
            round((solved_count / total_attempts * 100.0), 2)
            if total_attempts > 0
            else 0.0
        )
    else:
        total_attempts = 0
        solved_count = 0
        success_rate = 0.0

    return QuestionAdminResponse(
        id=q.id,
        assessment_id=q.assessment_id,
        title=q.title,
        problem_description=q.problem_description,
        input_format=q.input_format,
        output_format=q.output_format,
        constraints=q.constraints,
        difficulty=q.difficulty,
        topic=q.topic,
        marks=q.marks,
        time_limit_seconds=q.time_limit_seconds,
        memory_limit_mb=q.memory_limit_mb,
        display_order=q.display_order,
        tags=q.tags,
        starter_code=q.starter_code,
        is_archived=q.is_archived,
        created_by=q.created_by,
        test_cases=tc_admins,
        total_attempts=total_attempts,
        solved_count=solved_count,
        success_rate=success_rate,
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


def _to_public_response(q: Question) -> QuestionPublicResponse:
    """Helper to convert Question ORM entity to candidate-safe QuestionPublicResponse."""
    samples = [
        TestCasePublicResponse(
            id=tc.id,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            explanation=tc.explanation,
            marks=tc.marks,
            display_order=tc.display_order,
            category=tc.category or "SAMPLE",
        )
        for tc in sorted(q.test_cases, key=lambda x: x.display_order)
        if not tc.is_hidden
    ]
    return QuestionPublicResponse(
        id=q.id,
        title=q.title,
        problem_description=q.problem_description,
        input_format=q.input_format,
        output_format=q.output_format,
        constraints=q.constraints,
        difficulty=q.difficulty,
        topic=q.topic,
        marks=q.marks,
        time_limit_seconds=q.time_limit_seconds,
        memory_limit_mb=q.memory_limit_mb,
        display_order=q.display_order,
        tags=q.tags,
        starter_code=q.starter_code,
        sample_test_cases=samples,
    )


@router.post(
    "",
    response_model=QuestionAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question in the Question Bank (Instructor/Admin)",
)
async def create_question(
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> QuestionAdminResponse:
    """Creates a new question with optional initial sample and hidden test cases."""
    question_id = uuid.uuid4()
    question = Question(
        id=question_id,
        assessment_id=data.assessment_id,
        title=data.title,
        problem_description=data.problem_description,
        input_format=data.input_format,
        output_format=data.output_format,
        constraints=data.constraints,
        difficulty=data.difficulty,
        topic=data.topic,
        marks=data.marks,
        time_limit_seconds=data.time_limit_seconds,
        memory_limit_mb=data.memory_limit_mb,
        display_order=data.display_order,
        tags=data.tags,
        starter_code=data.starter_code,
        is_archived=False,
        created_by=current_user.id,
    )
    db.add(question)

    for tc_data in data.test_cases:
        tc = TestCase(
            id=uuid.uuid4(),
            question_id=question_id,
            input_data=tc_data.input_data,
            expected_output=tc_data.expected_output,
            explanation=tc_data.explanation,
            marks=tc_data.marks,
            display_order=tc_data.display_order,
            is_hidden=tc_data.is_hidden,
            category=tc_data.category or ("SAMPLE" if not tc_data.is_hidden else "FUNCTIONAL"),
        )
        db.add(tc)

    await db.commit()

    # Re-fetch with loaded test cases
    stmt = (
        select(Question)
        .options(selectinload(Question.test_cases))
        .where(Question.id == question_id)
    )
    result = await db.execute(stmt)
    created_q = result.scalar_one()
    return _to_admin_response(created_q)


@router.get(
    "",
    response_model=List[QuestionAdminResponse],
    summary="List questions in Question Bank with filters (Instructor/Admin)",
)
async def list_questions(
    topic: Optional[str] = Query(None, description="Filter by topic"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (EASY, MEDIUM, HARD)"),
    search: Optional[str] = Query(None, description="Search by title, topic, or tags"),
    is_archived: Optional[bool] = Query(False, description="Filter archived status"),
    assessment_id: Optional[uuid.UUID] = Query(None, description="Filter by assessment association"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> List[QuestionAdminResponse]:
    """List questions in Question Bank with optional topic, difficulty, search, and archive filters."""
    query = select(Question).options(
        selectinload(Question.test_cases),
        selectinload(Question.submissions),
    )

    if topic:
        query = query.where(Question.topic == topic)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    if is_archived is not None:
        query = query.where(Question.is_archived == is_archived)
    if assessment_id is not None:
        query = query.where(Question.assessment_id == assessment_id)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Question.title.ilike(search_pattern))
            | (Question.topic.ilike(search_pattern))
            | (Question.tags.ilike(search_pattern))
        )

    query = query.order_by(Question.display_order, Question.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    questions = result.scalars().all()
    return [_to_admin_response(q) for q in questions]


@router.get(
    "/{question_id}",
    summary="Get question details (Instructors receive all test cases; Students receive only public samples)",
)
async def get_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get question by ID.
    Enforces strict test case confidentiality:
    - Instructors/Admins: receives full suite of test cases (both sample and hidden).
    - Students: receives QuestionPublicResponse containing ONLY sample test cases.
    """
    stmt = (
        select(Question)
        .options(selectinload(Question.test_cases))
        .where(Question.id == question_id)
    )
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    user_roles = {r.name for r in current_user.roles}
    is_instructor_or_admin = bool(user_roles.intersection({"INSTRUCTOR", "ADMIN"}))

    if not is_instructor_or_admin:
        if question.is_archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found.",
            )
        return _to_public_response(question)

    return _to_admin_response(question)


@router.put(
    "/{question_id}",
    response_model=QuestionAdminResponse,
    summary="Update question details (Instructor/Admin)",
)
async def update_question(
    question_id: uuid.UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> QuestionAdminResponse:
    """Updates question fields and parameters."""
    stmt = (
        select(Question)
        .options(selectinload(Question.test_cases))
        .where(Question.id == question_id)
    )
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(question, field, value)

    await db.commit()

    refetch_stmt = (
        select(Question)
        .options(selectinload(Question.test_cases))
        .where(Question.id == question_id)
    )
    refetch_res = await db.execute(refetch_stmt)
    refetched_q = refetch_res.scalar_one()
    return _to_admin_response(refetched_q)


@router.delete(
    "/{question_id}",
    summary="Soft-delete / Archive a question (Instructor/Admin)",
)
async def archive_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Archives question to prevent breaking historical assessments while hiding from active pools."""
    stmt = select(Question).where(Question.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    question.is_archived = True
    await db.commit()
    return {"detail": "Question archived successfully."}


@router.post(
    "/{question_id}/test-cases",
    response_model=TestCaseAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a test case to a question (Instructor/Admin)",
)
async def add_test_case(
    question_id: uuid.UUID,
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> TestCaseAdminResponse:
    """Adds a new sample or hidden test case to the specified question."""
    stmt = select(Question).where(Question.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    tc = TestCase(
        id=uuid.uuid4(),
        question_id=question_id,
        input_data=data.input_data,
        expected_output=data.expected_output,
        explanation=data.explanation,
        marks=data.marks,
        display_order=data.display_order,
        is_hidden=data.is_hidden,
        category=data.category or ("SAMPLE" if not data.is_hidden else "FUNCTIONAL"),
    )
    db.add(tc)
    await db.commit()

    return TestCaseAdminResponse(
        id=tc.id,
        question_id=tc.question_id,
        input_data=tc.input_data,
        expected_output=tc.expected_output,
        explanation=tc.explanation,
        marks=tc.marks,
        display_order=tc.display_order,
        is_hidden=tc.is_hidden,
        category=tc.category,
    )


@router.put(
    "/{question_id}/test-cases/{test_case_id}",
    response_model=TestCaseAdminResponse,
    summary="Update a test case in a question (Instructor/Admin)",
)
async def update_test_case(
    question_id: uuid.UUID,
    test_case_id: uuid.UUID,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> TestCaseAdminResponse:
    """Updates properties of an existing test case (category, marks, input/output)."""
    stmt = select(TestCase).where(
        TestCase.id == test_case_id,
        TestCase.question_id == question_id,
    )
    result = await db.execute(stmt)
    tc = result.scalar_one_or_none()
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(tc, field, val)

    await db.commit()
    await db.refresh(tc)

    return TestCaseAdminResponse(
        id=tc.id,
        question_id=tc.question_id,
        input_data=tc.input_data,
        expected_output=tc.expected_output,
        explanation=tc.explanation,
        marks=tc.marks,
        display_order=tc.display_order,
        is_hidden=tc.is_hidden,
        category=tc.category,
    )


@router.post(
    "/{question_id}/validate",
    response_model=QuestionValidationResponse,
    summary="Validate question test cases and mark alignment before publishing (Instructor/Admin)",
)
async def validate_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> QuestionValidationResponse:
    """Pre-flight validation ensuring adequate test coverage across sample, functional, and edge cases."""
    stmt = (
        select(Question)
        .options(selectinload(Question.test_cases))
        .where(Question.id == question_id)
    )
    res = await db.execute(stmt)
    q = res.scalar_one_or_none()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    errors = []
    warnings = []

    sample_tests = [tc for tc in q.test_cases if tc.category == "SAMPLE" or not tc.is_hidden]
    functional_tests = [tc for tc in q.test_cases if tc.category == "FUNCTIONAL" and tc.is_hidden]
    edge_tests = [tc for tc in q.test_cases if tc.category == "EDGE_CASE"]

    if not sample_tests:
        errors.append("Question must contain at least one public sample test case.")
    if not functional_tests and not edge_tests:
        errors.append("Question must contain at least one hidden evaluation test case (functional or edge case).")

    total_test_marks = sum(tc.marks for tc in q.test_cases)
    if total_test_marks == 0:
        errors.append("Total test case marks cannot be zero.")
    elif total_test_marks != q.marks:
        warnings.append(
            f"Sum of test case marks ({total_test_marks}) does not equal question total marks ({q.marks})."
        )

    for idx, tc in enumerate(q.test_cases, 1):
        if not tc.input_data or not tc.input_data.strip():
            warnings.append(f"Test case #{idx} has empty input data.")
        if not tc.expected_output or not tc.expected_output.strip():
            errors.append(f"Test case #{idx} has empty expected output.")

    is_valid = len(errors) == 0

    return QuestionValidationResponse(
        question_id=q.id,
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        sample_test_count=len(sample_tests),
        functional_test_count=len(functional_tests),
        edge_test_count=len(edge_tests),
        total_test_marks=total_test_marks,
        question_marks=q.marks,
    )


@router.delete(
    "/{question_id}/test-cases/{test_case_id}",
    summary="Delete a test case from a question (Instructor/Admin)",
)
async def delete_test_case(
    question_id: uuid.UUID,
    test_case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Deletes a test case."""
    stmt = select(TestCase).where(
        TestCase.id == test_case_id,
        TestCase.question_id == question_id,
    )
    result = await db.execute(stmt)
    tc = result.scalar_one_or_none()
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    await db.delete(tc)
    await db.commit()
    return {"detail": "Test case deleted successfully."}
