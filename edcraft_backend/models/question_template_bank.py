"""Question template bank model - collection of question templates."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question_template_bank_question_template import (
        QuestionTemplateBankQuestionTemplate,
    )
    from edcraft_backend.models.user import User


class QuestionTemplateBank(EntityBase):
    """
    Question Template Bank model - collection of reusable question templates.
    Unlike AssessmentTemplate, this does not have ordering functionality.
    """

    __tablename__ = "question_template_banks"

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="question_template_banks")
    folder: Mapped["Folder"] = relationship(back_populates="question_template_banks")
    template_associations: Mapped[list["QuestionTemplateBankQuestionTemplate"]] = (
        relationship(
            back_populates="question_template_bank",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
    )

    def __repr__(self) -> str:
        return f"<QuestionTemplateBank(id={self.id}, title={self.title})>"
