from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.models.question_template_bank_question_template import (
    QuestionTemplateBankQuestionTemplate,
)
from edcraft_backend.repositories.base import AssociationRepository


class QuestionTemplateBankQuestionTemplateRepository(
    AssociationRepository[QuestionTemplateBankQuestionTemplate]
):
    """Repository for QuestionTemplateBankQuestionTemplate association operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionTemplateBankQuestionTemplate, db)

    async def find_association(
        self,
        question_template_bank_id: UUID,
        question_template_id: UUID,
    ) -> QuestionTemplateBankQuestionTemplate | None:
        """Find association between question template bank and question template.

        Args:
            question_template_bank_id: QuestionTemplateBank UUID
            question_template_id: QuestionTemplate UUID

        Returns:
            QuestionTemplateBankQuestionTemplate association if found, None otherwise
        """
        stmt = select(QuestionTemplateBankQuestionTemplate).where(
            QuestionTemplateBankQuestionTemplate.question_template_bank_id
            == question_template_bank_id,
            QuestionTemplateBankQuestionTemplate.question_template_id
            == question_template_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_question_template_bank(
        self,
        question_template_bank_id: UUID,
    ) -> list[QuestionTemplateBankQuestionTemplate]:
        """Get all template associations for a question template bank.

        Args:
            question_template_bank_id: QuestionTemplateBank UUID

        Returns:
            List of QuestionTemplateBankQuestionTemplate associations
        """
        stmt = select(QuestionTemplateBankQuestionTemplate).where(
            QuestionTemplateBankQuestionTemplate.question_template_bank_id
            == question_template_bank_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_question_template_banks_by_question_template_id(
        self,
        question_template_id: UUID,
    ) -> list[QuestionTemplateBank]:
        """Get all question template banks that contain a specific question template.

        Args:
            question_template_id: QuestionTemplate UUID

        Returns:
            List of QuestionTemplateBank objects that include this template
        """
        stmt = (
            select(QuestionTemplateBank)
            .join(
                QuestionTemplateBankQuestionTemplate,
                QuestionTemplateBank.id
                == QuestionTemplateBankQuestionTemplate.question_template_bank_id,
            )
            .where(
                QuestionTemplateBankQuestionTemplate.question_template_id
                == question_template_id
            )
            .order_by(QuestionTemplateBank.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
