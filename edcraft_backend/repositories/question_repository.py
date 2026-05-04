from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from edcraft_backend.models.question import Question
from edcraft_backend.repositories.base import EntityRepository
from edcraft_backend.repositories.mixins.orderable import OrderableRepositoryMixin


class QuestionRepository(
    EntityRepository[Question],
    OrderableRepositoryMixin[Question],
):
    """Repository for Question entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Question, db)

    def _parent_filter(self, parent_id: UUID) -> ColumnElement[bool]:
        return Question.assessment_id == parent_id

    def _base_filters(self) -> tuple[ColumnElement[bool], ...]:
        return (Question.deleted_at.is_(None),)

    async def get_orphaned_questions(self, owner_id: UUID) -> list[Question]:
        """Get questions not in any assessment or question bank.

        Args:
            owner_id: User UUID to filter questions

        Returns:
            List of orphaned questions
        """
        stmt = select(Question).where(
            Question.owner_id == owner_id,
            Question.deleted_at.is_(None),
            Question.assessment_id.is_(None),
            Question.question_bank_id.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
