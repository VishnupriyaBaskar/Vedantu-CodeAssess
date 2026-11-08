r"""
Assessment Management Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.question import QuestionAdminResponse, QuestionPublicResponse


class AssessmentBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int = Field(..., ge=1, le=1440, description="Duration in minutes (e.g. 60, 90, 120)")
    total_marks: int = Field(default=100, ge=1)
    passing_marks: int = Field(default=40, ge=1)
    difficulty: str = Field(default="MEDIUM", pattern="^(EASY|MEDIUM|HARD)$")
    allowed_languages: str = Field(default="ALL_ACTIVE", description="'ALL_ACTIVE' or comma-separated language names (e.g. 'Python 3,Java')")
    proctoring_config: Optional[dict] = Field(default=None, description="Optional proctoring settings (webcam, fullscreen, thresholds)")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AssessmentCreate(AssessmentBase):
    question_ids: Optional[List[uuid.UUID]] = Field(default=None, description="Optional question IDs to bind to this assessment")


class AssessmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    total_marks: Optional[int] = Field(None, ge=1)
    passing_marks: Optional[int] = Field(None, ge=1)
    difficulty: Optional[str] = Field(None, pattern="^(EASY|MEDIUM|HARD)$")
    allowed_languages: Optional[str] = None
    proctoring_config: Optional[dict] = None
    status: Optional[str] = Field(None, pattern="^(DRAFT|PUBLISHED|IN_PROGRESS|COMPLETED|ARCHIVED)$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    question_ids: Optional[List[uuid.UUID]] = None


class AssessmentCandidateAssign(BaseModel):
    user_ids: List[uuid.UUID] = Field(..., min_length=1, description="List of student user UUIDs to enroll")


class AssessmentPublicResponse(BaseModel):
    """
    Student-facing assessment summary.
    """
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: int
    passing_marks: int
    difficulty: str
    status: str
    allowed_languages: List[str] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    question_count: int = 0
    has_attempted: bool = False
    attempt_status: Optional[str] = None
    proctoring_config: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentPublicDetailResponse(AssessmentPublicResponse):
    """
    Student assessment detail during active examination, containing public questions.
    """
    questions: List[QuestionPublicResponse] = Field(default_factory=list)


class AssessmentAdminResponse(AssessmentBase):
    """
    Instructor/Admin assessment management detail.
    """
    id: uuid.UUID
    status: str
    created_by: uuid.UUID
    questions: List[QuestionAdminResponse] = Field(default_factory=list)
    candidate_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
