r"""
Assessment Attempt Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.user import User


class AssessmentAttempt(Base):
    """
    Server-authoritative student examination session.
    Enforces a strict one-attempt-per-assessment policy, server timing calculations,
    and concurrency-safe state transitions (IN_PROGRESS -> SUBMITTED -> EVALUATING -> COMPLETED).
    """
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        UniqueConstraint("assessment_id", "user_id", name="uq_assessment_attempts_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="IN_PROGRESS",
        index=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    total_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    is_passed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="attempts",
    )
    user: Mapped["User"] = relationship(
        "User",
    )

    def __repr__(self) -> str:
        return f"<AssessmentAttempt id={self.id} user_id={self.user_id} status={self.status!r}>"
