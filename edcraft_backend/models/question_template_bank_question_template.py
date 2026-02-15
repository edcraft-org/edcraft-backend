"""Association model between question template banks and question templates."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import AssociationBase

if TYPE_CHECKING:
    from edcraft_backend.models.question_template import QuestionTemplate
    from edcraft_backend.models.question_template_bank import QuestionTemplateBank


class QuestionTemplateBankQuestionTemplate(AssociationBase):
    """
    Many-to-many association between QuestionTemplateBank and QuestionTemplate.
    Unlike AssessmentTemplateQuestionTemplate, this does NOT have an order field.
    """

    __tablename__ = "question_template_bank_question_templates"

    # Foreign Keys
    question_template_bank_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_template_banks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    question_template_bank: Mapped["QuestionTemplateBank"] = relationship(
        back_populates="template_associations"
    )
    question_template: Mapped["QuestionTemplate"] = relationship(
        back_populates="question_template_bank_associations"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "question_template_bank_id",
            "question_template_id",
            name="uq_question_template_bank_question_template",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<QuestionTemplateBankQuestionTemplate("
            f"bank_id={self.question_template_bank_id}, "
            f"template_id={self.question_template_id})>"
        )
