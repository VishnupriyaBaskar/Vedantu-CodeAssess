r"""
Topic Mastery History Domain Model
Project: Vedantu Online Coding Assessment Platform (Phase 6)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class TopicMasteryHistory(Base):
    """
    Topic Mastery Snapshot entity maintaining longitudinal mastery progression over time.
    Provides verifiable historical data for learning curves, trend identification,
    and adaptive learning insights.
    """
    __tablename__ = "topic_mastery_history"

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
    topic: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    mastery_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    mastery_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    trigger_event: Mapped[str] = mapped_column(
        String(50),
        default="RECALCULATION",
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<TopicMasteryHistory user_id={self.user_id} topic={self.topic!r} "
            f"score={self.mastery_score:.1f} event={self.trigger_event!r}>"
        )
