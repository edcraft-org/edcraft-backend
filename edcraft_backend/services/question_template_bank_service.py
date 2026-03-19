from uuid import UUID

from edcraft_backend.exceptions import (
    ResourceNotFoundError,
    UnauthorizedAccessError,
    ValidationError,
)
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.repositories.question_template_bank_repository import (
    QuestionTemplateBankRepository,
)
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.schemas.question_template import CreateQuestionTemplateRequest
from edcraft_backend.schemas.question_template_bank import (
    CreateQuestionTemplateBankRequest,
    QuestionTemplateBankWithTemplatesResponse,
    UpdateQuestionTemplateBankRequest,
)
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.question_template_service import QuestionTemplateService


class QuestionTemplateBankService:
    """Service layer for QuestionTemplateBank business logic."""

    def __init__(
        self,
        question_template_bank_repository: QuestionTemplateBankRepository,
        folder_svc: FolderService,
        question_template_repository: QuestionTemplateRepository,
        question_template_service: QuestionTemplateService,
    ):
        self.question_template_bank_repo = question_template_bank_repository
        self.folder_svc = folder_svc
        self.qt_repo = question_template_repository
        self.question_template_svc = question_template_service

    async def get_owned_question_template_bank(
        self, user_id: UUID, question_template_bank_id: UUID
    ) -> QuestionTemplateBank:
        """Get question template bank and verify ownership.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID

        Returns:
            QuestionTemplateBank entity

        Raises:
            ResourceNotFoundError: If question template bank not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        question_template_bank = await self.question_template_bank_repo.get_by_id(
            question_template_bank_id
        )
        if not question_template_bank:
            raise ResourceNotFoundError(
                "QuestionTemplateBank", str(question_template_bank_id)
            )
        if question_template_bank.owner_id != user_id:
            raise UnauthorizedAccessError(
                "QuestionTemplateBank", str(question_template_bank_id)
            )
        return question_template_bank

    async def create_question_template_bank(
        self,
        user_id: UUID,
        question_template_bank_data: CreateQuestionTemplateBankRequest,
    ) -> QuestionTemplateBank:
        """Create a new question template bank.

        Args:
            user_id: User UUID
            question_template_bank_data: Question template bank creation data

        Returns:
            Created question template bank

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If user doesn't own the folder
        """
        await self.folder_svc.get_owned_folder(
            user_id, question_template_bank_data.folder_id
        )

        question_template_bank = QuestionTemplateBank(
            owner_id=user_id, **question_template_bank_data.model_dump()
        )
        return await self.question_template_bank_repo.create(question_template_bank)

    async def list_question_template_banks(
        self,
        user_id: UUID,
        folder_id: UUID | None = None,
    ) -> list[QuestionTemplateBank]:
        """List question template banks within folder or all user banks.

        Args:
            user_id: User UUID
            folder_id: Folder UUID (None for ALL banks owned by user)

        Returns:
            List of question template banks ordered by updated_at descending

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If folder does not belong to user
        """
        if folder_id:
            await self.folder_svc.get_owned_folder(user_id, folder_id)
            question_template_banks = (
                await self.question_template_bank_repo.get_by_folder(folder_id)
            )
        else:
            question_template_banks = await self.question_template_bank_repo.list(
                filters={"owner_id": user_id},
                order_by=QuestionTemplateBank.updated_at.desc(),
            )
        return question_template_banks

    async def get_question_template_bank(
        self, user_id: UUID, question_template_bank_id: UUID
    ) -> QuestionTemplateBank:
        """Get a question template bank by ID and verify ownership.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID

        Returns:
            QuestionTemplateBank entity

        Raises:
            ResourceNotFoundError: If question template bank not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        return await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )

    async def _get_question_template_bank_with_templates(
        self, user_id: UUID, question_template_bank_id: UUID
    ) -> QuestionTemplateBank:
        """Get question template bank with all templates loaded.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID

        Returns:
            QuestionTemplateBank with templates

        Raises:
            ResourceNotFoundError: If question template bank not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        question_template_bank = (
            await self.question_template_bank_repo.get_by_id_with_templates(
                question_template_bank_id
            )
        )
        if not question_template_bank:
            raise ResourceNotFoundError(
                "QuestionTemplateBank", str(question_template_bank_id)
            )
        if question_template_bank.owner_id != user_id:
            raise UnauthorizedAccessError(
                "QuestionTemplateBank", str(question_template_bank_id)
            )
        return question_template_bank

    async def get_question_template_bank_with_templates(
        self, user_id: UUID, question_template_bank_id: UUID
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Get question template bank with all templates loaded.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID

        Returns:
            QuestionTemplateBank with templates

        Raises:
            ResourceNotFoundError: If question template bank not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        question_template_bank = await self._get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )
        return QuestionTemplateBankWithTemplatesResponse.model_validate(
            question_template_bank
        )

    async def update_question_template_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template_bank_data: UpdateQuestionTemplateBankRequest,
    ) -> QuestionTemplateBank:
        """Update a question template bank.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID
            question_template_bank_data: QuestionTemplateBank update data

        Returns:
            Updated question template bank

        Raises:
            ResourceNotFoundError: If question template bank or folder not found
            UnauthorizedAccessError: If user doesn't own resources
        """
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )
        update_data = question_template_bank_data.model_dump(exclude_unset=True)

        if "folder_id" in update_data and update_data["folder_id"]:
            await self.folder_svc.get_owned_folder(user_id, update_data["folder_id"])

        for key, value in update_data.items():
            setattr(question_template_bank, key, value)

        return await self.question_template_bank_repo.update(question_template_bank)

    async def soft_delete_question_template_bank(
        self, user_id: UUID, question_template_bank_id: UUID
    ) -> QuestionTemplateBank:
        """Soft delete a question template bank and clean up orphaned templates.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID

        Returns:
            Soft-deleted question template bank

        Raises:
            ResourceNotFoundError: If question template bank not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        question_template_bank = await self._get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )
        for qt in question_template_bank.question_templates:
            qt.question_template_bank_id = None
            await self.qt_repo.update(qt)
            await self.qt_repo.soft_delete(qt)
        return await self.question_template_bank_repo.soft_delete(
            question_template_bank
        )

    async def _attach_qt_to_qt_bank(
        self,
        question_template_bank: QuestionTemplateBank,
        question_template: QuestionTemplate,
    ) -> None:
        """Set the question template's question_template_bank FK."""
        question_template.question_template_bank_id = question_template_bank.id
        await self.qt_repo.update(question_template)
        self.question_template_bank_repo.db.expire(question_template_bank)

    async def _require_question_template_in_bank(
        self, qt_bank_id: UUID, qt_id: UUID
    ) -> QuestionTemplate:
        """Fetch question template and verify it belongs to the given bank."""
        qt = await self.qt_repo.get_by_id(qt_id)
        if not qt or qt.question_template_bank_id != qt_bank_id:
            raise ResourceNotFoundError(
                "QuestionTemplate",
                f"question_template_bank={qt_bank_id}, question_template={qt_id}",
            )
        return qt

    async def add_question_template_to_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template: CreateQuestionTemplateRequest,
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Add a new question template to a question template bank."""
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )
        template_entity = await self.question_template_svc.create_template(
            user_id, question_template
        )
        await self._attach_qt_to_qt_bank(question_template_bank, template_entity)
        return await self.get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )

    async def link_question_template_to_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template_id: UUID,
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Copy a question template into a question template bank.
        Link to source question template.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID
            question_template_id: QuestionTemplate UUID

        Returns:
            Updated question template bank with templates

        Raises:
            ResourceNotFoundError: If bank or template not found
            DuplicateResourceError: If template already linked to bank
            UnauthorizedAccessError: If user doesn't own resources
        """
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )
        source = await self.question_template_svc.get_owned_template(
            user_id, question_template_id
        )

        copy = await self.question_template_svc.copy_question_template(source, user_id)
        await self._attach_qt_to_qt_bank(question_template_bank, copy)
        return await self.get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )

    async def remove_question_template_from_bank(
        self,
        user_id: UUID,
        qt_bank_id: UUID,
        qt_id: UUID,
    ) -> None:
        """Remove a question from a question bank and soft-delete it.

        Args:
            user_id: User UUID
            question_bank_id: QuestionBank UUID
            question_id: Question UUID

        Raises:
            ResourceNotFoundError: If question template not found in bank
            UnauthorizedAccessError: If user doesn't own the bank
        """
        await self.get_owned_question_template_bank(user_id, qt_bank_id)
        qt = await self._require_question_template_in_bank(qt_bank_id, qt_id)

        qt.question_template_bank_id = None
        await self.qt_repo.update(qt)
        await self.qt_repo.soft_delete(qt)

    async def sync_question_template_in_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template_id: UUID,
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Sync a linked question template's content from its source template.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID
            question_template_id: UUID of the question template copy in this bank

        Returns:
            Updated bank with question templates

        Raises:
            ResourceNotFoundError: If bank, template, or source not found
            ValidationError: If template has no source link
            UnauthorizedAccessError: If user doesn't own the bank
        """
        await self.get_owned_question_template_bank(user_id, question_template_bank_id)
        qt = await self._require_question_template_in_bank(
            question_template_bank_id, question_template_id
        )

        if not qt.linked_from_template_id:
            raise ValidationError("Question template has no source link to sync from.")

        source = await self.question_template_svc.get_template(
            user_id, qt.linked_from_template_id
        )
        await self.question_template_svc.sync_template(qt, source)

        return await self.get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )

    async def unlink_question_template_in_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template_id: UUID,
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Remove the source link from a question template copy (make it independent).

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID
            question_template_id: UUID of the question template copy

        Returns:
            Updated bank with question templates
        """
        await self.get_owned_question_template_bank(user_id, question_template_bank_id)
        qt = await self._require_question_template_in_bank(
            question_template_bank_id, question_template_id
        )

        qt.linked_from_template_id = None
        await self.qt_repo.update(qt)

        return await self.get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )
