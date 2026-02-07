"""User model."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.assessment import Assessment
    from edcraft_backend.models.assessment_template import AssessmentTemplate
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.oauth_account import OAuthAccount
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.question_template import QuestionTemplate


class User(EntityBase):
    """User model."""

    __tablename__ = "users"

    # Basic Fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Auth Fields
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

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
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
