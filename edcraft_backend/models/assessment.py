from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from edcraft_backend.models.base import FolderResourceBase

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.user import User


class Assessment(FolderResourceBase):
    """Assessment model - an ordered collection of questions."""

    __tablename__ = "assessments"

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="assessments")
    folder: Mapped["Folder"] = relationship(back_populates="assessments")

    # One-to-many relationship with questions, ordered by order field
    questions: Mapped[list["Question"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Question.order",
        foreign_keys="Question.assessment_id",
    )

    def __repr__(self) -> str:
        return f"<Assessment(id={self.id}, title={self.title})>"
