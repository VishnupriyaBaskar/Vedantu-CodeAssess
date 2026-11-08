r"""
Authentication and RBAC Test Suite
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New

Comprehensive test suite verifying student registration, login, token refresh,
Redis-backed token revocation/logout, generic credential failure responses,
JWT signature and expiration auditing, and multi-tier role-based authorization.
"""

from datetime import timedelta
import sys
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_password_strength,
)
from app.main import app
from app.models.role import Role, UserRole
from app.models.user import User


async def create_test_user_with_role(
    role_name: str,
    email: str = None,
    password: str = "SecureTestPassword123!",
    status_val: str = "ACTIVE",
) -> tuple[User, str]:
    """Helper fixture to insert an active test user with a specific role."""
    suffix = uuid.uuid4().hex[:8]
    user_email = email or f"{role_name.lower()}_{suffix}@vedantu-test.com"

    async with async_session_factory() as session:
        async with session.begin():
            # Check or create role
            stmt_role = select(Role).where(Role.name == role_name)
            role = (await session.execute(stmt_role)).scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=f"Test role {role_name}")
                session.add(role)
                await session.flush()

            # Create user
            user = User(
                full_name=f"Test {role_name.capitalize()} User",
                email=user_email,
                password_hash=hash_password(password),
                status=status_val,
            )
            session.add(user)
            await session.flush()

            # Assign role
            user_role = UserRole(user_id=user.id, role_id=role.id)
            session.add(user_role)

        stmt_load = select(User).options(selectinload(User.roles)).where(User.id == user.id)
        user_loaded = (await session.execute(stmt_load)).scalar_one()
        return user_loaded, password


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ------------------------------------------------------------------------------
# 1. Student Registration & Privilege Escalation Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_student_registration_success():
    """Verify clean student self-registration returns token pair and STUDENT role."""
    transport = ASGITransport(app=app)
    suffix = uuid.uuid4().hex[:8]
    email = f"student_reg_{suffix}@vedantu-test.com"
    password = "ValidStudentPass123!"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "full_name": "Rohan Sharma",
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["roles"] == ["STUDENT"]
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]


@pytest.mark.anyio
async def test_student_registration_rejects_duplicate_email():
    """Verify duplicate registration fails with HTTP 409 Conflict."""
    transport = ASGITransport(app=app)
    user, pwd = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "full_name": "Duplicate User",
                "email": user.email,
                "password": "ValidPassword123!",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_student_registration_weak_password_rejected():
    """Verify password policy rejects weak passwords (length, missing special chars)."""
    transport = ASGITransport(app=app)
    weak_passwords = ["short1!", "nouppercase123!", "NOLOWERCASE123!", "NoSpecialChar123", ""]

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for wp in weak_passwords:
            response = await ac.post(
                f"{settings.API_V1_STR}/auth/register",
                json={
                    "full_name": "Weak Pass User",
                    "email": f"weak_{uuid.uuid4().hex[:6]}@vedantu.com",
                    "password": wp,
                },
            )
            assert response.status_code == 422


@pytest.mark.anyio
async def test_registration_prevents_privilege_escalation():
    """
    Verify public registration rejects any attempt to specify roles (e.g. role='ADMIN').
    Pydantic config extra='forbid' must reject unexpected privilege assignment fields.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "full_name": "Attacker Trying Admin",
                "email": f"hacker_{uuid.uuid4().hex[:6]}@vedantu.com",
                "password": "SecurePassword123!",
                "role": "ADMIN",
            },
        )
        assert response.status_code == 422


# ------------------------------------------------------------------------------
# 2. Login & Credential Verification Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_login_valid_credentials():
    """Verify valid login returns access and refresh tokens, user metadata, and expires_in."""
    transport = ASGITransport(app=app)
    user, password = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == user.email
        assert "password_hash" not in data["user"]


@pytest.mark.anyio
async def test_login_invalid_password_returns_generic_error():
    """Verify incorrect password returns HTTP 401 with generic error message."""
    transport = ASGITransport(app=app)
    user, _ = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user.email, "password": "WrongPassword123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.anyio
async def test_login_unknown_email_returns_generic_error():
    """Verify non-existent email returns same generic HTTP 401 message (no email enumeration)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": f"nonexistent_{uuid.uuid4().hex[:8]}@vedantu.com", "password": "AnyPassword123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.anyio
