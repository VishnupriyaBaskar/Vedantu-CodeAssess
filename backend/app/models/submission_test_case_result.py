r"""
Submission TestCase Result Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.test_case import TestCase


class SubmissionTestCaseResult(Base):
    """
    Granular evaluation result for a single test case within a student submission.
    Provides verifiable audit trails while strictly isolating confidential hidden test data.
    """
    __tablename__ = "submission_test_case_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
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
    marks_awarded: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_sample: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="test_case_results",
    )
    test_case: Mapped["TestCase"] = relationship("TestCase")

    def __repr__(self) -> str:
        return f"<SubmissionTestCaseResult id={self.id} status={self.status!r} marks={self.marks_awarded}>"
