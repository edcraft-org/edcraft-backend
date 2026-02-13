"""Target element model for question templates."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ARRAY, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import Base
from edcraft_backend.models.enums import TargetElementType, TargetModifier

if TYPE_CHECKING:
    from edcraft_backend.models.question_template import QuestionTemplate


class TargetElement(Base):
    """
    Represents a single target element in a question template's target list.
    Uses composite primary key (template_id, order) to maintain list sequence.
    """

    __tablename__ = "target_elements"

    # Composite primary key
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_templates.id", ondelete="CASCADE"), primary_key=True
    )
    order: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Target element fields
    element_type: Mapped[TargetElementType] = mapped_column(
        Enum(
            TargetElementType,
            name="target_element_type",
            native_enum=True,
            create_constraint=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    id_list: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modifier: Mapped[TargetModifier | None] = mapped_column(
        Enum(
            TargetModifier,
            name="target_modifier",
            native_enum=True,
            create_constraint=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )

    # Relationship
    template: Mapped["QuestionTemplate"] = relationship(back_populates="target_elements")

    def __repr__(self) -> str:
        return (
            f"<TargetElement(template_id={self.template_id}, order={self.order}, "
            f"type={self.element_type})>"
        )
