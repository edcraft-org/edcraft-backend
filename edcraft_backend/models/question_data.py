"""Models for question-related data for each question type."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ARRAY, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import Base

if TYPE_CHECKING:
    from edcraft_backend.models.question import Question


class MCQData(Base):
    """Data for Multiple Choice Questions."""

    __tablename__ = "mcq_data"

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    options: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped["Question"] = relationship(back_populates="mcq_data")


class MRQData(Base):
    """Data for Multiple Response Questions."""

    __tablename__ = "mrq_data"

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    options: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    correct_indices: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)

    question: Mapped["Question"] = relationship(back_populates="mrq_data")


class ShortAnswerData(Base):
    """Data for Short Answer Questions."""

    __tablename__ = "short_answer_data"

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)

    question: Mapped["Question"] = relationship(back_populates="short_answer_data")
