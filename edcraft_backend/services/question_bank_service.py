from typing import Literal, cast
from uuid import UUID

from edcraft_backend.exceptions import (
    ResourceNotFoundError,
    UnauthorizedAccessError,
    ValidationError,
)
from edcraft_backend.models.enums import CollaboratorRole
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.repositories.question_bank_repository import QuestionBankRepository
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    MCQData,
    MRQData,
    ShortAnswerData,
    UpdateQuestionRequest,
)
from edcraft_backend.schemas.question_bank import (
    CreateQuestionBankRequest,
    QuestionBankWithQuestionsResponse,
    UpdateQuestionBankRequest,
)
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.question_service import QuestionService


class QuestionBankService:
    """Service layer for QuestionBank business logic."""

    def __init__(
        self,
        question_bank_repository: QuestionBankRepository,
        folder_svc: FolderService,
        question_service: QuestionService,
        collaborator_repository: ResourceCollaboratorRepository,
    ):
        self.question_bank_repo = question_bank_repository
        self.folder_svc = folder_svc
        self.question_svc = question_service
        self.collaborator_repo = collaborator_repository

    async def get_owned_question_bank(
        self, user_id: UUID, question_bank_id: UUID
    ) -> QuestionBank:
        """Get question bank and verify ownership.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID

        Returns:
            QuestionBank entity

        Raises:
            ResourceNotFoundError: If question bank not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        question_bank = await self.question_bank_repo.get_by_id(question_bank_id)
        if not question_bank:
            raise ResourceNotFoundError("QuestionBank", str(question_bank_id))
        if question_bank.owner_id != user_id:
            raise UnauthorizedAccessError("QuestionBank", str(question_bank_id))
        return question_bank

    async def create_question_bank(
        self, user_id: UUID, question_bank_data: CreateQuestionBankRequest
    ) -> QuestionBank:
        """Create a new question bank.

        Args:
            user_id: User UUID
            question_bank_data: Question bank creation data

        Returns:
            Created question bank

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If user doesn't own the folder
        """
        await self.folder_svc.get_owned_folder(user_id, question_bank_data.folder_id)

        question_bank = QuestionBank(
            owner_id=user_id, **question_bank_data.model_dump()
        )
        return await self.question_bank_repo.create(question_bank)

    async def list_question_banks(
        self,
        user_id: UUID,
        folder_id: UUID | None = None,
    ) -> list[QuestionBank]:
        """List question banks within folder or all user question banks.

        Args:
            user_id: User UUID
            folder_id: Folder UUID (None for ALL question banks owned by user)

        Returns:
            List of question banks ordered by updated_at descending

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If folder does not belong to user
        """
        if folder_id:
            await self.folder_svc.get_owned_folder(user_id, folder_id)
            question_banks = await self.question_bank_repo.get_by_folder(folder_id)
        else:
            question_banks = await self.question_bank_repo.list(
                filters={"owner_id": user_id},
                order_by=QuestionBank.updated_at.desc(),
            )

        return question_banks

    async def get_question_bank(
        self, user_id: UUID, question_bank_id: UUID
    ) -> QuestionBank:
        """Get a question bank by ID and verify ownership.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID

        Returns:
            QuestionBank entity

        Raises:
            ResourceNotFoundError: If question bank not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        return await self.get_owned_question_bank(user_id, question_bank_id)

    async def _get_question_bank_with_questions(
        self, user_id: UUID, question_bank_id: UUID
    ) -> QuestionBank:
        """Get question bank with all questions loaded.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID

        Returns:
            QuestionBank with questions

        Raises:
            ResourceNotFoundError: If question bank not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        question_bank = await self.question_bank_repo.get_by_id_with_questions(
            question_bank_id
        )
        if not question_bank:
            raise ResourceNotFoundError("QuestionBank", str(question_bank_id))
        if question_bank.owner_id != user_id:
            raise UnauthorizedAccessError("QuestionBank", str(question_bank_id))
        return question_bank

    async def get_question_bank_with_questions(
        self, user_id: UUID, question_bank_id: UUID
    ) -> QuestionBankWithQuestionsResponse:
        """Get question bank with all questions loaded.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID

        Returns:
            QuestionBank with questions

        Raises:
            ResourceNotFoundError: If question bank not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        question_bank = await self._get_question_bank_with_questions(
            user_id, question_bank_id
        )
        return QuestionBankWithQuestionsResponse.model_validate(question_bank)

    async def update_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question_bank_data: UpdateQuestionBankRequest,
    ) -> QuestionBank:
        """Update a question bank.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_bank_data: QuestionBank update data

        Returns:
            Updated question bank

        Raises:
            ResourceNotFoundError: If question bank or folder not found
            UnauthorizedAccessError: If user doesn't own resources
        """
        question_bank = await self.get_owned_question_bank(user_id, question_bank_id)
        update_data = question_bank_data.model_dump(exclude_unset=True)

        if "folder_id" in update_data and update_data["folder_id"]:
            await self.folder_svc.get_owned_folder(user_id, update_data["folder_id"])

        for key, value in update_data.items():
            setattr(question_bank, key, value)

        return await self.question_bank_repo.update(question_bank)

    async def soft_delete_question_bank(
        self, user_id: UUID, question_bank_id: UUID
    ) -> QuestionBank:
        """Soft delete a question bank and its questions.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID

        Returns:
            Soft-deleted question bank

        Raises:
            ResourceNotFoundError: If question bank not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        question_bank = await self._get_question_bank_with_questions(
            user_id, question_bank_id
        )
        for question in question_bank.questions:
            question.question_bank_id = None
            await self.question_svc.question_repo.update(question)
            await self.question_svc.question_repo.soft_delete(question)
        return await self.question_bank_repo.soft_delete(question_bank)

    async def _attach_question_to_question_bank(
        self,
        question_bank: QuestionBank,
        question: Question,
    ) -> None:
        """Set the question's question_bank FK."""
        question.question_bank_id = question_bank.id
        await self.question_svc.question_repo.update(question)
        self.question_bank_repo.db.expire(question_bank)

    async def _require_question_in_question_bank(
        self,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> Question:
        """Fetch question and verify it belongs to the given question bank."""
        question = await self.question_svc.question_repo.get_by_id(question_id)
        if not question or question.question_bank_id != question_bank_id:
            raise ResourceNotFoundError(
                "Question",
                f"question_bank={question_bank_id}, question={question_id}",
            )
        return question

    async def add_question_to_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question: CreateQuestionRequest,
    ) -> QuestionBankWithQuestionsResponse:
        """Add a question to a question bank.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question: QuestionCreate object

        Returns:
            Updated question bank with questions

        Raises:
            ResourceNotFoundError: If question bank or question not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        question_bank = await self.get_owned_question_bank(user_id, question_bank_id)
        question_entity = await self.question_svc.create_question(user_id, question)
        await self._attach_question_to_question_bank(question_bank, question_entity)
        return await self.get_question_bank_with_questions(user_id, question_bank_id)

    async def link_question_to_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> QuestionBankWithQuestionsResponse:
        """Copy a question into a question bank, and link to source question.

        The user must have at least VIEWER access to the source question.
        A new independent copy is created and linked to the question bank.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_id: UUID of the source question to copy

        Returns:
            Updated question bank with questions

        Raises:
            ResourceNotFoundError: If question bank or question not found
            UnauthorizedAccessError: If user doesn't own the question bank
                or lacks view access on the source question
        """
        question_bank = await self.get_owned_question_bank(user_id, question_bank_id)
        source_question = await self.question_svc.get_question(
            user_id, question_id, min_role=CollaboratorRole.VIEWER
        )

        copy = await self.question_svc.copy_question(source_question, user_id)
        await self._attach_question_to_question_bank(question_bank, copy)
        return await self.get_question_bank_with_questions(user_id, question_bank_id)

    async def sync_question_in_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> QuestionBankWithQuestionsResponse:
        """Sync a linked question's content from its source question.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_id: UUID of the question copy in this question bank

        Returns:
            Updated question bank with questions

        Raises:
            ResourceNotFoundError: If question bank, question, or source not found
            ValidationError: If question has no source link
            UnauthorizedAccessError:
                If user doesn't own the question bank or lacks view access on source
        """
        await self.get_owned_question_bank(user_id, question_bank_id)
        question = await self._require_question_in_question_bank(
            question_bank_id, question_id
        )

        if not question.linked_from_question_id:
            raise ValidationError("Question has no source link to sync from.")

        source_question = await self.question_svc.get_question(
            user_id, question.linked_from_question_id, min_role=CollaboratorRole.VIEWER
        )

        if source_question.question_type == "mcq":
            _schema_data: MCQData | MRQData | ShortAnswerData = MCQData.model_validate(
                source_question.data
            )
        elif source_question.question_type == "mrq":
            _schema_data = MRQData.model_validate(source_question.data)
        else:
            _schema_data = ShortAnswerData.model_validate(source_question.data)

        update_data = UpdateQuestionRequest(
            question_type=cast(
                Literal["mcq", "mrq", "short_answer"], source_question.question_type
            ),
            question_text=source_question.question_text,
            data=_schema_data,
        )
        await self.question_svc._update_question_data(question, update_data)

        return await self.get_question_bank_with_questions(user_id, question_bank_id)

    async def unlink_question_in_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> QuestionBankWithQuestionsResponse:
        """Sever the source link on a question without removing it from the question bank.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_id: UUID of the question in this question bank

        Returns:
            Updated question bank with questions

        Raises:
            ResourceNotFoundError: If question bank or question not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        await self.get_owned_question_bank(user_id, question_bank_id)
        question = await self._require_question_in_question_bank(
            question_bank_id, question_id
        )

        question.linked_from_question_id = None
        await self.question_svc.question_repo.update(question)

        return await self.get_question_bank_with_questions(user_id, question_bank_id)

    async def remove_question_from_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> None:
        """Remove a question from a question bank and soft-delete it.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_id: Question UUID

        Raises:
            ResourceNotFoundError: If question not found in question bank
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        await self.get_owned_question_bank(user_id, question_bank_id)
        question = await self._require_question_in_question_bank(
            question_bank_id, question_id
        )

        question.question_bank_id = None
        await self.question_svc.question_repo.update(question)
        await self.question_svc.question_repo.soft_delete(question)
