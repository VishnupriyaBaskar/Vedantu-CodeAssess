r"""
Authentication Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.user import UserResponse


class UserRegisterRequest(BaseModel):
    """
    Public student registration schema.
    Strictly forbids role specification to prevent privilege escalation.
    """
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of student")
    email: EmailStr = Field(..., description="Unique email address for authentication")
    password: str = Field(..., min_length=8, max_length=128, description="Candidate plaintext password meeting strength criteria")

    # Extra fields (such as 'role' or 'is_admin') are forbidden
    model_config = ConfigDict(extra="forbid")


class UserLoginRequest(BaseModel):
    """Credentials payload for email/password authentication."""
    email: EmailStr = Field(..., description="Registered user email")
    password: str = Field(..., min_length=1, max_length=128, description="User password")

    model_config = ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    """Full authentication response containing tokens and user metadata."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration period in seconds")
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    """Payload to exchange a valid refresh token for a fresh token pair."""
    refresh_token: str = Field(..., min_length=10, description="Valid JWT refresh token")

    model_config = ConfigDict(extra="forbid")


class TokenRefreshResponse(BaseModel):
    """Rotated token pair returned by refresh endpoint."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Optional payload to invalidate a specific refresh token during logout."""
    refresh_token: Optional[str] = None


class MessageResponse(BaseModel):
    """Standard operation outcome response."""
    message: str
    detail: Optional[str] = None