async def test_login_inactive_user_rejected():
    """Verify inactive/suspended accounts are forbidden from logging in."""
    transport = ASGITransport(app=app)
    user, password = await create_test_user_with_role("STUDENT", status_val="SUSPENDED")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()


# ------------------------------------------------------------------------------
# 3. Token Verification, Introspection & Expired/Invalid JWT Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_current_user_profile():
    """Verify GET /auth/me returns authenticated user's profile with assigned roles."""
    transport = ASGITransport(app=app)
    user, password = await create_test_user_with_role("INSTRUCTOR")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user.email, "password": password},
        )
        token = login_res.json()["access_token"]

        response = await ac.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert "INSTRUCTOR" in data["roles"]
        assert "password_hash" not in data


@pytest.mark.anyio
async def test_unauthenticated_request_rejected():
    """Verify requests lacking Bearer token receive HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"{settings.API_V1_STR}/auth/me")
        assert response.status_code == 401
        assert "credentials were not provided" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_expired_jwt_rejected():
    """Verify expired JWT tokens are rejected with HTTP 401."""
    transport = ASGITransport(app=app)
    user, _ = await create_test_user_with_role("STUDENT")

    # Manually issue expired token (-5 minutes)
    expired_token, _, _ = create_access_token(
        subject=str(user.id),
        roles=["STUDENT"],
        extra_claims={"email": user.email},
    )
    # Tamper payload with expired exp
    import jwt
    payload = jwt.decode(expired_token, options={"verify_signature": False})
    payload["exp"] = payload["iat"] - 300  # 5 minutes in past
    tampered_expired = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {tampered_expired}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_invalid_signature_jwt_rejected():
    """Verify JWT signed with wrong secret key is rejected with HTTP 401."""
    transport = ASGITransport(app=app)
    user, _ = await create_test_user_with_role("STUDENT")

    import jwt
    bogus_token = jwt.encode(
        {"sub": str(user.id), "type": "access", "jti": "bogus_jti", "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE, "iat": 1000, "exp": 9999999999},
        "wrong_fake_secret_key_that_does_not_match_at_all",
        algorithm="HS256",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {bogus_token}"},
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


# ------------------------------------------------------------------------------
# 4. Token Refresh & Rotation Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_token_refresh_and_rotation():
    """Verify refresh token exchanges for a new token pair and invalidates old refresh token."""
    transport = ASGITransport(app=app)
    user, password = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login
        login_res = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user.email, "password": password},
        )
        orig_refresh = login_res.json()["refresh_token"]

        # 2. Refresh
        refresh_res = await ac.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": orig_refresh},
        )
        assert refresh_res.status_code == 200
        new_data = refresh_res.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["refresh_token"] != orig_refresh

        # 3. New access token can access /auth/me
        me_res = await ac.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {new_data['access_token']}"},
        )
        assert me_res.status_code == 200

        # 4. Old refresh token cannot be reused (rotation enforcement)
        reuse_res = await ac.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": orig_refresh},
        )
        assert reuse_res.status_code == 401
        assert "revoked" in reuse_res.json()["detail"].lower()


# ------------------------------------------------------------------------------
# 5. Logout & Redis Token Invalidation Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_logout_invalidates_token_in_redis():
    """Verify logging out blacklists the access token in Redis; immediate subsequent calls are rejected."""
    transport = ASGITransport(app=app)
    user, password = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login
        login_res = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user.email, "password": password},
        )
        access_token = login_res.json()["access_token"]
        refresh_token = login_res.json()["refresh_token"]

        # Verify token works
        pre_res = await ac.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert pre_res.status_code == 200

        # Logout
        logout_res = await ac.post(
            f"{settings.API_V1_STR}/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": refresh_token},
        )
        assert logout_res.status_code == 200

        # Access token must now be rejected
        post_res = await ac.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert post_res.status_code == 401
        assert "revoked" in post_res.json()["detail"].lower()

        # Refresh token must also be rejected
        refresh_post_logout = await ac.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_post_logout.status_code == 401


# ------------------------------------------------------------------------------
# 6. Role-Based Access Control (RBAC) Tests
# ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_rbac_admin_endpoint_permissions():
    """
    Verify RBAC on /admin/users:
    - ADMIN: 200 OK
    - INSTRUCTOR: 403 Forbidden
    - STUDENT: 403 Forbidden
    """
    transport = ASGITransport(app=app)
    admin_user, admin_pwd = await create_test_user_with_role("ADMIN")
    inst_user, inst_pwd = await create_test_user_with_role("INSTRUCTOR")
    student_user, student_pwd = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login & access
        admin_login = await ac.post(f"{settings.API_V1_STR}/auth/login", json={"email": admin_user.email, "password": admin_pwd})
        admin_token = admin_login.json()["access_token"]

        admin_res = await ac.get(f"{settings.API_V1_STR}/auth/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_res.status_code == 200
        assert isinstance(admin_res.json(), list)

        # 2. Instructor login & forbidden access
        inst_login = await ac.post(f"{settings.API_V1_STR}/auth/login", json={"email": inst_user.email, "password": inst_pwd})
        inst_token = inst_login.json()["access_token"]

        inst_res = await ac.get(f"{settings.API_V1_STR}/auth/admin/users", headers={"Authorization": f"Bearer {inst_token}"})
        assert inst_res.status_code == 403
        assert "forbidden" in inst_res.json()["detail"].lower()

        # 3. Student login & forbidden access
        student_login = await ac.post(f"{settings.API_V1_STR}/auth/login", json={"email": student_user.email, "password": student_pwd})
        student_token = student_login.json()["access_token"]

        student_res = await ac.get(f"{settings.API_V1_STR}/auth/admin/users", headers={"Authorization": f"Bearer {student_token}"})
        assert student_res.status_code == 403
        assert "forbidden" in student_res.json()["detail"].lower()


@pytest.mark.anyio
async def test_rbac_instructor_endpoint_permissions():
    """
    Verify RBAC on /instructor/dashboard:
    - INSTRUCTOR: 200 OK
    - ADMIN: 200 OK (Admins have hierarchical supervisory access)
    - STUDENT: 403 Forbidden
    """
    transport = ASGITransport(app=app)
    admin_user, admin_pwd = await create_test_user_with_role("ADMIN")
    inst_user, inst_pwd = await create_test_user_with_role("INSTRUCTOR")
    student_user, student_pwd = await create_test_user_with_role("STUDENT")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        inst_login = await ac.post(f"{settings.API_V1_STR}/auth/login", json={"email": inst_user.email, "password": inst_pwd})
        inst_token = inst_login.json()["access_token"]
        inst_res = await ac.get(f"{settings.API_V1_STR}/auth/instructor/dashboard", headers={"Authorization": f"Bearer {inst_token}"})
        assert inst_res.status_code == 200

        admin_login = await ac.post(f"{settings.API_V1_STR}/auth/login", json={"email": admin_user.email, "password": admin_pwd})
        admin_token = admin_login.json()["access_token"]
        admin_res = await ac.get(f"{settings.API_V1_STR}/auth/instructor/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_res.status_code == 200

        student_login = await ac.post(f"{settings.API_V1_STR}/auth/login", json={"email": student_user.email, "password": student_pwd})
        student_token = student_login.json()["access_token"]
        student_res = await ac.get(f"{settings.API_V1_STR}/auth/instructor/dashboard", headers={"Authorization": f"Bearer {student_token}"})
        assert student_res.status_code == 403
