from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment_template_question_template import (
    AssessmentTemplateQuestionTemplate,
)
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
        """Get question templates not used in any non-deleted assessment template.

        Args:
            owner_id: User UUID to filter templates

        Returns:
            List of orphaned question templates
        """
        from edcraft_backend.models.assessment_template import AssessmentTemplate

        # Subquery to get template IDs that are in use
        used_templates_subquery = (
            select(AssessmentTemplateQuestionTemplate.question_template_id)
            .join(
                AssessmentTemplate,
                AssessmentTemplateQuestionTemplate.assessment_template_id == AssessmentTemplate.id,
            )
            .where(AssessmentTemplate.deleted_at.is_(None))
        )

        # Get templates not in the used list
        stmt = (
            select(QuestionTemplate)
            .where(
                QuestionTemplate.owner_id == owner_id,
                QuestionTemplate.deleted_at.is_(None),
                QuestionTemplate.id.notin_(used_templates_subquery),
            )
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
