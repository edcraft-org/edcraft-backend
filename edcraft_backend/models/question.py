"""Question model - individual question instance."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.database import Base

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_question import AssessmentQuestion
    from edcraft_backend.models.question_template import QuestionTemplate
    from edcraft_backend.models.user import User


class Question(Base):
    """
    Question model - individual question instance created from a template.
    Stores the actual question data as a mixture of JSON and structured fields (flexible schema).
    """

    __tablename__ = "questions"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

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
    additional_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Soft Delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
