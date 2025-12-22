"""Question template model - blueprint for creating questions."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.database import Base

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_template_question_template import (
        AssessmentTemplateQuestionTemplate,
    )
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.user import User


class QuestionTemplate(Base):
    """
    Question Template model - blueprint for creating question instances.
    Stores template configuration as JSON and structured fields (flexible schema).
    """

    __tablename__ = "question_templates"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic Fields
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., 'mcq', 'mrq', 'short_answer'
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # TODO
    # Template-specific data (flexible JSON structure)
    template_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

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
    owner: Mapped["User"] = relationship(back_populates="question_templates")

    # One-to-many: A template can create many questions
    questions: Mapped[list["Question"]] = relationship(back_populates="template", lazy="selectin")

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
