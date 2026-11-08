r"""
TestCase Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.question import Question


class TestCase(Base, TimestampMixin):
    """
    TestCase entity representing public sample or private validation test cases
    for an assessment programming question.
    """
    __tablename__ = "test_cases"
    __test__ = False

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    input_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expected_output: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default="FUNCTIONAL",
        index=True,
        nullable=False,
    )
    marks: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        index=True,
        nullable=False,
    )

    # Relationships
    question: Mapped["Question"] = relationship(
        "Question",
        back_populates="test_cases",
    )

    def __repr__(self) -> str:
        return (
            f"<TestCase id={self.id} question_id={self.question_id} "
            f"is_hidden={self.is_hidden} marks={self.marks}>"
        )
