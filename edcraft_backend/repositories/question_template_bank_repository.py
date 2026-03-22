from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.enums import ResourceType
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.repositories.collaborative_resource_repository import (
    FolderResourceRepository,
)


class QuestionTemplateBankRepository(FolderResourceRepository[QuestionTemplateBank]):
    """Repository for QuestionTemplateBank entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionTemplateBank, ResourceType.QUESTION_TEMPLATE_BANK, db)

    async def get_by_id_with_templates(
        self,
        question_template_bank_id: UUID,
        include_deleted: bool = False,
    ) -> QuestionTemplateBank | None:
        """Get question template bank by ID with all templates loaded.

        Args:
            question_template_bank_id: QuestionTemplateBank UUID
            include_deleted: Whether to include soft-deleted question template banks

        Returns:
            QuestionTemplateBank with templates loaded, or None if not found
        """
        stmt = (
            select(QuestionTemplateBank)
            .where(QuestionTemplateBank.id == question_template_bank_id)
            .options(
                selectinload(QuestionTemplateBank.question_templates).selectinload(
                    QuestionTemplate.target_elements
                )
            )
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(QuestionTemplateBank.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
