r"""
Protected Internal Judge0 Execution Route (Development Mode Only)
Project: Vedantu Online Coding Assessment Platform
Workspace: E:\VedantuCodingPlatform_New
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.judge0_service import (
    Judge0AuthError,
    Judge0ConnectionError,
    Judge0Error,
    Judge0RateLimitError,
    Judge0TimeoutError,
    judge0_service,
)

router = APIRouter(prefix="/internal/judge0", tags=["Internal Judge0 (Dev Only)"])

# Concurrency Admission Limiter: Max 3 concurrent in-flight executions
CONCURRENCY_LIMIT = 3
_execution_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# Request Size Limit: 32 KB
MAX_BODY_BYTES = 32 * 1024


class DevExecutionRequest(BaseModel):
    source_code: str = Field(..., max_length=10000, description="Source code (max 10,000 chars)")
    language_id: Optional[int] = Field(None, description="Judge0 Language ID")
    language: Optional[str] = Field("python", description="Language name ('python' or 'java')")
    stdin: Optional[str] = Field(None, max_length=5000, description="Standard input (max 5,000 chars)")
    expected_output: Optional[str] = Field(None, max_length=5000, description="Expected stdout for matching")
    cpu_time_limit: Optional[float] = Field(2.0, ge=0.5, le=5.0, description="CPU time limit in seconds (0.5 - 5.0s)")
    memory_limit: Optional[int] = Field(128000, ge=16000, le=256000, description="Memory limit in KB (16MB - 256MB)")


class DevExecutionResponse(BaseModel):
    status: str
    status_id: int
    is_passed: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    time_seconds: Optional[float] = None
    memory_kb: Optional[int] = None
    language_id: int
    token: str


def _verify_internal_secret(x_internal_secret: Optional[str] = Header(None)) -> None:
    """Enforce internal security secret for development execution."""
    if not settings.INTERNAL_DEV_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal execution disabled: INTERNAL_DEV_SECRET not configured.",
        )
    if not x_internal_secret or x_internal_secret != settings.INTERNAL_DEV_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing X-Internal-Secret header.",
        )


@router.post(
    "/execute",
    response_model=DevExecutionResponse,
    summary="Internal Code Execution (Development Only)",
    description="Executes Python 3 or Java code in sandboxed Judge0 CE with admission limiting and size clamps.",
)
async def execute_code_internal(
    payload: DevExecutionRequest,
    request: Request,
    x_internal_secret: Optional[str] = Header(None),
):
    # 1. Environment Gate
    if settings.ENVIRONMENT != "development" or not settings.ENABLE_DEV_JUDGE0_ROUTES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in this environment.",
        )

    # 2. Secret Verification
    _verify_internal_secret(x_internal_secret)

    # 3. Payload Body Size Clamp (Max 32 KB)
    body_bytes = await request.body()
    if len(body_bytes) > MAX_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body exceeds maximum size of {MAX_BODY_BYTES // 1024} KB.",
        )

    # 4. Resolve Language ID
    lang_id = payload.language_id
    if not lang_id:
        lang_id = await judge0_service.discover_language_id(payload.language or "python")

    # 5. Non-blocking Concurrency Check (Returns 429 if capacity exhausted)
    if _execution_semaphore.locked():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Execution capacity exhausted: Maximum concurrent executions in progress. Please retry.",
        )

    # 6. Execute inside Semaphore
    try:
        async with _execution_semaphore:
            result = await judge0_service.execute_and_wait(
                source_code=payload.source_code,
                language_id=lang_id,
                stdin=payload.stdin,
                expected_output=payload.expected_output,
                cpu_time_limit=payload.cpu_time_limit or 2.0,
                memory_limit=payload.memory_limit or 128000,
                max_poll_seconds=10.0,
                poll_interval=0.4,
            )

            return DevExecutionResponse(
                status=result.status.description,
                status_id=result.status.id,
                is_passed=result.is_passed,
                stdout=result.stdout,
                stderr=result.stderr,
                compile_output=result.compile_output,
                time_seconds=result.time,
                memory_kb=result.memory,
                language_id=result.language_id or lang_id,
                token=result.token,
            )
    except Judge0TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Execution timed out while waiting for Judge0 worker response.",
        ) from e
    except Judge0RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Judge0 submission queue is full. Try again shortly.",
        ) from e
    except (Judge0ConnectionError, Judge0AuthError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Execution engine communication failure.",
        ) from e
    except Judge0Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal execution error.",
        ) from e


@router.get(
    "/languages",
    summary="Get Supported Languages",
    description="Returns available language runtimes from Judge0 CE.",
)
async def get_supported_languages(
    x_internal_secret: Optional[str] = Header(None),
):
    if settings.ENVIRONMENT != "development" or not settings.ENABLE_DEV_JUDGE0_ROUTES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in this environment.",
        )
    _verify_internal_secret(x_internal_secret)

    try:
        languages = await judge0_service.get_languages()
        return [{"id": l.id, "name": l.name} for l in languages]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve language registry from Judge0.",
        ) from e