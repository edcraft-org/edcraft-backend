"""Assessment template model - collection of question templates."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.database import Base

if TYPE_CHECKING:
    from edcraft_backend.models.assessment_template_question_template import (
        AssessmentTemplateQuestionTemplate,
    )
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.user import User


class AssessmentTemplate(Base):
    """
    Assessment Template model - collection of question templates.
    Also serves as a question template bank.
    """

    __tablename__ = "assessment_templates"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Basic Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    owner: Mapped["User"] = relationship(back_populates="assessment_templates")
    folder: Mapped["Folder | None"] = relationship(back_populates="assessment_templates")

    # Many-to-many relationship with question templates
    template_associations: Mapped[list["AssessmentTemplateQuestionTemplate"]] = relationship(
        back_populates="assessment_template",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AssessmentTemplate(id={self.id}, title={self.title})>"
