r"""
User Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Stage 3)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import List
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Full legal name of candidate")
    email: EmailStr = Field(..., description="Unique user email address")


class UserResponse(UserBase):
    """
    Public sanitized user profile representation.
    Guarantees password hashes are never exposed.
    """
    id: uuid.UUID
    status: str
    roles: List[str] = Field(default_factory=list, description="Assigned role names (e.g. STUDENT, INSTRUCTOR, ADMIN)")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)
