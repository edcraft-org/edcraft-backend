from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.assessment import Assessment
from edcraft_backend.repositories.base import EntityRepository


class AssessmentRepository(EntityRepository[Assessment]):
    """Repository for Assessment entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Assessment, db)

    async def get_by_id_with_questions(
        self,
        assessment_id: UUID,
        include_deleted: bool = False,
    ) -> Assessment | None:
        """Get assessment by ID with all questions loaded.

        Args:
            assessment_id: Assessment UUID
            include_deleted: Whether to include soft-deleted assessments

        Returns:
            Assessment with questions loaded and ordered, or None if not found
        """
        from edcraft_backend.models.assessment_question import AssessmentQuestion

        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(
                selectinload(Assessment.question_associations).selectinload(
                    AssessmentQuestion.question
                )
            )
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(Assessment.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_folder(
        self,
        folder_id: UUID,
        include_deleted: bool = False,
    ) -> list[Assessment]:
        """Get all assessments in a folder.

        Args:
            folder_id: Folder UUID
            include_deleted: Whether to include soft-deleted assessments

        Returns:
            List of assessments in the folder ordered by last updated descending
        """
        stmt = (
            select(Assessment)
            .where(Assessment.folder_id == folder_id)
            .order_by(Assessment.updated_at.desc())
        )

        if not include_deleted:
            stmt = stmt.where(Assessment.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_soft_delete_by_folder_ids(self, folder_ids: list[UUID]) -> None:
        """Bulk soft-delete assessments by folder IDs.

        Args:
            folder_ids: List of folder UUIDs whose assessments should be soft-deleted
        """
        from datetime import UTC, datetime

        if not folder_ids:
            return

        stmt = (
            update(Assessment)
            .where(Assessment.folder_id.in_(folder_ids))
            .where(Assessment.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await self.db.execute(stmt)
        await self.db.flush()
