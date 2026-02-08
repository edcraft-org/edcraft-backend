from uuid import UUID

from edcraft_backend.exceptions import ResourceNotFoundError, UnauthorizedAccessError
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.question import Question
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    UpdateQuestionRequest,
)


class QuestionService:
    """Service layer for Question business logic."""

    def __init__(
        self,
        question_repository: QuestionRepository,
        assessment_question_repository: AssessmentQuestionRepository,
    ):
        self.question_repo = question_repository
        self.assoc_repo = assessment_question_repository

    async def get_owned_question(self, user_id: UUID, question_id: UUID) -> Question:
        """Get question and verify ownership.

        Args:
            user_id: User UUID requesting resources
            question_id: Question UUID

        Returns:
            Question entity

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundError("Question", str(question_id))
        if question.owner_id != user_id:
            raise UnauthorizedAccessError("Question", str(question_id))
        return question

    async def create_question(
        self, user_id: UUID, question_data: CreateQuestionRequest
    ) -> Question:
        """Create a new question.

        Args:
            user_id: User UUID requesting resources
            question_data: Question creation data

        Returns:
            Created question
        """
        question = Question(owner_id=user_id, **question_data.model_dump())
        return await self.question_repo.create(question)

    async def list_questions(
        self,
        user_id: UUID | None = None,
    ) -> list[Question]:
        """List questions with optional filtering.

        Args:
            user_id: Filter by user UUID

        Returns:
            List of questions ordered by creation date
        """
        filters: dict[str, UUID] = {}
        if user_id:
            filters["owner_id"] = user_id

        return await self.question_repo.list(
            filters=filters if filters else None,
            order_by=Question.created_at.desc(),
        )

    async def get_question(self, user_id: UUID, question_id: UUID) -> Question:
        """Get a question by ID and verify ownership.

        Args:
            user_id: User UUID requesting resources
            question_id: Question UUID

        Returns:
            Question entity

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        return await self.get_owned_question(user_id, question_id)

    async def update_question(
        self,
        user_id: UUID,
        question_id: UUID,
        question_data: UpdateQuestionRequest,
    ) -> Question:
        """Update a question.

        Args:
            user_id: User UUID requesting resources
            question_id: Question UUID
            question_data: Question update data

        Returns:
            Updated question

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        question = await self.get_owned_question(user_id, question_id)
        update_data = question_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(question, key, value)

        return await self.question_repo.update(question)

    async def soft_delete_question(self, user_id: UUID, question_id: UUID) -> Question:
        """Soft delete a question.

        Args:
            user_id: User UUID requesting resources
            question_id: Question UUID

        Returns:
            Soft-deleted question

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        question = await self.get_owned_question(user_id, question_id)
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
        user_id: UUID,
        question_id: UUID,
    ) -> list[Assessment]:
        """Get all assessments that include this question.

        Args:
            user_id: User UUID requesting resources
            question_id: Question UUID

        Returns:
            List of assessments that include this question

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        await self.get_owned_question(user_id, question_id)
        return await self.assoc_repo.get_assessments_by_question_id(question_id)
