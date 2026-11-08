r"""
Automated Unit and Integration Tests for Judge0 Service & Internal Endpoint
Project: Vedantu Online Coding Assessment Platform
Workspace: E:\VedantuCodingPlatform_New
"""

import asyncio
import base64
import json
import pytest
import httpx
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.judge0_service import (
    Judge0AuthError,
    Judge0ConnectionError,
    Judge0Error,
    Judge0RateLimitError,
    Judge0Service,
    Judge0TimeoutError,
)


@pytest.fixture
def test_client():
    return TestClient(app)


# ------------------------------------------------------------------------------
# 1. Base64 and Serialization Tests
# ------------------------------------------------------------------------------
def test_judge0_base64_encoding_and_decoding():
    raw_code = 'print("Hello, Vedantu!")\n'
    encoded = Judge0Service._encode_b64(raw_code)
    assert encoded == base64.b64encode(raw_code.encode("utf-8")).decode("utf-8")

    decoded = Judge0Service._decode_b64(encoded)
    assert decoded == raw_code

    # None and empty handling
    assert Judge0Service._encode_b64(None) is None
    assert Judge0Service._decode_b64(None) is None
    assert Judge0Service._decode_b64("") is None


# ------------------------------------------------------------------------------
# 2. Client Mocking Tests (Python, Java, Limits, Errors)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_judge0_python_clean_execution():
    """Test successful Python execution lifecycle with Base64 encoding/decoding."""
    token = "test-token-python-123"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "submissions" in str(request.url):
            return httpx.Response(201, json={"token": token})
        elif request.method == "GET" and f"submissions/{token}" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "status": {"id": 3, "description": "Accepted"},
                    "stdout": base64.b64encode(b"Vedantu Output\n").decode("utf-8"),
                    "stderr": None,
                    "compile_output": None,
                    "time": "0.045",
                    "memory": 12400,
                    "language_id": 71,
                },
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handler)
    service = Judge0Service(base_url="http://mock-judge0:2358", auth_token="test-token")

    async with httpx.AsyncClient(transport=mock_transport) as client:
        # 1. Create submission
        ret_token = await service.create_submission(
            source_code='print("Vedantu Output")',
            language_id=71,
            client=client,
        )
        assert ret_token == token

        # 2. Get submission
        result = await service.get_submission(token=ret_token, client=client)
        assert result.is_completed is True
        assert result.is_passed is True
        assert result.status.id == 3
        assert result.status.description == "Accepted"
        assert result.stdout == "Vedantu Output\n"
        assert result.time == 0.045
        assert result.memory == 12400


@pytest.mark.anyio
async def test_judge0_java_clean_execution():
    """Test successful Java execution lifecycle with stdin input."""
    token = "test-token-java-456"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "submissions" in str(request.url):
            return httpx.Response(201, json={"token": token})
        elif request.method == "GET" and f"submissions/{token}" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "status": {"id": 3, "description": "Accepted"},
                    "stdout": base64.b64encode(b"Java Double: 42\n").decode("utf-8"),
                    "stderr": None,
                    "compile_output": None,
                    "time": "0.150",
                    "memory": 38400,
                    "language_id": 62,
                },
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handler)
    service = Judge0Service(base_url="http://mock-judge0:2358", auth_token="test-token")

    async with httpx.AsyncClient(transport=mock_transport) as client:
        result = await service.get_submission(token=token, client=client)
        assert result.is_completed is True
        assert result.is_passed is True
        assert result.status.id == 3
        assert result.stdout == "Java Double: 42\n"
        assert result.language_id == 62


@pytest.mark.anyio
async def test_judge0_compilation_error():
    """Test compilation error mapping (Status 6)."""
    token = "test-token-compile-err"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": {"id": 6, "description": "Compilation Error"},
                "stdout": None,
                "stderr": None,
                "compile_output": base64.b64encode(b"Main.java:2: error: ';' expected").decode("utf-8"),
                "time": None,
                "memory": None,
                "language_id": 62,
            },
        )

    mock_transport = httpx.MockTransport(handler)
    service = Judge0Service(base_url="http://mock-judge0:2358", auth_token="test-token")

    async with httpx.AsyncClient(transport=mock_transport) as client:
        result = await service.get_submission(token=token, client=client)
        assert result.is_completed is True
        assert result.is_passed is False
        assert result.status.id == 6
        assert result.status.description == "Compilation Error"
        assert "Main.java:2: error: ';' expected" in (result.compile_output or "")


