from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.models.question_bank_question import QuestionBankQuestion
from edcraft_backend.repositories.base import EntityRepository


class QuestionBankRepository(EntityRepository[QuestionBank]):
    """Repository for QuestionBank entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionBank, db)

    async def get_by_id_with_questions(
        self,
        question_bank_id: UUID,
        include_deleted: bool = False,
    ) -> QuestionBank | None:
        """Get question bank by ID with all questions loaded.

        Args:
            question_bank_id: QuestionBank UUID
            include_deleted: Whether to include soft-deleted question banks

        Returns:
            QuestionBank with questions loaded and ordered, or None if not found
        """
        stmt = (
            select(QuestionBank)
            .where(QuestionBank.id == question_bank_id)
            .options(
                selectinload(QuestionBank.question_associations).selectinload(
                    QuestionBankQuestion.question
                )
            )
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(QuestionBank.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_folder(
        self,
        folder_id: UUID,
        include_deleted: bool = False,
    ) -> list[QuestionBank]:
        """Get all question banks in a folder.

        Args:
            folder_id: Folder UUID
            include_deleted: Whether to include soft-deleted question banks

        Returns:
            List of question banks in the folder ordered by last updated descending
        """
        stmt = (
            select(QuestionBank)
            .where(QuestionBank.folder_id == folder_id)
            .order_by(QuestionBank.updated_at.desc())
        )

        if not include_deleted:
            stmt = stmt.where(QuestionBank.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_soft_delete_by_folder_ids(self, folder_ids: list[UUID]) -> None:
        """Bulk soft-delete question banks by folder IDs.

        Args:
            folder_ids: List of folder UUIDs whose question banks should be soft-deleted
        """
        from datetime import UTC, datetime

        if not folder_ids:
            return

        stmt = (
            update(QuestionBank)
            .where(QuestionBank.folder_id.in_(folder_ids))
            .where(QuestionBank.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await self.db.execute(stmt)
        await self.db.flush()
