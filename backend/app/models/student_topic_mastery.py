r"""
Student Topic Mastery Domain Model
Project: Vedantu Online Coding Assessment Platform (Phase 6)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class StudentTopicMastery(Base):
    """
    Topic Mastery entity recording aggregated student proficiency per programming topic.
    Maintains deterministic mastery score (0-100), classification level, confidence tier,
    adaptive recommended difficulty, and performance metrics.
    """
    __tablename__ = "student_topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_student_topic_mastery_user_topic"),
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
    topic: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    mastery_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    mastery_level: Mapped[str] = mapped_column(
        String(50),
        default="BEGINNER",
        index=True,
        nullable=False,
    )
    confidence_level: Mapped[str] = mapped_column(
        String(50),
        default="LOW",
        nullable=False,
    )
    questions_attempted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    questions_solved: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_submissions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    successful_submissions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    best_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    recommended_difficulty: Mapped[str] = mapped_column(
        String(50),
        default="EASY",
        nullable=False,
    )
    trend: Mapped[str] = mapped_column(
        String(50),
        default="STABLE",
        nullable=False,
    )
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<StudentTopicMastery user_id={self.user_id} topic={self.topic!r} "
            f"score={self.mastery_score:.1f} level={self.mastery_level!r}>"
        )
