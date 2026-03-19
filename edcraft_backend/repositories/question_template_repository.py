from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.repositories.base import EntityRepository


class QuestionTemplateRepository(EntityRepository[QuestionTemplate]):
    """Repository for QuestionTemplate entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionTemplate, db)

    async def get_orphaned_templates(
        self,
        owner_id: UUID,
    ) -> list[QuestionTemplate]:
        """Get question templates not in any active container.

        Args:
            owner_id: User UUID to filter templates

        Returns:
            List of orphaned question templates
        """
        stmt = select(QuestionTemplate).where(
            QuestionTemplate.owner_id == owner_id,
            QuestionTemplate.deleted_at.is_(None),
            QuestionTemplate.assessment_template_id.is_(None),
            QuestionTemplate.question_template_bank_id.is_(None),
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_assessment_template_id(
        self, assessment_template_id: UUID
    ) -> list[QuestionTemplate]:
        """Get all question templates for an assessment template, ordered by order.

        Args:
            assessment_template_id: AssessmentTemplate UUID

        Returns:
            List of QuestionTemplate instances ordered by order field
        """
        stmt = (
            select(QuestionTemplate)
            .where(
                QuestionTemplate.assessment_template_id == assessment_template_id,
                QuestionTemplate.deleted_at.is_(None),
            )
            .order_by(QuestionTemplate.order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def shift_orders_from(
        self, assessment_template_id: UUID, start_order: int
    ) -> None:
        """Shift order values up by 1 for all templates at or after start_order.

        Args:
            assessment_template_id: AssessmentTemplate UUID
            start_order: Order value to start shifting from (inclusive)
        """
        templates = await self.db.execute(
            select(QuestionTemplate)
            .where(
                QuestionTemplate.assessment_template_id == assessment_template_id,
                QuestionTemplate.order >= start_order,
                QuestionTemplate.deleted_at.is_(None),
            )
            .order_by(QuestionTemplate.order.desc())
        )
        for template in templates.scalars().all():
            if template.order is not None:
                template.order = template.order + 1
                await self.update(template)
        await self.db.flush()

    async def normalize_orders(self, assessment_template_id: UUID) -> None:
        """Normalize order values to consecutive integers starting from 0.

        Args:
            assessment_template_id: AssessmentTemplate UUID
        """
        templates = await self.get_by_assessment_template_id(assessment_template_id)
        for idx, template in enumerate(templates):
            if template.order != idx:
                template.order = idx
                await self.update(template)
        await self.db.flush()
