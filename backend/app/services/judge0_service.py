r"""
Judge0 Community Edition v1.13.1 Client Service
Project: Vedantu Online Coding Assessment Platform
Workspace: E:\VedantuCodingPlatform_New
"""

import asyncio
import base64
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------
class Judge0Error(Exception):
    """Base exception for all Judge0 service errors."""
    pass


class Judge0ConnectionError(Judge0Error):
    """Raised when Judge0 API cannot be reached."""
    pass


class Judge0TimeoutError(Judge0Error):
    """Raised when submission polling exceeds the timeout limit."""
    pass


class Judge0AuthError(Judge0Error):
    """Raised when authentication with Judge0 fails (HTTP 401/403)."""
    pass


class Judge0RateLimitError(Judge0Error):
    """Raised when Judge0 returns HTTP 429 Too Many Requests."""
    pass


# ------------------------------------------------------------------------------
# Domain Models
# ------------------------------------------------------------------------------
class Judge0SubmissionStatus(BaseModel):
    id: int
    description: str


class ExecutionResult(BaseModel):
    token: str
    status: Judge0SubmissionStatus
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    time: Optional[float] = None
    memory: Optional[int] = None
    language_id: int
    is_completed: bool = False
    is_passed: bool = False


class LanguageInfo(BaseModel):
    id: int
    name: str


