from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question import Question
from edcraft_backend.repositories.base import EntityRepository


class QuestionRepository(EntityRepository[Question]):
    """Repository for Question entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Question, db)

    async def get_orphaned_questions(
        self,
        owner_id: UUID,
    ) -> list[Question]:
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

    async def shift_orders_from(
        self,
        assessment_id: UUID,
        start_order: int,
    ) -> None:
        """Increment order by 1 for all questions at or after start_order in an assessment.

        Args:
            assessment_id: Assessment UUID
            start_order: Order value to start shifting from (inclusive)
        """
        stmt = (
            select(Question)
            .where(
                Question.assessment_id == assessment_id,
                Question.order >= start_order,
            )
            .order_by(Question.order.desc())
        )
        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())

        for question in questions:
            if question.order is not None:
                question.order += 1
                await self.update(question)

        await self.db.flush()

    async def normalize_orders(self, assessment_id: UUID) -> None:
        """Normalize order values to consecutive integers starting from 0.

        Args:
            assessment_id: Assessment UUID
        """
        stmt = (
            select(Question)
            .where(
                Question.assessment_id == assessment_id,
                Question.deleted_at.is_(None),
            )
            .order_by(Question.order)
        )
        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())
        for idx, question in enumerate(questions):
            question.order = idx
        await self.db.flush()
