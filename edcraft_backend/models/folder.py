"""Folder model with tree structure."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.database import Base

if TYPE_CHECKING:
    from edcraft_backend.models.assessment import Assessment
    from edcraft_backend.models.assessment_template import AssessmentTemplate
    from edcraft_backend.models.user import User


class Folder(Base):
    """
    Folder model with tree structure.
    Can contain: sub-folders, assessments, assessment_templates
    """

    __tablename__ = "folders"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Basic Fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="folders")

    # Self-referential relationship for tree structure
    parent: Mapped["Folder | None"] = relationship(
        "Folder", remote_side=[id], back_populates="children", lazy="joined"
    )
    children: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="parent", cascade="all, delete-orphan", lazy="selectin"
    )

    # Contains relationships
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="folder", cascade="all, delete-orphan", lazy="selectin"
    )
    assessment_templates: Mapped[list["AssessmentTemplate"]] = relationship(
        back_populates="folder", cascade="all, delete-orphan", lazy="selectin"
    )

    # Constraints
    __table_args__ = (
        # Ensure unique folder names within the same parent for the same user
        UniqueConstraint("owner_id", "parent_id", "name", name="uq_folder_name_per_parent_user"),
    )

    def __repr__(self) -> str:
        return f"<Folder(id={self.id}, name={self.name}, parent_id={self.parent_id})>"
