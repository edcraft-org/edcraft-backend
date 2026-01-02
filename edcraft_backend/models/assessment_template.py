"""Assessment template model - collection of question templates."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_template_question_template import (
        AssessmentTemplateQuestionTemplate,
    )
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.user import User


class AssessmentTemplate(EntityBase):
    """
    Assessment Template model - collection of question templates.
    Also serves as a question template bank.
    """

    __tablename__ = "assessment_templates"

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Basic Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="assessment_templates")
    folder: Mapped["Folder | None"] = relationship(back_populates="assessment_templates")

    # Many-to-many relationship with question templates
    template_associations: Mapped[list["AssessmentTemplateQuestionTemplate"]] = relationship(
        back_populates="assessment_template",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentTemplateQuestionTemplate.order",
    )

    def __repr__(self) -> str:
        return f"<AssessmentTemplate(id={self.id}, title={self.title})>"