@pytest.mark.anyio
async def test_judge0_runtime_error():
    """Test runtime exception mapping (Status 11)."""
    token = "test-token-runtime-err"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": {"id": 11, "description": "Runtime Error (NZEC)"},
                "stdout": None,
                "stderr": base64.b64encode(b"ZeroDivisionError: division by zero").decode("utf-8"),
                "compile_output": None,
                "time": "0.020",
                "memory": 11000,
                "language_id": 71,
            },
        )

    mock_transport = httpx.MockTransport(handler)
    service = Judge0Service(base_url="http://mock-judge0:2358", auth_token="test-token")

    async with httpx.AsyncClient(transport=mock_transport) as client:
        result = await service.get_submission(token=token, client=client)
        assert result.is_completed is True
        assert result.is_passed is False
        assert result.status.id == 11
        assert "ZeroDivisionError" in (result.stderr or "")


@pytest.mark.anyio
async def test_judge0_time_limit_exceeded():
    """Test TLE mapping (Status 5)."""
    token = "test-token-tle"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": {"id": 5, "description": "Time Limit Exceeded"},
                "stdout": None,
                "stderr": None,
                "compile_output": None,
                "time": "2.005",
                "memory": 13000,
                "language_id": 71,
            },
        )

    mock_transport = httpx.MockTransport(handler)
    service = Judge0Service(base_url="http://mock-judge0:2358", auth_token="test-token")

    async with httpx.AsyncClient(transport=mock_transport) as client:
        result = await service.get_submission(token=token, client=client)
        assert result.is_completed is True
        assert result.is_passed is False
        assert result.status.id == 5
        assert result.status.description == "Time Limit Exceeded"


@pytest.mark.anyio
async def test_judge0_auth_failure_rejection():
    """Test rejection when Judge0 returns HTTP 401."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized"})

    mock_transport = httpx.MockTransport(handler)
    service = Judge0Service(base_url="http://mock-judge0:2358", auth_token="invalid-token")

    async with httpx.AsyncClient(transport=mock_transport) as client:
        with pytest.raises(Judge0AuthError):
            await service.create_submission(source_code="print(1)", language_id=71, client=client)


# ------------------------------------------------------------------------------
# 3. Protected Internal API Route Tests
# ------------------------------------------------------------------------------
def test_internal_endpoint_missing_secret_rejected(test_client):
    """Confirm HTTP 403 when X-Internal-Secret is omitted."""
    payload = {
        "source_code": "print(1)",
        "language": "python",
    }
    resp = test_client.post("/api/v1/internal/judge0/execute", json=payload)
    assert resp.status_code == 403
    assert "Invalid or missing X-Internal-Secret" in resp.json()["detail"]


def test_internal_endpoint_invalid_secret_rejected(test_client):
    """Confirm HTTP 403 when X-Internal-Secret is incorrect."""
    payload = {
        "source_code": "print(1)",
        "language": "python",
    }
    resp = test_client.post(
        "/api/v1/internal/judge0/execute",
        json=payload,
        headers={"X-Internal-Secret": "wrong-secret-value"},
    )
    assert resp.status_code == 403
    assert "Invalid or missing X-Internal-Secret" in resp.json()["detail"]


def test_internal_endpoint_source_length_clamp(test_client):
    """Confirm validation error when source code exceeds 10,000 chars."""
    payload = {
        "source_code": "a" * 10001,
        "language": "python",
    }
    resp = test_client.post(
        "/api/v1/internal/judge0/execute",
        json=payload,
        headers={"X-Internal-Secret": settings.INTERNAL_DEV_SECRET or "dev-secret"},
    )
    # Pydantic validation rejects string length > 10,000 with 422
    assert resp.status_code == 422


def test_internal_endpoint_cpu_limit_clamp(test_client):
    """Confirm validation error when requested CPU time exceeds 5.0 seconds."""
    payload = {
        "source_code": "print(1)",
        "language": "python",
        "cpu_time_limit": 10.0,
    }
    resp = test_client.post(
        "/api/v1/internal/judge0/execute",
        json=payload,
        headers={"X-Internal-Secret": settings.INTERNAL_DEV_SECRET or "dev-secret"},
    )
    assert resp.status_code == 422


def test_languages_endpoint_protection(test_client):
    """Confirm GET /languages requires internal secret."""
    resp = test_client.get("/api/v1/internal/judge0/languages")
    assert resp.status_code == 403