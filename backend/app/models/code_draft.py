r"""
Code Draft Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.programming_language import ProgrammingLanguage
    from app.models.question import Question
    from app.models.user import User


class CodeDraft(Base):
    """
    Autosaved code draft per candidate, assessment, and question.
    Used for crash resilience and automated evaluation upon assessment expiry.
    """
    __tablename__ = "code_drafts"
    __table_args__ = (
        UniqueConstraint("user_id", "assessment_id", "question_id", name="uq_code_drafts_user_assessment_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
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
        default="",
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    assessment: Mapped["Assessment"] = relationship("Assessment")
    question: Mapped["Question"] = relationship("Question")
    programming_language: Mapped["ProgrammingLanguage"] = relationship("ProgrammingLanguage")

    def __repr__(self) -> str:
        return f"<CodeDraft user_id={self.user_id} question_id={self.question_id}>"
