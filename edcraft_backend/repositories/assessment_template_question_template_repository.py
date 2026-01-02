from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment_template_question_template import (
    AssessmentTemplateQuestionTemplate,
)
from edcraft_backend.repositories.base import AssociationRepository


class AssessmentTemplateQuestionTemplateRepository(
    AssociationRepository[AssessmentTemplateQuestionTemplate]
):
    """Repository for AssessmentTemplateQuestionTemplate association operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(AssessmentTemplateQuestionTemplate, db)

    async def find_association(
        self,
        assessment_template_id: UUID,
        question_template_id: UUID,
    ) -> AssessmentTemplateQuestionTemplate | None:
        """Find association between assessment template and question template.

        Args:
            assessment_template_id: AssessmentTemplate UUID
            question_template_id: QuestionTemplate UUID

        Returns:
            AssessmentTemplateQuestionTemplate association if found, None otherwise
        """
        stmt = select(AssessmentTemplateQuestionTemplate).where(
            AssessmentTemplateQuestionTemplate.assessment_template_id
            == assessment_template_id,
            AssessmentTemplateQuestionTemplate.question_template_id
            == question_template_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_count(self, assessment_template_id: UUID) -> int:
        """Get the count of question templates in an assessment template.

        Args:
            assessment_template_id: AssessmentTemplate UUID

        Returns:
            Count of question templates
        """
        stmt = select(
            func.count(AssessmentTemplateQuestionTemplate.id)
        ).where(
            AssessmentTemplateQuestionTemplate.assessment_template_id
            == assessment_template_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_all_for_assessment_template(
        self,
        assessment_template_id: UUID,
    ) -> list[AssessmentTemplateQuestionTemplate]:
        """Get all question template associations for an assessment template,
        ordered by order field.

        Args:
            assessment_template_id: AssessmentTemplate UUID

        Returns:
            List of AssessmentTemplateQuestionTemplate associations ordered by order field
        """
        stmt = (
            select(AssessmentTemplateQuestionTemplate)
            .where(
                AssessmentTemplateQuestionTemplate.assessment_template_id
                == assessment_template_id
            )
            .order_by(AssessmentTemplateQuestionTemplate.order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def shift_orders_from(
        self, assessment_template_id: UUID, start_order: int
    ) -> None:
        """Shift order values up by 1 for all question templates at or after start_order.

        Args:
            assessment_template_id: AssessmentTemplate UUID
            start_order: Order value to start shifting from (inclusive)
        """
        # Get all associations that need shifting, ordered by order DESC
        stmt = (
            select(AssessmentTemplateQuestionTemplate)
            .where(
                AssessmentTemplateQuestionTemplate.assessment_template_id
                == assessment_template_id,
                AssessmentTemplateQuestionTemplate.order >= start_order,
            )
            .order_by(AssessmentTemplateQuestionTemplate.order.desc())
        )
        result = await self.db.execute(stmt)
        associations = list(result.scalars().all())

        # Update in descending order to avoid constraint violations
        for assoc in associations:
            assoc.order += 1
            await self.update(assoc)

        await self.db.flush()

    async def normalize_orders(self, assessment_template_id: UUID) -> None:
        """Normalize order values to consecutive integers starting from 0.

        Renumbers all questions in an assessment template to have consecutive order values
        (0, 1, 2, 3...) based on their current order and added_at timestamp.

        Args:
            assessment_template_id: AssessmentTemplate UUID
        """
        associations = await self.get_all_for_assessment_template(
            assessment_template_id
        )

        for idx, assoc in enumerate(associations):
            if assoc.order != idx:
                assoc.order = idx
                await self.update(assoc)

        await self.db.flush()
