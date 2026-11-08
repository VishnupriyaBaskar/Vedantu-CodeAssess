r"""
Submission Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.programming_language import ProgrammingLanguage
    from app.models.question import Question
    from app.models.submission_evaluation import SubmissionEvaluation
    from app.models.submission_test_case_result import SubmissionTestCaseResult
    from app.models.user import User


class Submission(Base):
    """
    Submission entity recording a student code submission against a question.
    Preserves audit integrity with RESTRICT cascades on user, assessment, question, and language.
    """
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    programming_language_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programming_languages.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    source_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
        nullable=False,
    )
    execution_time: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    memory_usage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    judge0_token: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="submissions",
    )
    assessment: Mapped[Optional["Assessment"]] = relationship(
        "Assessment",
    )
    question: Mapped["Question"] = relationship(
        "Question",
        back_populates="submissions",
    )
    programming_language: Mapped["ProgrammingLanguage"] = relationship(
        "ProgrammingLanguage",
        back_populates="submissions",
    )
    test_case_results: Mapped[List["SubmissionTestCaseResult"]] = relationship(
        "SubmissionTestCaseResult",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    evaluation: Mapped[Optional["SubmissionEvaluation"]] = relationship(
        "SubmissionEvaluation",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Submission id={self.id} user_id={self.user_id} "
            f"question_id={self.question_id} status={self.status!r} score={self.score}>"
        )
