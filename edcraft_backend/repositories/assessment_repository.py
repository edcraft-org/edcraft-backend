from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.enums import ResourceType
from edcraft_backend.repositories.collaborative_resource_repository import FolderResourceRepository


class AssessmentRepository(FolderResourceRepository[Assessment]):
    """Repository for Assessment entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Assessment, ResourceType.ASSESSMENT, db)

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
        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(selectinload(Assessment.questions))
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(Assessment.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

