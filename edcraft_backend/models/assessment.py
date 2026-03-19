from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase
from edcraft_backend.models.enums import ResourceVisibility

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question import Question
    from edcraft_backend.models.user import User


class Assessment(EntityBase):
    """Assessment model - an ordered collection of questions."""

    __tablename__ = "assessments"

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
    visibility: Mapped[ResourceVisibility] = mapped_column(
        String(50),
        nullable=False,
        default=ResourceVisibility.PRIVATE,
        server_default="private",
    )

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
