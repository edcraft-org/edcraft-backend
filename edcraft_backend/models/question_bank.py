from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question_bank_question import QuestionBankQuestion
    from edcraft_backend.models.user import User


class QuestionBank(EntityBase):
    """Question Bank - collection of reusable questions for storage."""

    __tablename__ = "question_banks"

    # Foreign Keys
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="question_banks")
    folder: Mapped["Folder"] = relationship(back_populates="question_banks")

    # Many-to-many relationship with questions
    question_associations: Mapped[list["QuestionBankQuestion"]] = relationship(
        back_populates="question_bank",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<QuestionBank(id={self.id}, title={self.title})>"
