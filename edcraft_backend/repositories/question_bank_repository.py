from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.enums import ResourceType
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.repositories.collaborative_resource_repository import (
    FolderResourceRepository,
)


class QuestionBankRepository(FolderResourceRepository[QuestionBank]):
    """Repository for QuestionBank entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionBank, ResourceType.QUESTION_BANK, db)

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
            .options(selectinload(QuestionBank.questions))
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(QuestionBank.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
