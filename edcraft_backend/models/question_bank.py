from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from edcraft_backend.models.base import FolderResourceBase

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.user import User


class QuestionBank(FolderResourceBase):
    """Question Bank - collection of reusable questions for storage."""

    __tablename__ = "question_banks"

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="question_banks")
    folder: Mapped["Folder"] = relationship(back_populates="question_banks")

    # One-to-many relationship with questions
    questions: Mapped[list["Question"]] = relationship(
        back_populates="question_bank",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Question.question_bank_id",
    )

    def __repr__(self) -> str:
        return f"<QuestionBank(id={self.id}, title={self.title})>"
