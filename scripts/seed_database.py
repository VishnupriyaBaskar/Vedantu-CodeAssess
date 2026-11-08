r"""
Database Seeding Script
Project: Vedantu Online Coding Assessment Platform (Stage 2.6)
Workspace: E:\VedantuCodingPlatform_New

Seeds fundamental platform roles (ADMIN, INSTRUCTOR, STUDENT) and initial
programming languages (Python 3, Java) aligned with Judge0 runtime identifiers.
Idempotent and safe to run multiple times.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select
from app.core.database import async_session_factory, dispose_database_engine
from app.models.role import Role
from app.models.programming_language import ProgrammingLanguage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("seed_database")

DEFAULT_ROLES = [
    {
        "name": "ADMIN",
        "description": "System Administrator with platform-wide governance and user management permissions.",
    },
    {
        "name": "INSTRUCTOR",
        "description": "Assessment creator and evaluator with question authoring and grading permissions.",
    },
    {
        "name": "STUDENT",
        "description": "Candidate participating in coding assessments and submitting solutions.",
    },
]

DEFAULT_LANGUAGES = [
    {
        "name": "Python 3",
        "judge0_language_id": 71,
        "version": "3.8.1",
        "is_active": True,
    },
    {
        "name": "Java",
        "judge0_language_id": 62,
        "version": "13.0.1",
        "is_active": True,
    },
]


async def seed_roles(session) -> int:
    """Seed initial system roles idempotently."""
    created_count = 0
    for role_def in DEFAULT_ROLES:
        stmt = select(Role).where(Role.name == role_def["name"])
        result = await session.execute(stmt)
        existing_role = result.scalar_one_or_none()

        if existing_role is None:
            new_role = Role(
                name=role_def["name"],
                description=role_def["description"],
            )
            session.add(new_role)
            created_count += 1
            logger.info("Queued role for creation: %s", role_def["name"])
        else:
            logger.info("Role already exists: %s", role_def["name"])

    return created_count


async def seed_programming_languages(session) -> int:
    """Seed supported programming language runtimes idempotently."""
    created_count = 0
    for lang_def in DEFAULT_LANGUAGES:
        stmt = select(ProgrammingLanguage).where(
            (ProgrammingLanguage.name == lang_def["name"])
            | (ProgrammingLanguage.judge0_language_id == lang_def["judge0_language_id"])
        )
        result = await session.execute(stmt)
        existing_lang = result.scalar_one_or_none()

        if existing_lang is None:
            new_lang = ProgrammingLanguage(
                name=lang_def["name"],
                judge0_language_id=lang_def["judge0_language_id"],
                version=lang_def["version"],
                is_active=lang_def["is_active"],
            )
            session.add(new_lang)
            created_count += 1
            logger.info(
                "Queued language for creation: %s (Judge0 ID %d, version %s)",
                lang_def["name"],
                lang_def["judge0_language_id"],
                lang_def["version"],
            )
        else:
            # Update attributes if needed
            existing_lang.version = lang_def["version"]
            existing_lang.is_active = lang_def["is_active"]
            logger.info(
                "Language already exists (updated if needed): %s (Judge0 ID %d)",
                existing_lang.name,
                existing_lang.judge0_language_id,
            )

    return created_count


async def main() -> None:
    logger.info("Starting database seeding process...")
    try:
        async with async_session_factory() as session:
            async with session.begin():
                roles_created = await seed_roles(session)
                langs_created = await seed_programming_languages(session)

        logger.info(
            "Seeding completed successfully: %d role(s) created, %d language(s) created.",
            roles_created,
            langs_created,
        )
    finally:
        await dispose_database_engine()


if __name__ == "__main__":
    asyncio.run(main())
