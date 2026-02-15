from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.models.question_template_bank_question_template import (
    QuestionTemplateBankQuestionTemplate,
)
from edcraft_backend.repositories.base import EntityRepository


class QuestionTemplateBankRepository(EntityRepository[QuestionTemplateBank]):
    """Repository for QuestionTemplateBank entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionTemplateBank, db)

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
                selectinload(QuestionTemplateBank.template_associations).selectinload(
                    QuestionTemplateBankQuestionTemplate.question_template
                )
            )
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(QuestionTemplateBank.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_folder(
        self,
        folder_id: UUID,
        include_deleted: bool = False,
    ) -> list[QuestionTemplateBank]:
        """Get all question template banks in a folder.

        Args:
            folder_id: Folder UUID
            include_deleted: Whether to include soft-deleted question template banks

        Returns:
            List of question template banks in the folder ordered by last updated descending
        """
        stmt = (
            select(QuestionTemplateBank)
            .where(QuestionTemplateBank.folder_id == folder_id)
            .order_by(QuestionTemplateBank.updated_at.desc())
        )

        if not include_deleted:
            stmt = stmt.where(QuestionTemplateBank.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_soft_delete_by_folder_ids(self, folder_ids: list[UUID]) -> None:
        """Bulk soft-delete question template banks by folder IDs.

        Args:
            folder_ids: List of folder UUIDs whose banks should be soft-deleted
        """
        from datetime import UTC, datetime

        if not folder_ids:
            return

        stmt = (
            update(QuestionTemplateBank)
            .where(QuestionTemplateBank.folder_id.in_(folder_ids))
            .where(QuestionTemplateBank.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await self.db.execute(stmt)
        await self.db.flush()
