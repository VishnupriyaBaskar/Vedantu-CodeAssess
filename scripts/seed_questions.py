r"""
Idempotent Question Bank and Assessment Seeder Script
Project: Vedantu Online Coding Assessment Platform
Workspace: E:\VedantuCodingPlatform_New

Seeds 18 curated topics and 54 foundational questions with verified test cases
and creates a flagship published assessment for candidate testing.
"""

import asyncio
import logging
import sys
from pathlib import Path
import uuid

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import async_session_factory, dispose_database_engine
from app.models.user import User
from app.models.role import Role
from app.models.question import Question
from app.models.test_case import TestCase
from app.models.assessment import Assessment
from app.core.question_seed_data import SEED_QUESTIONS, TOPIC_DESCRIPTIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("seed_questions")


async def get_or_create_system_instructor(session) -> uuid.UUID:
    """Finds an existing instructor or creates a system instructor for seeded questions."""
    stmt = (
        select(User)
        .join(User.roles)
        .where(Role.name.in_(["INSTRUCTOR", "ADMIN"]))
        .limit(1)
    )
    res = await session.execute(stmt)
    instructor = res.scalar_one_or_none()
    if instructor:
        logger.info("Using existing instructor account: %s", instructor.email)
        return instructor.id

    # Fallback to any user
    any_user_res = await session.execute(select(User).limit(1))
    any_user = any_user_res.scalar_one_or_none()
    if any_user:
        return any_user.id

    return uuid.uuid4()


async def seed_question_bank(session, instructor_id: uuid.UUID) -> tuple[int, int]:
    """
    Seeds the 54 questions across 18 topics into the Question Bank idempotently.
    Returns (created_questions_count, created_test_cases_count).
    """
    created_q = 0
    created_tc = 0

    for q_def in SEED_QUESTIONS:
        # Check if question with this title already exists
        stmt = (
            select(Question)
            .options(selectinload(Question.test_cases))
            .where(Question.title == q_def["title"])
        )
        res = await session.execute(stmt)
        existing_q = res.scalar_one_or_none()

        if existing_q is None:
            q_id = uuid.uuid4()
            new_question = Question(
                id=q_id,
                assessment_id=None,  # Belongs to Question Bank
                title=q_def["title"],
                problem_description=q_def["problem_description"],
                input_format=q_def["input_format"],
                output_format=q_def["output_format"],
                constraints=q_def["constraints"],
                difficulty=q_def["difficulty"],
                topic=q_def["topic"],
                marks=q_def["marks"],
                time_limit_seconds=q_def["time_limit_seconds"],
                memory_limit_mb=q_def["memory_limit_mb"],
                starter_code=q_def.get("starter_code"),
                tags="SEED_SAMPLE_DATA",
                is_archived=False,
                created_by=instructor_id,
            )
            session.add(new_question)
            created_q += 1

            # Add test cases
            for order, tc_def in enumerate(q_def["test_cases"], start=1):
                tc = TestCase(
                    id=uuid.uuid4(),
                    question_id=q_id,
                    input_data=tc_def["input_data"],
                    expected_output=tc_def["expected_output"],
                    explanation=tc_def.get("explanation"),
                    is_hidden=tc_def["is_hidden"],
                    category="SAMPLE" if not tc_def["is_hidden"] else "FUNCTIONAL",
                    marks=tc_def.get("marks", 5),
                    display_order=order,
                )
                session.add(tc)
                created_tc += 1
        else:
            # Check if existing question has test cases
            if not existing_q.test_cases:
                logger.info("Question '%s' exists without test cases. Adding test cases...", existing_q.title)
                for order, tc_def in enumerate(q_def["test_cases"], start=1):
                    tc = TestCase(
                        id=uuid.uuid4(),
                        question_id=existing_q.id,
                        input_data=tc_def["input_data"],
                        expected_output=tc_def["expected_output"],
                        explanation=tc_def.get("explanation"),
                        is_hidden=tc_def["is_hidden"],
                        category="SAMPLE" if not tc_def["is_hidden"] else "FUNCTIONAL",
                        marks=tc_def.get("marks", 5),
                        display_order=order,
                    )
                    session.add(tc)
                    created_tc += 1

    return created_q, created_tc


