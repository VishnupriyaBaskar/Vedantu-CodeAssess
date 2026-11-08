r"""
Question Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.test_case import TestCase
    from app.models.submission import Submission
    from app.models.user import User


class Question(Base, TimestampMixin):
    """
    Question entity representing an individual programming challenge in the Question Bank
    or attached directly to an Assessment.
    Maintains ordered test cases and links to student submissions.
    """
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    problem_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    input_format: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    output_format: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    constraints: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        default="MEDIUM",
        index=True,
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(
        String(100),
        default="General",
        index=True,
        nullable=False,
    )
    marks: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )
    time_limit_seconds: Mapped[float] = mapped_column(
        Float,
        default=2.0,
        nullable=False,
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer,
        default=256,
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        index=True,
        nullable=False,
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        nullable=False,
    )
    tags: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    starter_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Relationships
    assessment: Mapped[Optional["Assessment"]] = relationship(
        "Assessment",
        back_populates="questions",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="TestCase.display_order",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="question",
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} title={self.title!r} difficulty={self.difficulty!r}>"
