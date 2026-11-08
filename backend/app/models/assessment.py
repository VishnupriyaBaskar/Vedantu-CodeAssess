r"""
Assessment Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.question import Question
    from app.models.assessment_candidate import AssessmentCandidate
    from app.models.assessment_attempt import AssessmentAttempt


class Assessment(Base, TimestampMixin):
    """
    Assessment entity representing timed online coding examinations or challenges.
    Protected against accidental deletion via RESTRICT foreign keys on creator.
    """
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_marks: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    passing_marks: Mapped[int] = mapped_column(
        Integer,
        default=40,
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        default="MEDIUM",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        index=True,
        nullable=False,
    )
    allowed_languages: Mapped[str] = mapped_column(
        String(255),
        default="ALL_ACTIVE",
        nullable=False,
    )
    proctoring_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="assessments_created",
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="Question.display_order",
    )
    candidates: Mapped[List["AssessmentCandidate"]] = relationship(
        "AssessmentCandidate",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    attempts: Mapped[List["AssessmentAttempt"]] = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Assessment id={self.id} title={self.title!r} status={self.status!r}>"
