r"""
Migration Downgrade Verification Script
Project: Vedantu Online Coding Assessment Platform (Stage 2.6)
Workspace: E:\VedantuCodingPlatform_New

Verifies Alembic migration upgrade and downgrade mechanics in an isolated,
disposable PostgreSQL schema ('test_disposable_schema'), proving that down-revisions
cleanly drop created objects without affecting the live application public schema.
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

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migration_downgrade_verifier")

TEST_SCHEMA = "test_disposable_schema"


def list_tables(sync_conn, schema: str) -> list[str]:
    stmt = text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = :schema ORDER BY table_name;"
    )
    res = sync_conn.execute(stmt, {"schema": schema})
    return [row[0] for row in res.fetchall()]


def run_verification() -> None:
    logger.info("Initializing isolated migration downgrade verification...")
    ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))

    sync_engine = create_engine(settings.sync_database_url)

    try:
        # Step 1: Clean test schema setup and baseline public schema inspection
        with sync_engine.connect() as conn:
            logger.info("Setting up clean disposable schema: %s", TEST_SCHEMA)
            conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE;"))
            conn.execute(text(f"CREATE SCHEMA {TEST_SCHEMA};"))
            conn.commit()

            public_tables_before = list_tables(conn, "public")
            logger.info(
                "Public schema baseline tables (%d): %s",
                len(public_tables_before),
                public_tables_before,
            )

        # Step 2: Run upgrade head in test schema
        with sync_engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {TEST_SCHEMA};"))
            conn.commit()

            logger.info("Executing Alembic upgrade head in %s...", TEST_SCHEMA)
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")
            conn.commit()

            test_tables_up = list_tables(conn, TEST_SCHEMA)
            logger.info(
                "Tables created in %s after upgrade (%d): %s",
                TEST_SCHEMA,
                len(test_tables_up),
                test_tables_up,
            )
            assert len(test_tables_up) >= 8, f"Expected at least 8 tables in {TEST_SCHEMA}"
            assert "alembic_version" in test_tables_up

        # Step 3: Run downgrade base in test schema
        with sync_engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {TEST_SCHEMA};"))
            conn.commit()

            logger.info("Executing Alembic downgrade base in %s...", TEST_SCHEMA)
            alembic_cfg.attributes["connection"] = conn
            command.downgrade(alembic_cfg, "base")
            conn.commit()

            test_tables_down = list_tables(conn, TEST_SCHEMA)
            logger.info(
                "Tables remaining in %s after downgrade (%d): %s",
                TEST_SCHEMA,
                len(test_tables_down),
                test_tables_down,
            )
            domain_tables = [t for t in test_tables_down if t != "alembic_version"]
            assert len(domain_tables) == 0, f"Expected 0 domain tables after downgrade, found: {domain_tables}"
            logger.info("All domain tables successfully dropped during downgrade!")

        # Step 4: Drop disposable schema and verify public schema was untouched
        with sync_engine.connect() as conn:
            logger.info("Dropping disposable schema: %s", TEST_SCHEMA)
            conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE;"))
            conn.commit()

            public_tables_after = list_tables(conn, "public")
            logger.info(
                "Public schema tables after test (%d): %s",
                len(public_tables_after),
                public_tables_after,
            )
            assert public_tables_before == public_tables_after, "Public schema was unexpectedly modified!"

        logger.info("Migration downgrade verification PASSED successfully.")

    finally:
        sync_engine.dispose()


if __name__ == "__main__":
    run_verification()
