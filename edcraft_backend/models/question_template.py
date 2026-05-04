"""Question template model - blueprint for creating questions."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase
from edcraft_backend.models.enums import OutputType, QuestionType, TextTemplateType

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_template import AssessmentTemplate
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.question_template_bank import QuestionTemplateBank
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
    assessment_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_template_bank_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_template_banks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_from_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Order within assessment template (only relevant when assessment_template_id is set)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    question_text_template: Mapped[str] = mapped_column(Text, nullable=False)
    text_template_type: Mapped[TextTemplateType] = mapped_column(
        Enum(
            TextTemplateType,
            name="text_template_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
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
    input_data_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    code_info: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="question_templates")

    # Container relationships
    assessment_template: Mapped["AssessmentTemplate | None"] = relationship(
        back_populates="question_templates"
    )
    question_template_bank: Mapped["QuestionTemplateBank | None"] = relationship(
        back_populates="question_templates"
    )

    # Source template
    linked_from_template: Mapped["QuestionTemplate | None"] = relationship(
        "QuestionTemplate",
        foreign_keys=[linked_from_template_id],
        remote_side="QuestionTemplate.id",
    )

    # One-to-many: A template can create many questions
    questions: Mapped[list["Question"]] = relationship(
        back_populates="template", lazy="selectin"
    )

    # One-to-many: Target elements for this template
    target_elements: Mapped[list["TargetElement"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TargetElement.order",
    )

    __table_args__ = (
        CheckConstraint(
            "assessment_template_id IS NULL OR question_template_bank_id IS NULL",
            name="ck_question_template_single_container",
        ),
        CheckConstraint(
            '"order" IS NULL OR "order" >= 0',
            name="ck_question_template_order_non_negative",
        ),
        UniqueConstraint(
            "assessment_template_id",
            "order",
            name="uq_question_template_assessment_template_order",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<QuestionTemplate(id={self.id}, "
            f"text={self.question_text_template[:30]}..., type={self.question_type})>"
        )
