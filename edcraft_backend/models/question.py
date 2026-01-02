"""Question model - individual question instance."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_question import AssessmentQuestion
    from edcraft_backend.models.question_template import QuestionTemplate
    from edcraft_backend.models.user import User


class Question(EntityBase):
    """
    Question model - individual question instance created from a template.
    Stores the actual question data as a mixture of JSON and structured fields (flexible schema).
    """

    __tablename__ = "questions"

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Basic Fields
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., 'mcq', 'mrq', 'short_answer'
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional data (flexible JSON structure)
    # For multiple_choice: {"options": ["A", "B", "C"], "correct_indices": [0]}
    # For short_answer: {"correct_answer": "42"}
    additional_data: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="questions")
    template: Mapped["QuestionTemplate | None"] = relationship(back_populates="questions")

    # Many-to-many relationship with assessments
    assessment_associations: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Question(id={self.id}, text={self.question_text[:30]}..., "
            f"type={self.question_type})>"
        )
