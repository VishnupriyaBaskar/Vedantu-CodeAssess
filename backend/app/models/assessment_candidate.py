r"""
Assessment Candidate Junction Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.user import User


class AssessmentCandidate(Base):
    """
    Candidate eligibility mapping: links eligible students to published assessments.
    """
    __tablename__ = "assessment_candidates"
    __table_args__ = (
        UniqueConstraint("assessment_id", "user_id", name="uq_assessment_candidates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="candidates",
    )
    user: Mapped["User"] = relationship(
        "User",
    )

    def __repr__(self) -> str:
        return f"<AssessmentCandidate assessment_id={self.assessment_id} user_id={self.user_id}>"
