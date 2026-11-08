r"""
Asynchronous Database Connection and Session Architecture
Project: Vedantu Online Coding Assessment Platform (Stage 2.6)
Workspace: E:\VedantuCodingPlatform_New
"""

import asyncio
import logging
import sys
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# On Windows platforms, psycopg async mode requires WindowsSelectorEventLoopPolicy
if sys.platform == "win32":
    try:
        current_policy = asyncio.get_event_loop_policy()
        if not isinstance(current_policy, asyncio.WindowsSelectorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        logger.warning("Could not set WindowsSelectorEventLoopPolicy: %s", e)

# ------------------------------------------------------------------------------
# Async Database Engine Factory
# ------------------------------------------------------------------------------
def create_engine_instance() -> AsyncEngine:
    """Create and configure the SQLAlchemy async engine with connection pooling."""
    return create_async_engine(
        settings.async_database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DB_ECHO,
    )


async_engine = create_engine_instance()

# ------------------------------------------------------------------------------
# Async Session Factory
# ------------------------------------------------------------------------------
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ------------------------------------------------------------------------------
# FastAPI Database Session Dependency
# ------------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an asynchronous SQLAlchemy database session.
    Automatically commits transactions upon successful request completion,
    rolls back on unhandled exceptions, and safely releases the session back
    to the connection pool.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ------------------------------------------------------------------------------
# Lifecycle & Diagnostic Helpers
# ------------------------------------------------------------------------------
async def check_database_connection() -> bool:
    """
    Diagnostic helper to test PostgreSQL database connectivity.
    Returns True if a 'SELECT 1' query succeeds, False otherwise.
    """
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1;"))
            return result.scalar() == 1
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error during database health check: %s", exc)
        return False


async def dispose_database_engine() -> None:
    """Gracefully dispose all active connections in the connection pool."""
    await async_engine.dispose()
