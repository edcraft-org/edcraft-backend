"""
Association table for many-to-many relationship between assessment
templates and question templates.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.database import Base

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_template import AssessmentTemplate
    from edcraft_backend.models.question_template import QuestionTemplate


class AssessmentTemplateQuestionTemplate(Base):
    """
    Association table for many-to-many relationship between
    assessment templates and question templates.
    """

    __tablename__ = "assessment_template_question_templates"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    assessment_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Additional Fields
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    assessment_template: Mapped["AssessmentTemplate"] = relationship(
        back_populates="template_associations"
    )
    question_template: Mapped["QuestionTemplate"] = relationship(
        back_populates="assessment_template_associations"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "assessment_template_id",
            "question_template_id",
            name="uq_assessment_template_question_template",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AssessmentTemplateQuestionTemplate("
            f"assessment_template_id={self.assessment_template_id}, "
            f"question_template_id={self.question_template_id})>"
        )
