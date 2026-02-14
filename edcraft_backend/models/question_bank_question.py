"""Association table for many-to-many relationship between question banks and questions."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import AssociationBase

if TYPE_CHECKING:
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.question_bank import QuestionBank


class QuestionBankQuestion(AssociationBase):
    """
    Association table for many-to-many relationship between question banks and questions.
    Allows questions to be reused across multiple question banks.
    """

    __tablename__ = "question_bank_questions"

    # Foreign Keys
    question_bank_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    question_bank: Mapped["QuestionBank"] = relationship(
        back_populates="question_associations"
    )
    question: Mapped["Question"] = relationship(
        back_populates="question_bank_associations"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "question_bank_id", "question_id", name="uq_question_bank_question"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<QuestionBankQuestion(question_bank_id={self.question_bank_id}, "
            f"question_id={self.question_id})>"
        )