# ------------------------------------------------------------------------------
# Client Implementation
# ------------------------------------------------------------------------------
class Judge0Service:
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_header: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.JUDGE0_URL).rstrip("/")
        self.auth_header = auth_header or settings.JUDGE0_AUTHN_HEADER
        self.auth_token = auth_token or settings.JUDGE0_AUTHN_TOKEN
        self.timeout = timeout or settings.JUDGE0_TIMEOUT_SECONDS
        self._cached_languages: Optional[List[Dict[str, Any]]] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.auth_token:
            headers[self.auth_header] = self.auth_token
        return headers

    @staticmethod
    def _encode_b64(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return base64.b64encode(value.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _decode_b64(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return base64.b64decode(value.encode("utf-8")).decode("utf-8", errors="replace")
        except Exception:
            return value

    async def get_system_info(self, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
        """Fetch system info to verify Judge0 connectivity and authentication."""
        url = f"{self.base_url}/system_info"
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close = True

        try:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 401:
                raise Judge0AuthError("Unauthorized: Judge0 rejected authentication token.")
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError as e:
            raise Judge0ConnectionError(f"Could not connect to Judge0 at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise Judge0TimeoutError(f"Connection to Judge0 timed out after {self.timeout}s") from e
        finally:
            if should_close:
                await client.aclose()

    async def get_languages(self, client: Optional[httpx.AsyncClient] = None) -> List[LanguageInfo]:
        """Fetch all supported programming languages from Judge0."""
        if self._cached_languages is not None:
            return [LanguageInfo(**item) for item in self._cached_languages]

        url = f"{self.base_url}/languages"
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close = True

        try:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 401:
                raise Judge0AuthError("Unauthorized: Judge0 rejected authentication token.")
            resp.raise_for_status()
            languages_data = resp.json()
            self._cached_languages = languages_data
            return [LanguageInfo(**item) for item in languages_data]
        except httpx.ConnectError as e:
            raise Judge0ConnectionError(f"Could not connect to Judge0 at {self.base_url}") from e
        finally:
            if should_close:
                await client.aclose()

    async def discover_language_id(self, language_name: str, client: Optional[httpx.AsyncClient] = None) -> int:
        """
        Dynamically discover language ID by matching language name (e.g., 'python' or 'java').
        Falls back to known official Judge0 CE v1.13.1 IDs if discovery is unreachable.
        """
        fallbacks = {
            "python": 71,  # Python 3.8.1
            "python3": 71,
            "java": 62,    # Java OpenJDK 13.0.1
        }

        try:
            languages = await self.get_languages(client=client)
            target = language_name.lower().strip()
            # If target is python, prefer Python 3 over Python 2
            if target in ("python", "python3"):
                for lang in languages:
                    if "python (3" in lang.name.lower():
                        return lang.id
            for lang in languages:
                lname = lang.name.lower()
                if target in lname:
                    return lang.id
        except Exception:
            pass

        key = language_name.lower().strip()
        if key in fallbacks:
            return fallbacks[key]
        raise Judge0Error(f"Unsupported programming language: '{language_name}'")

    async def create_submission(
        self,
        source_code: str,
        language_id: int,
        stdin: Optional[str] = None,
        expected_output: Optional[str] = None,
        cpu_time_limit: float = 2.0,
        memory_limit: int = 128000,
        client: Optional[httpx.AsyncClient] = None,
    ) -> str:
        """
        Create a new submission in Judge0.
        Uses Base64 encoding for source code, stdin, and expected output.
        """
        url = f"{self.base_url}/submissions?base64_encoded=true&wait=false"
        # Java 13 64-bit JVM requires 3 GB virtual address space (RLIMIT_AS) for VM initialization
        if language_id == 62:
            effective_mem = max(memory_limit, 3000000)
        else:
            effective_mem = memory_limit

        payload = {
            "source_code": self._encode_b64(source_code),
            "language_id": language_id,
            "stdin": self._encode_b64(stdin) if stdin else None,
            "expected_output": self._encode_b64(expected_output) if expected_output else None,
            "cpu_time_limit": min(cpu_time_limit, 5.0),
            "memory_limit": effective_mem,
            "enable_per_process_and_thread_time_limit": True,
            "enable_per_process_and_thread_memory_limit": True,
        }
        # Filter None values
        payload = {k: v for k, v in payload.items() if v is not None}

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close = True

        try:
            resp = await client.post(url, headers=self._get_headers(), json=payload)
            if resp.status_code == 401:
                raise Judge0AuthError("Unauthorized: Judge0 rejected authentication token.")
            if resp.status_code == 429:
                raise Judge0RateLimitError("Judge0 submission queue is full (HTTP 429).")
            resp.raise_for_status()
            data = resp.json()
            token = data.get("token")
            if not token:
                raise Judge0Error(f"Judge0 response missing submission token: {data}")
            return token
        except httpx.ConnectError as e:
            raise Judge0ConnectionError(f"Could not connect to Judge0 at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise Judge0TimeoutError("Judge0 create_submission request timed out.") from e
        finally:
            if should_close:
                await client.aclose()

    async def get_submission(
        self,
        token: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> ExecutionResult:
        """Fetch submission status and execution output by token."""
        url = f"{self.base_url}/submissions/{token}?base64_encoded=true"

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close = True

        try:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 401:
                raise Judge0AuthError("Unauthorized: Judge0 rejected authentication token.")
            resp.raise_for_status()
            data = resp.json()

            status_dict = data.get("status", {})
            status_id = status_dict.get("id", 1)
            status_desc = status_dict.get("description", "In Queue")

            # Completed if status_id >= 3 (Accepted, Wrong Answer, TLE, Error, etc.)
            is_completed = status_id >= 3
            is_passed = status_id == 3

            time_val = None
            if data.get("time") is not None:
                try:
                    time_val = float(data["time"])
                except (ValueError, TypeError):
                    pass

            return ExecutionResult(
                token=token,
                status=Judge0SubmissionStatus(id=status_id, description=status_desc),
                stdout=self._decode_b64(data.get("stdout")),
                stderr=self._decode_b64(data.get("stderr")),
                compile_output=self._decode_b64(data.get("compile_output")),
                message=self._decode_b64(data.get("message")),
                time=time_val,
                memory=data.get("memory"),
                language_id=data.get("language_id", 0),
                is_completed=is_completed,
                is_passed=is_passed,
            )
        except httpx.ConnectError as e:
            raise Judge0ConnectionError(f"Could not connect to Judge0 at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise Judge0TimeoutError("Judge0 get_submission request timed out.") from e
        finally:
            if should_close:
                await client.aclose()

    async def execute_and_wait(
        self,
        source_code: str,
        language_id: int,
        stdin: Optional[str] = None,
        expected_output: Optional[str] = None,
        cpu_time_limit: float = 2.0,
        memory_limit: int = 128000,
        max_poll_seconds: float = 10.0,
        poll_interval: float = 0.5,
    ) -> ExecutionResult:
        """
        Complete submission lifecycle:
        1. Submits code asynchronously to Judge0.
        2. Polls Judge0 until status is completed or max_poll_seconds elapsed.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            token = await self.create_submission(
                source_code=source_code,
                language_id=language_id,
                stdin=stdin,
                expected_output=expected_output,
                cpu_time_limit=cpu_time_limit,
                memory_limit=memory_limit,
                client=client,
            )

            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < max_poll_seconds:
                result = await self.get_submission(token=token, client=client)
                if result.is_completed:
                    return result
                await asyncio.sleep(poll_interval)

            # Polling timed out before execution completed
            raise Judge0TimeoutError(
                f"Submission {token} did not complete within {max_poll_seconds} seconds."
            )


# Default singleton service instance
judge0_service = Judge0Service()