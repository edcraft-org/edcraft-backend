"""Question template model - blueprint for creating questions."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase
from edcraft_backend.models.enums import OutputType, QuestionType

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_template_question_template import (
        AssessmentTemplateQuestionTemplate,
    )
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.target_element import TargetElement
    from edcraft_backend.models.user import User


class QuestionTemplate(EntityBase):
    """
    Question Template model - blueprint for creating question instances.
    Stores template configuration as JSON and structured fields (flexible schema).
    """

    __tablename__ = "question_templates"

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic Fields
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            name="question_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured template configuration fields
    code: Mapped[str] = mapped_column(Text, nullable=False)
    entry_function: Mapped[str] = mapped_column(String(255), nullable=False)
    num_distractors: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    output_type: Mapped[OutputType] = mapped_column(
        Enum(
            OutputType,
            name="output_type",
            native_enum=True,
            create_constraint=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="question_templates")

    # One-to-many: A template can create many questions
    questions: Mapped[list["Question"]] = relationship(back_populates="template", lazy="selectin")

    # One-to-many: Target elements for this template
    target_elements: Mapped[list["TargetElement"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TargetElement.order",
    )

    # Many-to-many relationship with assessment templates
    assessment_template_associations: Mapped[list["AssessmentTemplateQuestionTemplate"]] = (
        relationship(
            back_populates="question_template",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
    )

    def __repr__(self) -> str:
        return (
            f"<QuestionTemplate(id={self.id}, "
            f"text={self.question_text[:30]}..., type={self.question_type})>"
        )
