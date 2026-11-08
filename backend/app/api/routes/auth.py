r"""
Authentication and User Management Routes
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New

Exposes registration, credential authentication, token refresh, revocation/logout,
user profile introspection, and RBAC-governed endpoints.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_token_payload,
    get_current_user,
    get_db,
    require_admin,
    require_instructor,
    require_student,
)
from app.core.redis import (
    is_token_revoked,
    revoke_refresh_token,
    revoke_token,
    track_refresh_token,
)
from app.core.security import (
    InvalidTokenException,
    TokenExpiredException,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.auth import (
    LogoutRequest,
    MessageResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Student Account",
    description=(
        "Public self-registration for candidates. Assigns the STUDENT role exclusively. "
        "Attempts to request or self-assign ADMIN or INSTRUCTOR roles are strictly rejected."
    ),
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Validate password strength
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    normalized_email = payload.email.lower().strip()

    # 2. Check for duplicate email
    stmt = select(User).where(User.email == normalized_email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # 3. Retrieve default STUDENT role
    stmt_role = select(Role).where(Role.name == "STUDENT")
    student_role = (await db.execute(stmt_role)).scalar_one_or_none()
    if student_role is None:
        # Fallback creation if not yet seeded
        student_role = Role(
            name="STUDENT",
            description="Candidate participating in coding assessments.",
        )
        db.add(student_role)
        await db.flush()

    # 4. Create new user with Argon2 password hash
    new_user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
        status="ACTIVE",
    )
    db.add(new_user)
    await db.flush()

    # 5. Assign STUDENT role
    user_role = UserRole(user_id=new_user.id, role_id=student_role.id)
    db.add(user_role)
    await db.commit()

    # 6. Eagerly reload user with roles
    stmt_reload = select(User).options(selectinload(User.roles)).where(User.id == new_user.id)
    created_user = (await db.execute(stmt_reload)).scalar_one()

    roles = [r.name for r in created_user.roles]

    # 7. Issue JWT token pair
    access_token, a_jti, a_exp = create_access_token(
        subject=str(created_user.id),
        roles=roles,
        extra_claims={"email": created_user.email},
    )
    refresh_token, r_jti, r_exp = create_refresh_token(subject=str(created_user.id))

    # Track refresh token in Redis
    await track_refresh_token(str(created_user.id), r_jti, r_exp)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=a_exp,
        user=UserResponse(
            id=created_user.id,
            full_name=created_user.full_name,
            email=created_user.email,
            status=created_user.status,
            roles=roles,
            created_at=created_user.created_at,
        ),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates candidate, instructor, or administrator with email and password.",
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    normalized_email = payload.email.lower().strip()

    stmt = select(User).options(selectinload(User.roles)).where(User.email == normalized_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Constant-time / generic credential verification (prevents email enumeration)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended. Please contact administrator.",
        )

    roles = [r.name for r in user.roles]

    # Generate JWT token pair
    access_token, a_jti, a_exp = create_access_token(
        subject=str(user.id),
        roles=roles,
        extra_claims={"email": user.email},
    )
    refresh_token, r_jti, r_exp = create_refresh_token(subject=str(user.id))

    # Track active refresh token in Redis
    await track_refresh_token(str(user.id), r_jti, r_exp)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=a_exp,
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            status=user.status,
            roles=roles,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Rotates refresh token and issues a new access token.",
)
async def refresh_tokens(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenRefreshResponse:
    # 1. Decode and validate incoming refresh token
    try:
        decoded = decode_jwt_token(payload.refresh_token)
    except TokenExpiredException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc
    except InvalidTokenException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for refresh endpoint.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    old_jti = decoded.get("jti")
    if not old_jti or await is_token_revoked(old_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or invalidated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Query user to verify active status and roles
    try:
        user_uuid = uuid.UUID(decoded["sub"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject in refresh token.",
        ) from exc

    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is None or user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer active.",
        )

    # 3. Revoke previous refresh token (enforce refresh token rotation)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    remaining_ttl = max(decoded.get("exp", now_ts + 3600) - now_ts, 1)
    await revoke_refresh_token(str(user.id), old_jti, ttl_seconds=remaining_ttl)

    # 4. Issue new token pair
    roles = [r.name for r in user.roles]
    new_access_token, a_jti, a_exp = create_access_token(
        subject=str(user.id),
        roles=roles,
        extra_claims={"email": user.email},
    )
    new_refresh_token, r_jti, r_exp = create_refresh_token(subject=str(user.id))

    await track_refresh_token(str(user.id), r_jti, r_exp)

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=a_exp,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Revokes active access token and optional refresh token in Redis.",
)
async def logout(
    logout_payload: Optional[LogoutRequest] = None,
    token_payload: dict = Depends(get_current_token_payload),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    # 1. Invalidate current access token
    jti = token_payload.get("jti")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    remaining_ttl = max(token_payload.get("exp", now_ts + 60) - now_ts, 1)

    if jti:
        await revoke_token(jti, remaining_ttl)

    # 2. Invalidate refresh token if provided
    if logout_payload and logout_payload.refresh_token:
        try:
            r_decoded = decode_jwt_token(logout_payload.refresh_token)
            r_jti = r_decoded.get("jti")
            if r_jti:
                r_ttl = max(r_decoded.get("exp", now_ts + 3600) - now_ts, 1)
                await revoke_refresh_token(str(current_user.id), r_jti, ttl_seconds=r_ttl)
        except Exception:
            pass

    return MessageResponse(
        message="Successfully logged out and invalidated session.",
        detail="Token has been blacklisted in session store.",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns public profile and role assignments for the authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        status=current_user.status,
        roles=[r.name for r in current_user.roles],
        created_at=current_user.created_at,
    )


# ------------------------------------------------------------------------------
# Role-Protected Demonstration & Verification Endpoints (RBAC Validation)
# ------------------------------------------------------------------------------

@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin User Directory (ADMIN Role Required)",
    description="Lists all users in the system. Accessible exclusively by administrators.",
)
async def list_users_admin(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    stmt = select(User).options(selectinload(User.roles)).order_by(User.created_at.desc())
    users = (await db.execute(stmt)).scalars().all()
    return [
        UserResponse(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            status=u.status,
            roles=[r.name for r in u.roles],
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get(
    "/instructor/dashboard",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Instructor Assessment Portal (INSTRUCTOR or ADMIN Required)",
    description="Instructor workspace endpoint protected by role check.",
)
async def instructor_dashboard(
    instructor_user: User = Depends(require_instructor),
) -> MessageResponse:
    return MessageResponse(
        message=f"Welcome to the Instructor Evaluation Portal, {instructor_user.full_name}.",
        detail=f"Authorized under roles: {[r.name for r in instructor_user.roles]}",
    )


@router.get(
    "/student/profile",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Student Profile Workspace (STUDENT, INSTRUCTOR, or ADMIN)",
    description="Candidate workspace endpoint accessible to enrolled students.",
)
async def student_profile(
    student_user: User = Depends(require_student),
) -> MessageResponse:
    return MessageResponse(
        message=f"Candidate workspace active for {student_user.full_name}.",
        detail=f"Assigned roles: {[r.name for r in student_user.roles]}",
    )
