"""Question template bank model - collection of question templates."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from edcraft_backend.models.base import FolderResourceBase

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question_template import QuestionTemplate
    from edcraft_backend.models.user import User


class QuestionTemplateBank(FolderResourceBase):
    """
    Question Template Bank model - collection of reusable question templates.
    Unlike AssessmentTemplate, this does not have ordering functionality.
    """

    __tablename__ = "question_template_banks"

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="question_template_banks")
    folder: Mapped["Folder"] = relationship(back_populates="question_template_banks")
    # One-to-many: question templates directly owned by this bank
    question_templates: Mapped[list["QuestionTemplate"]] = relationship(
        back_populates="question_template_bank",
        lazy="selectin",
        foreign_keys="QuestionTemplate.question_template_bank_id",
    )

    def __repr__(self) -> str:
        return f"<QuestionTemplateBank(id={self.id}, title={self.title})>"
