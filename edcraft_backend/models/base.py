"""Base models for entities and associations."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from edcraft_backend.models.enums import ResourceVisibility


# Shared declarative base for all models
class Base(DeclarativeBase):
    """Shared base class for all database models."""

    pass


# Base class for entity models
class EntityBase(Base):
    """Base class for entity models (User, Folder, Question, etc.)."""

    __abstract__ = True

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Soft Delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FolderResourceBase(EntityBase):
    """Abstract base for folder-based collaborative resources (Assessment, QuestionBank, etc.)."""

    __abstract__ = True

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visibility: Mapped[ResourceVisibility] = mapped_column(
        String(50), nullable=False, default=ResourceVisibility.PRIVATE
    )


# Base class for association/junction tables
class AssociationBase(Base):
    """Base class for association/junction tables."""

    __abstract__ = True

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Timestamp for when the association was created
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
