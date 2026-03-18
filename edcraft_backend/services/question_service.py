from typing import TypedDict
from uuid import UUID

from edcraft_backend.exceptions import ResourceNotFoundError, UnauthorizedAccessError
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.enums import CollaboratorRole
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.models.question_data import MCQData, MRQData, ShortAnswerData
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from edcraft_backend.repositories.question_bank_question_repository import (
    QuestionBankQuestionRepository,
)
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.schemas.question import (
    CreateMCQRequest,
    CreateMRQRequest,
    CreateQuestionRequest,
    CreateShortAnswerRequest,
    UpdateQuestionRequest,
)
from edcraft_backend.schemas.question import (
    MCQData as MCQDataSchema,
)
from edcraft_backend.schemas.question import (
    MRQData as MRQDataSchema,
)
from edcraft_backend.schemas.question import (
    ShortAnswerData as ShortAnswerDataSchema,
)


class QuestionUsageDict(TypedDict):
    """Dict type for question usage."""

    assessments: list[Assessment]
    question_banks: list[QuestionBank]


class QuestionService:
    """Service layer for Question business logic."""

    def __init__(
        self,
        question_repository: QuestionRepository,
        assessment_question_repository: AssessmentQuestionRepository,
        question_bank_question_repository: QuestionBankQuestionRepository,
        collaborator_repository: ResourceCollaboratorRepository,
    ):
        self.question_repo = question_repository
        self.assessment_assoc_repo = assessment_question_repository
        self.question_bank_assoc_repo = question_bank_question_repository
        self.collaborator_repo = collaborator_repository

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
            Created question with related data

        """
        question = Question(
            owner_id=user_id,
            template_id=question_data.template_id,
            question_type=question_data.question_type,
            question_text=question_data.question_text,
        )

        if isinstance(question_data, CreateMCQRequest):
            question.mcq_data = MCQData(
                options=question_data.data.options,
                correct_index=question_data.data.correct_index,
            )
        elif isinstance(question_data, CreateMRQRequest):
            question.mrq_data = MRQData(
                options=question_data.data.options,
                correct_indices=question_data.data.correct_indices,
            )
        elif isinstance(question_data, CreateShortAnswerRequest):
            question.short_answer_data = ShortAnswerData(
                correct_answer=question_data.data.correct_answer,
            )

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
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundError("Question", str(question_id))

        if question.owner_id != user_id:
            can_edit = await self.collaborator_repo.check_question_permission(
                question_id, user_id, CollaboratorRole.EDITOR
            )
            if not can_edit:
                raise UnauthorizedAccessError("Question", str(question_id))

        return await self._update_question_data(question, question_data)

    async def _update_question_data(
        self, question: Question, question_data: UpdateQuestionRequest
    ) -> Question:
        if question_data.question_text is not None:
            question.question_text = question_data.question_text

        # If changing type, clear old data and update question_type
        if (
            question_data.question_type is not None
            and question_data.question_type != question.question_type
        ):
            question.question_type = question_data.question_type
            question.mcq_data = None
            question.mrq_data = None
            question.short_answer_data = None

        # Update or create data
        if question_data.data is not None:
            if isinstance(question_data.data, MCQDataSchema):
                if question.mcq_data:
                    question.mcq_data.options = question_data.data.options
                    question.mcq_data.correct_index = question_data.data.correct_index
                else:
                    question.mcq_data = MCQData(
                        options=question_data.data.options,
                        correct_index=question_data.data.correct_index,
                    )
            elif isinstance(question_data.data, MRQDataSchema):
                if question.mrq_data:
                    question.mrq_data.options = question_data.data.options
                    question.mrq_data.correct_indices = (
                        question_data.data.correct_indices
                    )
                else:
                    question.mrq_data = MRQData(
                        options=question_data.data.options,
                        correct_indices=question_data.data.correct_indices,
                    )
            elif isinstance(question_data.data, ShortAnswerDataSchema):
                if question.short_answer_data:
                    question.short_answer_data.correct_answer = (
                        question_data.data.correct_answer
                    )
                else:
                    question.short_answer_data = ShortAnswerData(
                        correct_answer=question_data.data.correct_answer,
                    )

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

    async def copy_question(self, source: Question, new_owner_id: UUID) -> Question:
        """Create an independent copy of a question owned by new_owner_id.

        Args:
            source: Source question to copy
            new_owner_id: User UUID who will own the copy

        Returns:
            Newly created Question with linked_from_question_id set to source.id
        """
        copy = Question(
            owner_id=new_owner_id,
            template_id=source.template_id,
            question_type=source.question_type,
            question_text=source.question_text,
            linked_from_question_id=source.id,
        )

        if source.question_type == "mcq" and source.mcq_data:
            copy.mcq_data = MCQData(
                options=list(source.mcq_data.options),
                correct_index=source.mcq_data.correct_index,
            )
        elif source.question_type == "mrq" and source.mrq_data:
            copy.mrq_data = MRQData(
                options=list(source.mrq_data.options),
                correct_indices=list(source.mrq_data.correct_indices),
            )
        elif source.question_type == "short_answer" and source.short_answer_data:
            copy.short_answer_data = ShortAnswerData(
                correct_answer=source.short_answer_data.correct_answer,
            )

        return await self.question_repo.create(copy)

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

    async def get_question_usage(
        self,
        user_id: UUID,
        question_id: UUID,
    ) -> QuestionUsageDict:
        """Get all assessments that include this question.

        Args:
            user_id: User UUID requesting resources
            question_id: Question UUID

        Returns:
            Dict containing lists of associated resources

        Raises:
            ResourceNotFoundError: If question not found
            UnauthorizedAccessError: If user doesn't own the question
        """
        await self.get_owned_question(user_id, question_id)
        assessments = await self.assessment_assoc_repo.get_assessments_by_question_id(
            question_id
        )
        question_banks = (
            await self.question_bank_assoc_repo.get_question_banks_by_question_id(
                question_id
            )
        )
        return {"assessments": assessments, "question_banks": question_banks}
