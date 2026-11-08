r"""
Proctoring Event Domain Model
Project: Vedantu Online Coding Assessment Platform (Phase 7)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.proctoring_session import ProctoringSession


class ProctoringEvent(Base):
    """
    Immutable audit log entry for browser focus, visibility, fullscreen,
    and technical camera status events during an assessment.
    """
    __tablename__ = "proctoring_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    proctoring_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proctoring_sessions.id", ondelete="CASCADE"),
        index=True,
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
    event_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default="LOW",
        index=True,
        nullable=False,
    )
    event_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    session: Mapped["ProctoringSession"] = relationship(
        "ProctoringSession",
        back_populates="events",
    )

    def __repr__(self) -> str:
        return f"<ProctoringEvent id={self.id} type={self.event_type!r} severity={self.severity!r}>"
