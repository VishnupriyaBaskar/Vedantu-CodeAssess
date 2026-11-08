r"""
SQLAlchemy Declarative Base and Common Model Helpers
Project: Vedantu Online Coding Assessment Platform (Stage 2.6)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Canonical SQLAlchemy 2.0 Declarative Base."""
    pass


class TimestampMixin:
    """Reusable mixin providing UTC created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
