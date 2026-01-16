from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.repositories.base import AssociationRepository


class AssessmentQuestionRepository(AssociationRepository[AssessmentQuestion]):
    """Repository for AssessmentQuestion association operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(AssessmentQuestion, db)

    async def find_association(
        self,
        assessment_id: UUID,
        question_id: UUID,
    ) -> AssessmentQuestion | None:
        """Find association between assessment and question.

        Args:
            assessment_id: Assessment UUID
            question_id: Question UUID

        Returns:
            AssessmentQuestion association if found, None otherwise
        """
        stmt = select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentQuestion.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_count(self, assessment_id: UUID) -> int:
        """Get the count of questions in an assessment.

        Args:
            assessment_id: Assessment UUID

        Returns:
            Count of questions
        """
        stmt = (
            select(func.count(AssessmentQuestion.id))
            .where(AssessmentQuestion.assessment_id == assessment_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_all_for_assessment(
        self,
        assessment_id: UUID,
    ) -> list[AssessmentQuestion]:
        """Get all question associations for an assessment, ordered by order field.

        Args:
            assessment_id: Assessment UUID

        Returns:
            List of AssessmentQuestion associations ordered by order field
        """
        stmt = (
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def shift_orders_from(self, assessment_id: UUID, start_order: int) -> None:
        """Shift order values up by 1 for all questions at or after start_order.

        Args:
            assessment_id: Assessment UUID
            start_order: Order value to start shifting from (inclusive)
        """
        # Get all associations that need shifting, ordered by order DESC
        stmt = (
            select(AssessmentQuestion)
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.order >= start_order,
            )
            .order_by(AssessmentQuestion.order.desc())
        )
        result = await self.db.execute(stmt)
        associations = list(result.scalars().all())

        # Update in descending order to avoid constraint violations
        for assoc in associations:
            assoc.order += 1
            await self.update(assoc)

        await self.db.flush()

    async def normalize_orders(self, assessment_id: UUID) -> None:
        """Normalize order values to consecutive integers starting from 0.

        Renumbers all questions in an assessment to have consecutive order values
        (0, 1, 2, 3...) based on their current order and added_at timestamp.

        Args:
            assessment_id: Assessment UUID
        """
        associations = await self.get_all_for_assessment(assessment_id)

        for idx, assoc in enumerate(associations):
            if assoc.order != idx:
                assoc.order = idx
                await self.update(assoc)

        await self.db.flush()

    async def get_assessments_by_question_id(
        self,
        question_id: UUID,
    ) -> list[Assessment]:
        """Get all assessments that contain a specific question.

        Args:
            question_id: Question UUID

        Returns:
            List of Assessment objects that include this question
        """
        stmt = (
            select(Assessment)
            .join(AssessmentQuestion, Assessment.id == AssessmentQuestion.assessment_id)
            .where(AssessmentQuestion.question_id == question_id)
            .order_by(Assessment.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
