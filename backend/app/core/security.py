r"""
Security and Cryptographic Services
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New

Provides Argon2 password hashing and verification, password strength auditing,
and RFC 7519 compliant JSON Web Token (JWT) issuance and verification.
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import jwt

from app.core.config import settings

# Initialize Argon2id password hasher with secure parameters (OWASP recommended)
_password_hasher = PasswordHasher(
    time_cost=3,        # 3 iterations
    memory_cost=65536,  # 64 MiB RAM
    parallelism=4,      # 4 lanes / threads
    hash_len=32,
    salt_len=16,
)

# Password policy pattern: min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
_PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


class SecurityException(Exception):
    """Base exception for authentication and token validation failures."""
    pass


class TokenExpiredException(SecurityException):
    """Raised when an inspected JWT has passed its expiration time."""
    pass


class InvalidTokenException(SecurityException):
    """Raised when a JWT signature, issuer, audience, or payload format is invalid."""
    pass


def hash_password(password: str) -> str:
    """Computes an Argon2id hash of a plaintext password."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against an Argon2 hash.
    Returns True if matches, False otherwise. Never throws.
    """
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False


def validate_password_strength(password: str) -> None:
    """
    Validates candidate password against enterprise security policy:
    - Minimum 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters.")
    if not _PASSWORD_REGEX.match(password):
        raise ValueError(
            "Password must contain at least one uppercase letter, "
            "one lowercase letter, one number, and one special character."
        )


def create_access_token(
    subject: str,
    roles: List[str],
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, int]:
    """
    Generates a short-lived signed JWT access token.
    Returns tuple: (token_str, jti, expires_in_seconds)
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=expires_delta,
        roles=roles,
        extra_claims=extra_claims,
    )


def create_refresh_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, int]:
    """
    Generates a longer-lived signed JWT refresh token.
    Returns tuple: (token_str, jti, expires_in_seconds)
    """
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=expires_delta,
        roles=None,
        extra_claims=extra_claims,
    )


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    roles: Optional[List[str]] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, int]:
    now = datetime.now(timezone.utc)
    exp = now + expires_delta
    jti = uuid.uuid4().hex

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "jti": jti,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    if roles is not None:
        payload["roles"] = roles

    if extra_claims:
        for k, v in extra_claims.items():
            if k not in payload:
                payload[k] = v

    token_str = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    expires_in_seconds = int(expires_delta.total_seconds())
    return token_str, jti, expires_in_seconds


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a signed JWT token against signature, expiration,
    issuer, and audience.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": ["exp", "iat", "sub", "jti", "iss", "aud"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredException("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenException("Invalid token signature or claims.") from exc
