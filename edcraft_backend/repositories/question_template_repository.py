from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.repositories.base import EntityRepository
from edcraft_backend.repositories.mixins.orderable import OrderableRepositoryMixin


class QuestionTemplateRepository(
    EntityRepository[QuestionTemplate],
    OrderableRepositoryMixin[QuestionTemplate],
):
    """Repository for QuestionTemplate entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionTemplate, db)

    def _parent_filter(self, parent_id: UUID) -> ColumnElement[bool]:
        return QuestionTemplate.assessment_template_id == parent_id

    def _base_filters(self) -> tuple[ColumnElement[bool], ...]:
        return (QuestionTemplate.deleted_at.is_(None),)

    async def get_orphaned_templates(self, owner_id: UUID) -> list[QuestionTemplate]:
        """Get question templates not in any active container.

        Args:
            owner_id: User UUID to filter templates

        Returns:
            List of orphaned question templates
        """
        stmt = select(QuestionTemplate).where(
            QuestionTemplate.owner_id == owner_id,
            QuestionTemplate.deleted_at.is_(None),
            QuestionTemplate.assessment_template_id.is_(None),
            QuestionTemplate.question_template_bank_id.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
