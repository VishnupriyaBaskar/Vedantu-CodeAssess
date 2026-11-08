r"""
Proctoring Session Domain Model
Project: Vedantu Online Coding Assessment Platform (Phase 7)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.proctoring_alert import ProctoringAlert
    from app.models.proctoring_event import ProctoringEvent
    from app.models.user import User


class ProctoringSession(Base, TimestampMixin):
    """
    Candidate proctoring session associated 1-to-1 with an assessment attempt.
    Tracks monitoring lifecycle, explicit consent status, configuration snapshot,
    and periodic heartbeats.
    """
    __tablename__ = "proctoring_sessions"
    __table_args__ = (
        UniqueConstraint("assessment_attempt_id", name="uq_proctoring_sessions_attempt"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    assessment_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        index=True,
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
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="INITIALIZED",
        index=True,
        nullable=False,
    )
    consent_given: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    monitoring_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    attempt: Mapped["AssessmentAttempt"] = relationship(
        "AssessmentAttempt",
    )
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
    )
    user: Mapped["User"] = relationship(
        "User",
    )
    events: Mapped[List["ProctoringEvent"]] = relationship(
        "ProctoringEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ProctoringEvent.recorded_at",
    )
    alerts: Mapped[List["ProctoringAlert"]] = relationship(
        "ProctoringAlert",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ProctoringAlert.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<ProctoringSession id={self.id} user_id={self.user_id} status={self.status!r}>"
