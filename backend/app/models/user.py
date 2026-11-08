r"""
User Domain Model
Project: Vedantu Online Coding Assessment Platform (Stage 2.6)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import TYPE_CHECKING, List
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.role import Role, UserRole
    from app.models.assessment import Assessment
    from app.models.submission import Submission


class User(Base, TimestampMixin):
    """
    User entity representing students, instructors, and system administrators.
    Enforces UUID primary keys, globally unique email addresses, and account status flags.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        index=True,
        nullable=False,
    )

    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        viewonly=True,
    )
    assessments_created: Mapped[List["Assessment"]] = relationship(
        "Assessment",
        back_populates="creator",
        cascade="all, delete",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} status={self.status!r}>"