async def seed_flagship_assessment(session, instructor_id: uuid.UUID) -> bool:
    """
    Creates a flagship published assessment with complete test cases if not already present.
    Ensures students have a fully-functional, pre-configured assessment.
    """
    title = "Core DSA & Problem Solving Assessment"
    stmt = (
        select(Assessment)
        .options(selectinload(Assessment.questions))
        .where(Assessment.title == title)
    )
    res = await session.execute(stmt)
    existing_a = res.scalar_one_or_none()

    if existing_a is not None:
        logger.info("Flagship assessment '%s' already exists.", title)
        return False

    assessment_id = uuid.uuid4()
    assessment = Assessment(
        id=assessment_id,
        title=title,
        description="Comprehensive evaluation of algorithmic problem solving, array manipulation, and dynamic programming.",
        instructions="Read each problem statement carefully. Ensure your solution passes all visible sample test cases before final submission. Time limit is strictly enforced.",
        duration_minutes=60,
        total_marks=60,
        passing_marks=30,
        difficulty="MEDIUM",
        status="PUBLISHED",
        allowed_languages="ALL_ACTIVE",
        created_by=instructor_id,
        proctoring_config={
            "enable_tab_monitoring": True,
            "enable_fullscreen_monitoring": True,
            "max_allowed_tab_switches": 3,
            "alert_on_paste": True,
        },
    )
    session.add(assessment)

    # Attach 3 questions specifically to this assessment
    exam_questions = [
        {
            "title": "Two Sum Target Identification",
            "topic": "Arrays",
            "difficulty": "EASY",
            "marks": 20,
            "problem_description": "Given an array of N integers and target T, print 'YES' if any two distinct elements sum to T, otherwise print 'NO'.",
            "input_format": "Line 1: N and T. Line 2: N space-separated integers.",
            "output_format": "Print 'YES' or 'NO'.",
            "constraints": "2 <= N <= 10^5",
            "time_limit_seconds": 2.0,
            "memory_limit_mb": 256,
            "starter_code": "import sys\n\ndef solve():\n    tokens = sys.stdin.read().split()\n    if not tokens: return\n    n, t = int(tokens[0]), int(tokens[1])\n    arr = [int(tokens[i]) for i in range(2, 2 + n)]\n    seen = set()\n    for x in arr:\n        if (t - x) in seen:\n            print('YES')\n            return\n        seen.add(x)\n    print('NO')\n\nif __name__ == '__main__':\n    solve()\n",
            "test_cases": [
                {"input_data": "5 9\n2 7 11 15 3", "expected_output": "YES", "is_hidden": False, "marks": 10, "explanation": "2 + 7 = 9"},
                {"input_data": "4 10\n1 2 3 4", "expected_output": "NO", "is_hidden": True, "marks": 5, "explanation": "No sum 10"},
                {"input_data": "5 0\n-5 2 3 4 5", "expected_output": "YES", "is_hidden": True, "marks": 5, "explanation": "-5 + 5 = 0"},
            ],
        },
        {
            "title": "Reverse Words in a String Sentence",
            "topic": "Strings",
            "difficulty": "MEDIUM",
            "marks": 20,
            "problem_description": "Given a sentence string with words separated by spaces, reverse the order of the words.",
            "input_format": "A single line containing space-separated words.",
            "output_format": "Print the words in reverse order separated by space.",
            "constraints": "1 <= length <= 10^5",
            "time_limit_seconds": 2.0,
            "memory_limit_mb": 256,
            "starter_code": "import sys\n\ndef solve():\n    words = sys.stdin.read().split()\n    print(' '.join(reversed(words)))\n\nif __name__ == '__main__':\n    solve()\n",
            "test_cases": [
                {"input_data": "the sky is blue", "expected_output": "blue is sky the", "is_hidden": False, "marks": 10, "explanation": "Reversed words"},
                {"input_data": "hello world", "expected_output": "world hello", "is_hidden": True, "marks": 5, "explanation": "Reversed 2 words"},
                {"input_data": "a b c d", "expected_output": "d c b a", "is_hidden": True, "marks": 5, "explanation": "Reversed characters"},
            ],
        },
        {
            "title": "Climbing Stairs Path Variations",
            "topic": "Dynamic Programming",
            "difficulty": "MEDIUM",
            "marks": 20,
            "problem_description": "You are climbing a staircase with N steps. Each time you can climb 1 or 2 steps. Calculate in how many distinct ways you can reach the top.",
            "input_format": "Single integer N.",
            "output_format": "Print the number of distinct ways.",
            "constraints": "1 <= N <= 40",
            "time_limit_seconds": 2.0,
            "memory_limit_mb": 256,
            "starter_code": "import sys\n\ndef solve():\n    n = int(sys.stdin.read().strip())\n    if n <= 2:\n        print(n)\n        return\n    a, b = 1, 2\n    for _ in range(3, n + 1):\n        a, b = b, a + b\n    print(b)\n\nif __name__ == '__main__':\n    solve()\n",
            "test_cases": [
                {"input_data": "3", "expected_output": "3", "is_hidden": False, "marks": 10, "explanation": "1+1+1, 1+2, 2+1"},
                {"input_data": "4", "expected_output": "5", "is_hidden": True, "marks": 5, "explanation": "5 distinct paths"},
                {"input_data": "6", "expected_output": "13", "is_hidden": True, "marks": 5, "explanation": "13 distinct paths"},
            ],
        },
    ]

    for idx, q_info in enumerate(exam_questions, start=1):
        q_id = uuid.uuid4()
        q = Question(
            id=q_id,
            assessment_id=assessment_id,
            title=q_info["title"],
            problem_description=q_info["problem_description"],
            input_format=q_info["input_format"],
            output_format=q_info["output_format"],
            constraints=q_info["constraints"],
            difficulty=q_info["difficulty"],
            topic=q_info["topic"],
            marks=q_info["marks"],
            time_limit_seconds=q_info["time_limit_seconds"],
            memory_limit_mb=q_info["memory_limit_mb"],
            starter_code=q_info.get("starter_code"),
            display_order=idx,
            tags="FLAGSHIP_ASSESSMENT",
            is_archived=False,
            created_by=instructor_id,
        )
        session.add(q)

        for tc_idx, tc_def in enumerate(q_info["test_cases"], start=1):
            tc = TestCase(
                id=uuid.uuid4(),
                question_id=q_id,
                input_data=tc_def["input_data"],
                expected_output=tc_def["expected_output"],
                explanation=tc_def.get("explanation"),
                is_hidden=tc_def["is_hidden"],
                category="SAMPLE" if not tc_def["is_hidden"] else "FUNCTIONAL",
                marks=tc_def.get("marks", 5),
                display_order=tc_idx,
            )
            session.add(tc)

    logger.info("Queued flagship assessment '%s' with 3 fully-configured questions.", title)
    return True


async def main():
    logger.info("Starting question bank and assessment seeding...")
    try:
        async with async_session_factory() as session:
            async with session.begin():
                instructor_id = await get_or_create_system_instructor(session)
                q_created, tc_created = await seed_question_bank(session, instructor_id)
                assess_created = await seed_flagship_assessment(session, instructor_id)

        logger.info(
            "Seeding completed successfully: %d question(s) created, %d test case(s) created, Flagship assessment: %s.",
            q_created,
            tc_created,
            "Created" if assess_created else "Existed",
        )
    finally:
        await dispose_database_engine()


if __name__ == "__main__":
    asyncio.run(main())
