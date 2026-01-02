from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment_question import AssessmentQuestion
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
        """Get questions not used in any non-deleted assessment.

        Args:
            owner_id: User UUID to filter questions

        Returns:
            List of orphaned questions
        """
        from edcraft_backend.models.assessment import Assessment

        # Subquery to get question IDs that are in use
        used_questions_subquery = (
            select(AssessmentQuestion.question_id)
            .join(Assessment, AssessmentQuestion.assessment_id == Assessment.id)
            .where(Assessment.deleted_at.is_(None))
        )

        # Get questions not in the used list
        stmt = (
            select(Question)
            .where(
                Question.owner_id == owner_id,
                Question.deleted_at.is_(None),
                Question.id.notin_(used_questions_subquery),
            )
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
