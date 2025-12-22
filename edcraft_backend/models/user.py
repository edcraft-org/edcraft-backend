"""User model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.database import Base

if TYPE_CHECKING:
    from edcraft_backend.models.assessment import Assessment
    from edcraft_backend.models.assessment_template import AssessmentTemplate
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.question_template import QuestionTemplate


class User(Base):
    """User model."""

    __tablename__ = "users"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Basic Fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

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
    folders: Mapped[list["Folder"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    assessment_templates: Mapped[list["AssessmentTemplate"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    question_templates: Mapped[list["QuestionTemplate"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
