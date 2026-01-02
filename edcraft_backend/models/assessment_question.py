"""Association table for many-to-many relationship between assessments and questions."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import AssociationBase

if TYPE_CHECKING:
    from edcraft_backend.models.assessment import Assessment
    from edcraft_backend.models.question import Question


class AssessmentQuestion(AssociationBase):
    """
    Association table for many-to-many relationship between assessments and questions.
    Allows questions to be reused across multiple assessments.
    Tracks ordering within an assessment.
    """

    __tablename__ = "assessment_questions"

    # Foreign Keys
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Additional Fields
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    assessment: Mapped["Assessment"] = relationship(back_populates="question_associations")
    question: Mapped["Question"] = relationship(back_populates="assessment_associations")

    # Constraints
    __table_args__ = (
        # Ensure a question can only be added once to an assessment
        UniqueConstraint("assessment_id", "question_id", name="uq_assessment_question"),
        UniqueConstraint("assessment_id", "order", name="uq_assessment_question_order"),
    )

    def __repr__(self) -> str:
        return (
            f"<AssessmentQuestion(assessment_id={self.assessment_id}, "
            f"question_id={self.question_id})>"
        )
