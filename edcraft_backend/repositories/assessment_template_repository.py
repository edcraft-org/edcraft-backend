from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.repositories.base import EntityRepository


class AssessmentTemplateRepository(EntityRepository[AssessmentTemplate]):
    """Repository for AssessmentTemplate entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(AssessmentTemplate, db)

    async def get_by_id_with_templates(
        self,
        template_id: UUID,
        include_deleted: bool = False,
    ) -> AssessmentTemplate | None:
        """Get assessment template by ID with all question templates loaded.

        Args:
            template_id: Assessment template UUID
            include_deleted: Whether to include soft-deleted templates

        Returns:
            AssessmentTemplate with question templates loaded, or None if not found
        """
        from edcraft_backend.models.assessment_template_question_template import (
            AssessmentTemplateQuestionTemplate,
        )

        stmt = (
            select(AssessmentTemplate)
            .where(AssessmentTemplate.id == template_id)
            .options(
                selectinload(AssessmentTemplate.template_associations).selectinload(
                    AssessmentTemplateQuestionTemplate.question_template
                )
            )
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(AssessmentTemplate.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_folder(
        self,
        folder_id: UUID,
        include_deleted: bool = False,
    ) -> list[AssessmentTemplate]:
        """Get all assessment templates in a folder.

        Args:
            folder_id: Folder UUID
            include_deleted: Whether to include soft-deleted templates

        Returns:
            List of assessment templates in the folder ordered by last updated descending
        """
        stmt = (
            select(AssessmentTemplate)
            .where(AssessmentTemplate.folder_id == folder_id)
            .order_by(AssessmentTemplate.updated_at.desc())
        )

        if not include_deleted:
            stmt = stmt.where(AssessmentTemplate.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_root_templates(
        self,
        owner_id: UUID,
        include_deleted: bool = False,
    ) -> list[AssessmentTemplate]:
        """Get all root assessment templates (no folder) for a user.

        Args:
            owner_id: User UUID
            include_deleted: Whether to include soft-deleted templates

        Returns:
            List of root assessment templates order by last updated descending
        """
        stmt = (
            select(AssessmentTemplate)
            .where(
                AssessmentTemplate.owner_id == owner_id,
                AssessmentTemplate.folder_id.is_(None),
            )
            .order_by(AssessmentTemplate.updated_at.desc())
        )

        if not include_deleted:
            stmt = stmt.where(AssessmentTemplate.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_soft_delete_by_folder_ids(self, folder_ids: list[UUID]) -> None:
        """Bulk soft-delete assessment templates by folder IDs.

        Args:
            folder_ids: List of folder UUIDs whose templates should be soft-deleted
        """
        from datetime import UTC, datetime

        if not folder_ids:
            return

        stmt = (
            update(AssessmentTemplate)
            .where(AssessmentTemplate.folder_id.in_(folder_ids))
            .where(AssessmentTemplate.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await self.db.execute(stmt)
        await self.db.flush()
