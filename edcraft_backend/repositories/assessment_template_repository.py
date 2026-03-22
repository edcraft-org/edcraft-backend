from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.enums import ResourceType
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.repositories.collaborative_resource_repository import (
    FolderResourceRepository,
)


class AssessmentTemplateRepository(FolderResourceRepository[AssessmentTemplate]):
    """Repository for AssessmentTemplate entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(AssessmentTemplate, ResourceType.ASSESSMENT_TEMPLATE, db)

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
        stmt = (
            select(AssessmentTemplate)
            .where(AssessmentTemplate.id == template_id)
            .options(
                selectinload(AssessmentTemplate.question_templates).selectinload(
                    QuestionTemplate.target_elements
                )
            )
            .execution_options(populate_existing=True)
        )

        if not include_deleted:
            stmt = stmt.where(AssessmentTemplate.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
