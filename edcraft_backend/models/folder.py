"""Folder model with tree structure."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.assessment import Assessment
    from edcraft_backend.models.assessment_template import AssessmentTemplate
    from edcraft_backend.models.question_bank import QuestionBank
    from edcraft_backend.models.question_template_bank import QuestionTemplateBank
    from edcraft_backend.models.user import User


class Folder(EntityBase):
    """
    Folder model with tree structure.
    Can contain: sub-folders, assessments, assessment_templates, question_banks
    """

    __tablename__ = "folders"

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

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="folders")

    # Self-referential relationship for tree structure
    parent: Mapped["Folder | None"] = relationship(
        "Folder", remote_side="[Folder.id]", back_populates="children", lazy="joined"
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
    question_banks: Mapped[list["QuestionBank"]] = relationship(
        back_populates="folder", cascade="all, delete-orphan", lazy="selectin"
    )
    question_template_banks: Mapped[list["QuestionTemplateBank"]] = relationship(
        back_populates="folder", cascade="all, delete-orphan", lazy="selectin"
    )

    # Constraints
    __table_args__ = (
        # Ensure unique folder names within the same parent for the same user
        UniqueConstraint(
            "owner_id", "parent_id", "name", name="uq_folder_name_per_parent_user"
        ),
        # Ensure each user has only one root folder (no parent, not deleted)
        Index(
            "uq_one_root_per_user",
            "owner_id",
            unique=True,
            postgresql_where=text("(parent_id IS NULL) AND (deleted_at IS NULL)"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Folder(id={self.id}, name={self.name}, parent_id={self.parent_id})>"
