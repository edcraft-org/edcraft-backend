from uuid import UUID

from edcraft_backend.exceptions import ResourceNotFoundError, UnauthorizedAccessError
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.question import Question
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.schemas.question import QuestionCreate, QuestionUpdate


class QuestionService:
    """Service layer for Question business logic."""

    def __init__(
        self,
        question_repository: QuestionRepository,
        assessment_question_repository: AssessmentQuestionRepository,
    ):
        self.question_repo = question_repository
        self.assoc_repo = assessment_question_repository

    async def create_question(self, question_data: QuestionCreate) -> Question:
        """Create a new question.

        Args:
            question_data: Question creation data

        Returns:
            Created question
        """
        question = Question(**question_data.model_dump())
        return await self.question_repo.create(question)

    async def list_questions(
        self,
        owner_id: UUID | None = None,
    ) -> list[Question]:
        """List questions with optional filtering.

        Args:
            owner_id: Filter by owner

        Returns:
            List of questions ordered by creation date
        """
        filters: dict[str, UUID] = {}
        if owner_id:
            filters["owner_id"] = owner_id

        return await self.question_repo.list(
            filters=filters if filters else None,
            order_by=Question.created_at.desc(),
        )

    async def get_question(self, question_id: UUID) -> Question:
        """Get a question by ID.

        Args:
            question_id: Question UUID

        Returns:
            Question entity

        Raises:
            ResourceNotFoundError: If question not found
        """
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundError("Question", str(question_id))
        return question

    async def update_question(
        self,
        question_id: UUID,
        question_data: QuestionUpdate,
    ) -> Question:
        """Update a question.

        Args:
            question_id: Question UUID
            question_data: Question update data

        Returns:
            Updated question

        Raises:
            ResourceNotFoundError: If question not found
        """
        question = await self.get_question(question_id)
        update_data = question_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(question, key, value)

        return await self.question_repo.update(question)

    async def soft_delete_question(self, question_id: UUID) -> Question:
        """Soft delete a question.

        Args:
            question_id: Question UUID

        Returns:
            Soft-deleted question

        Raises:
            ResourceNotFoundError: If question not found
        """
        question = await self.get_question(question_id)
        return await self.question_repo.soft_delete(question)

    async def cleanup_orphaned_questions(self, owner_id: UUID) -> int:
        """Delete questions not used in any active assessment.

        Args:
            owner_id: User UUID

        Returns:
            Number of questions deleted
        """
        orphaned = await self.question_repo.get_orphaned_questions(owner_id)
        count = 0

        for question in orphaned:
            await self.question_repo.soft_delete(question)
            count += 1

        return count

    async def get_assessments_for_question(
        self,
        question_id: UUID,
        requesting_user_id: UUID,
    ) -> list[Assessment]:
        """Get all assessments that include this question.

        Args:
            question_id: Question UUID
            requesting_user_id: User UUID making the request

        Returns:
            List of assessments that include this question

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        question = await self.get_question(question_id)
        if question.owner_id != requesting_user_id:
            raise UnauthorizedAccessError("Question", str(question_id))

        return await self.assoc_repo.get_assessments_by_question_id(question_id)
