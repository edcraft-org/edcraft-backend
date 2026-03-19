"""Question model - individual question instance."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.exceptions import DataIntegrityError
from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.assessment import Assessment
    from edcraft_backend.models.question_bank import QuestionBank
    from edcraft_backend.models.question_data import MCQData, MRQData, ShortAnswerData
    from edcraft_backend.models.question_template import QuestionTemplate
    from edcraft_backend.models.user import User


class Question(EntityBase):
    """
    Question model - individual question instance created from a template.
    Question-type-specific data is stored in separate related tables.
    Each question belongs to at most one container (assessment or question bank).
    """

    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('mcq', 'mrq', 'short_answer')",
            name="valid_question_type",
        ),
        CheckConstraint(
            "assessment_id IS NULL OR question_bank_id IS NULL",
            name="ck_question_single_container",
        ),
        UniqueConstraint("assessment_id", "order", name="uq_question_assessment_order"),
    )

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_from_question_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_bank_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_banks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Ordering within assessment (only relevant when assessment_id is set)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Basic Fields
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., 'mcq', 'mrq', 'short_answer'
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="questions")
    template: Mapped["QuestionTemplate | None"] = relationship(
        back_populates="questions"
    )
    assessment: Mapped[Optional["Assessment"]] = relationship(
        back_populates="questions",
        foreign_keys=[assessment_id],
    )
    question_bank: Mapped[Optional["QuestionBank"]] = relationship(
        back_populates="questions",
        foreign_keys=[question_bank_id],
    )

    # Question-type-specific data (one-to-one, only one will be populated based on question_type)
    mcq_data: Mapped["MCQData | None"] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    mrq_data: Mapped["MRQData | None"] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    short_answer_data: Mapped["ShortAnswerData | None"] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    @property
    def data(self) -> "MCQData | MRQData | ShortAnswerData":
        """Unified accessor for question-type-specific data.

        Returns:
            The populated data relationship based on question_type.

        Raises:
            DataIntegrityError: If no data is populated (data integrity issue).
        """
        result = self.mcq_data or self.mrq_data or self.short_answer_data
        if result is None:
            raise DataIntegrityError(
                f"Question {self.id} (type: {self.question_type}) has no associated data."
            )
        return result

    def __repr__(self) -> str:
        return (
            f"<Question(id={self.id}, text={self.question_text[:30]}..., "
            f"type={self.question_type})>"
        )
