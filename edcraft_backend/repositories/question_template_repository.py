from uuid import UUID

from sqlalchemy import select, union
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
        """Get unused question templates.

        A template is considered orphaned if it's not in ANY of:
        - Non-deleted AssessmentTemplate
        - Non-deleted QuestionTemplateBank

        Args:
            owner_id: User UUID to filter templates

        Returns:
            List of orphaned question templates
        """
        from edcraft_backend.models.assessment_template import AssessmentTemplate
        from edcraft_backend.models.question_template_bank import QuestionTemplateBank
        from edcraft_backend.models.question_template_bank_question_template import (
            QuestionTemplateBankQuestionTemplate,
        )

        # Subquery for templates in use by assessment templates
        used_in_assessment_templates_subquery = (
            select(AssessmentTemplateQuestionTemplate.question_template_id)
            .join(
                AssessmentTemplate,
                AssessmentTemplateQuestionTemplate.assessment_template_id
                == AssessmentTemplate.id,
            )
            .where(AssessmentTemplate.deleted_at.is_(None))
        )

        # Subquery for templates in use by question template banks
        used_in_template_banks_subquery = (
            select(QuestionTemplateBankQuestionTemplate.question_template_id)
            .join(
                QuestionTemplateBank,
                QuestionTemplateBankQuestionTemplate.question_template_bank_id
                == QuestionTemplateBank.id,
            )
            .where(QuestionTemplateBank.deleted_at.is_(None))
        )

        used_question_templates_subquery = union(
            used_in_assessment_templates_subquery, used_in_template_banks_subquery
        ).subquery()

        # Get templates not in either used list
        stmt = select(QuestionTemplate).where(
            QuestionTemplate.owner_id == owner_id,
            QuestionTemplate.deleted_at.is_(None),
            QuestionTemplate.id.notin_(
                select(used_question_templates_subquery.c.question_template_id)
            ),
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
