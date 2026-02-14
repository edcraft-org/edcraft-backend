from uuid import UUID

from sqlalchemy import select, union
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_bank_question import QuestionBankQuestion
from edcraft_backend.repositories.base import EntityRepository


class QuestionRepository(EntityRepository[Question]):
    """Repository for Question entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Question, db)

    async def get_orphaned_questions(
        self,
        owner_id: UUID,
    ) -> list[Question]:
        """Get questions not used in any non-deleted assessment or question bank.

        Args:
            owner_id: User UUID to filter questions

        Returns:
            List of orphaned questions
        """
        from edcraft_backend.models.assessment import Assessment
        from edcraft_backend.models.question_bank import QuestionBank

        # Subquery to get question IDs used in assessments
        used_in_assessments = (
            select(AssessmentQuestion.question_id)
            .join(Assessment, AssessmentQuestion.assessment_id == Assessment.id)
            .where(Assessment.deleted_at.is_(None))
        )

        # Subquery to get question IDs used in question banks
        used_in_question_banks = (
            select(QuestionBankQuestion.question_id)
            .join(
                QuestionBank, QuestionBankQuestion.question_bank_id == QuestionBank.id
            )
            .where(QuestionBank.deleted_at.is_(None))
        )

        # Combine both subqueries using union
        used_questions_subquery = union(
            used_in_assessments, used_in_question_banks
        ).subquery()

        # Get questions not in the combined used list
        stmt = select(Question).where(
            Question.owner_id == owner_id,
            Question.deleted_at.is_(None),
            Question.id.notin_(select(used_questions_subquery.c.question_id)),
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
