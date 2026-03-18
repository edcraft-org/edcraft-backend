from typing import Literal, cast
from uuid import UUID

from edcraft_backend.exceptions import (
    DataIntegrityError,
    ResourceNotFoundError,
    UnauthorizedAccessError,
    ValidationError,
)
from edcraft_backend.models.enums import CollaboratorRole
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.models.question_bank_question import QuestionBankQuestion
from edcraft_backend.models.question_data import MCQData, MRQData
from edcraft_backend.repositories.question_bank_question_repository import (
    QuestionBankQuestionRepository,
)
from edcraft_backend.repositories.question_bank_repository import QuestionBankRepository
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
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
from edcraft_backend.schemas.question_bank import (
    CreateQuestionBankRequest,
    QuestionBankMCQResponse,
    QuestionBankMRQResponse,
    QuestionBankQuestionResponse,
    QuestionBankShortAnswerResponse,
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
        question_bank_question_repository: QuestionBankQuestionRepository,
        question_service: QuestionService,
        collaborator_repository: ResourceCollaboratorRepository,
    ):
        self.question_bank_repo = question_bank_repository
        self.folder_svc = folder_svc
        self.assoc_repo = question_bank_question_repository
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
        """Soft delete a question bank and clean up orphaned questions.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID

        Returns:
            Soft-deleted question bank

        Raises:
            ResourceNotFoundError: If question bank not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        question_bank = await self.get_owned_question_bank(user_id, question_bank_id)

        assocs = await self.assoc_repo.get_all_for_question_bank(question_bank.id)
        for assoc in assocs:
            question = await self.question_svc.question_repo.get_by_id(assoc.question_id)
            if question:
                await self.question_svc.question_repo.soft_delete(question)

        deleted_question_bank = await self.question_bank_repo.soft_delete(question_bank)
        return deleted_question_bank

    def _build_question_bank_question_response(
        self, assoc: QuestionBankQuestion
    ) -> QuestionBankQuestionResponse:
        """Build the appropriate response type for a question bank question.

        Args:
            assoc: QuestionBankQuestion association

        Returns:
            QuestionBankQuestionResponse subtype based on question_type

        Raises:
            DataIntegrityError: If question type is unknown
        """
        q = assoc.question

        base_data = {
            "id": q.id,
            "owner_id": q.owner_id,
            "template_id": q.template_id,
            "linked_from_question_id": q.linked_from_question_id,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "created_at": q.created_at,
            "updated_at": q.updated_at,
            "added_at": assoc.added_at,
        }

        if q.question_type == "mcq":
            return QuestionBankMCQResponse.model_validate(
                {**base_data, "mcq_data": q.data}
            )
        elif q.question_type == "mrq":
            return QuestionBankMRQResponse.model_validate(
                {**base_data, "mrq_data": q.data}
            )
        elif q.question_type == "short_answer":
            return QuestionBankShortAnswerResponse.model_validate(
                {**base_data, "short_answer_data": q.data}
            )
        else:
            raise DataIntegrityError(f"Unknown question type: {q.question_type}")

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
        question_bank = await self.question_bank_repo.get_by_id_with_questions(
            question_bank_id
        )
        if not question_bank:
            raise ResourceNotFoundError("QuestionBank", str(question_bank_id))
        if question_bank.owner_id != user_id:
            raise UnauthorizedAccessError("QuestionBank", str(question_bank_id))

        # Filter out soft-deleted questions
        questions: list[QuestionBankQuestionResponse] = []
        for assoc in question_bank.question_associations:
            if assoc.question and assoc.question.deleted_at is None:
                question_response = self._build_question_bank_question_response(assoc)
                questions.append(question_response)

        return QuestionBankWithQuestionsResponse(
            id=question_bank.id,
            owner_id=question_bank.owner_id,
            folder_id=question_bank.folder_id,
            title=question_bank.title,
            description=question_bank.description,
            created_at=question_bank.created_at,
            updated_at=question_bank.updated_at,
            questions=questions,
        )

    async def _attach_question_to_question_bank(
        self,
        question_bank: QuestionBank,
        question_id: UUID,
    ) -> None:
        """Insert the association and expire the cached question bank."""
        assoc = QuestionBankQuestion(
            question_bank_id=question_bank.id,
            question_id=question_id,
        )
        await self.assoc_repo.create(assoc)
        self.question_bank_repo.db.expire(question_bank)

    async def _require_assoc_and_question(
        self,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> tuple[QuestionBankQuestion, Question]:
        """Fetch and validate the assoc + question, raising if either is missing."""
        assoc = await self.assoc_repo.find_association(question_bank_id, question_id)
        if not assoc:
            raise ResourceNotFoundError(
                "QuestionBankQuestion",
                f"question_bank={question_bank_id}, question={question_id}",
            )

        question = await self.question_svc.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundError("Question", str(question_id))

        return assoc, question

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
        await self._attach_question_to_question_bank(question_bank, question_entity.id)
        return await self.get_question_bank_with_questions(user_id, question_bank_id)

    async def link_question_to_question_bank(
        self,
        user_id: UUID,
        question_bank_id: UUID,
        question_id: UUID,
    ) -> QuestionBankWithQuestionsResponse:
        """Copy a question into a question bank, tracking the source via linked_from_question_id.

        The user must have at least VIEWER access to the source question. A new independent
        copy is created and linked to the question bank.

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

        source = await self.question_svc.question_repo.get_by_id(question_id)
        if not source:
            raise ResourceNotFoundError("Question", str(question_id))

        can_view = await self.collaborator_repo.check_question_permission(
            question_id, user_id, CollaboratorRole.VIEWER
        )
        if not can_view:
            raise UnauthorizedAccessError("Question", str(question_id))

        copy = await self.question_svc.copy_question(source, user_id)
        await self._attach_question_to_question_bank(question_bank, copy.id)
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
        _, question = await self._require_assoc_and_question(
            question_bank_id, question_id
        )

        if not question.linked_from_question_id:
            raise ValidationError("Question has no source link to sync from.")

        source = await self.question_svc.question_repo.get_by_id(
            question.linked_from_question_id
        )
        if not source:
            raise ResourceNotFoundError(
                "Question", str(question.linked_from_question_id)
            )

        can_view = await self.collaborator_repo.check_question_permission(
            source.id, user_id, CollaboratorRole.VIEWER
        )
        if not can_view:
            raise UnauthorizedAccessError("Question", str(source.id))

        _raw = source.data
        if isinstance(_raw, MCQData):
            _schema_data: MCQDataSchema | MRQDataSchema | ShortAnswerDataSchema = (
                MCQDataSchema.model_validate(_raw)
            )
        elif isinstance(_raw, MRQData):
            _schema_data = MRQDataSchema.model_validate(_raw)
        else:
            _schema_data = ShortAnswerDataSchema.model_validate(_raw)

        update_data = UpdateQuestionRequest(
            question_type=cast(
                Literal["mcq", "mrq", "short_answer"], source.question_type
            ),
            question_text=source.question_text,
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
        _, question = await self._require_assoc_and_question(
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
        """Remove a question from a question bank and clean up if orphaned.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_id: Question UUID

        Raises:
            ResourceNotFoundError: If association not found
            UnauthorizedAccessError: If user doesn't own the question bank
        """
        await self.get_owned_question_bank(user_id, question_bank_id)
        assoc, question = await self._require_assoc_and_question(question_bank_id, question_id)
        await self.assoc_repo.hard_delete(assoc)
        await self.question_svc.question_repo.soft_delete(question)
