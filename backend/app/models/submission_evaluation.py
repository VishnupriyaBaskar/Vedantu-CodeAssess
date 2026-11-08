r"""
Submission Evaluation Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.submission import Submission


class SubmissionEvaluation(Base):
    """
    Qualitative evaluation result combining:
    - Static code analysis findings (AST, cyclomatic complexity, code smells, readability)
    - AI qualitative evaluation (logical approach, algorithmic efficiency, improvement suggestions)
    - Evaluation metadata (AI provider name, completion status, created timestamp)

    Kept strictly independent from authoritative deterministic scoring.
    """
    __tablename__ = "submission_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    static_analysis: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    ai_feedback: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    ai_provider: Mapped[str] = mapped_column(
        String(50),
        default="mock",
        nullable=False,
    )
    ai_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="evaluation",
    )

    def __repr__(self) -> str:
        return (
            f"<SubmissionEvaluation id={self.id} submission_id={self.submission_id} "
            f"provider={self.ai_provider!r} status={self.ai_status!r}>"
        )
