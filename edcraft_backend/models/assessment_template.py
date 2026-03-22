"""Assessment template model - collection of question templates."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from edcraft_backend.models.base import FolderResourceBase

if TYPE_CHECKING:
    from edcraft_backend.models.folder import Folder
    from edcraft_backend.models.question_template import QuestionTemplate
    from edcraft_backend.models.user import User


class AssessmentTemplate(FolderResourceBase):
    """
    Assessment Template model - collection of question templates.
    Also serves as a question template bank.
    """

    __tablename__ = "assessment_templates"

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="assessment_templates")
    folder: Mapped["Folder"] = relationship(back_populates="assessment_templates")

    # One-to-many: question templates directly owned by this assessment template
    question_templates: Mapped[list["QuestionTemplate"]] = relationship(
        back_populates="assessment_template",
        lazy="selectin",
        order_by="QuestionTemplate.order",
        foreign_keys="QuestionTemplate.assessment_template_id",
    )

    def __repr__(self) -> str:
        return f"<AssessmentTemplate(id={self.id}, title={self.title})>"
