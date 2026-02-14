from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.models.question_bank_question import QuestionBankQuestion
from edcraft_backend.repositories.base import AssociationRepository


class QuestionBankQuestionRepository(AssociationRepository[QuestionBankQuestion]):
    """Repository for QuestionBankQuestion association operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(QuestionBankQuestion, db)

    async def find_association(
        self,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> QuestionBankQuestion | None:
        """Find association between question bank and question.

        Args:
            question_bank_id: QuestionBank UUID
            question_id: Question UUID

        Returns:
            QuestionBankQuestion association if found, None otherwise
        """
        stmt = select(QuestionBankQuestion).where(
            QuestionBankQuestion.question_bank_id == question_bank_id,
            QuestionBankQuestion.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_question_bank(
        self,
        question_bank_id: UUID,
    ) -> list[QuestionBankQuestion]:
        """Get all question associations for a question bank.

        Args:
            question_bank_id: QuestionBank UUID

        Returns:
            List of QuestionBankQuestion associations
        """
        stmt = select(QuestionBankQuestion).where(
            QuestionBankQuestion.question_bank_id == question_bank_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_question_banks_by_question_id(
        self,
        question_id: UUID,
    ) -> list[QuestionBank]:
        """Get all question banks that contain a specific question.

        Args:
            question_id: Question UUID

        Returns:
            List of QuestionBank objects that include this question
        """
        stmt = (
            select(QuestionBank)
            .join(
                QuestionBankQuestion,
                QuestionBank.id == QuestionBankQuestion.question_bank_id,
            )
            .where(QuestionBankQuestion.question_id == question_id)
            .order_by(QuestionBank.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
