r"""
Authentication and Role-Based Access Control Dependencies
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New

Enforces JWT extraction, signature and expiration verification, Redis revocation checks,
active user resolution, and role-based permissions.
"""

from typing import Any, Callable, Dict, Optional, Sequence
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.redis import is_token_revoked
from app.core.security import (
    InvalidTokenException,
    TokenExpiredException,
    decode_jwt_token,
)
from app.models.user import User

# HTTPBearer authorization extractor
security_scheme = HTTPBearer(auto_error=False)


async def get_current_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    Extracts and validates JWT Bearer credentials from Authorization header.
    Verifies signature, expiration, issuer, audience, and Redis revocation.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Expected Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = credentials.credentials

    try:
        payload = decode_jwt_token(raw_token)
    except TokenExpiredException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token expired\""},
        ) from exc
    except InvalidTokenException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc

    # Enforce access token type for API authorization
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for endpoint authorization.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check real-time revocation in Redis
    jti = payload.get("jti")
    if not jti or await is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked or invalidated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach raw token for downstream logout/revocation handler
    payload["_raw_token"] = raw_token
    return payload


async def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the authenticated User entity from database, eagerly loading assigned roles.
    Guarantees user account exists and is in ACTIVE status.
    """
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is not active (current status: {user.status}).",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Convenience alias ensuring active authenticated user."""
    return current_user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces that the authenticated user possesses at least one of the specified roles.
    """
    allowed_set = set(allowed_roles)

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        user_role_names = {r.name for r in user.roles}
        if not user_role_names.intersection(allowed_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Access requires one of the following roles: {sorted(list(allowed_set))}.",
            )
        return user

    return role_checker


# Canonical RBAC dependencies
require_admin = require_roles("ADMIN")
require_instructor = require_roles("INSTRUCTOR", "ADMIN")
require_student = require_roles("STUDENT", "INSTRUCTOR", "ADMIN")
