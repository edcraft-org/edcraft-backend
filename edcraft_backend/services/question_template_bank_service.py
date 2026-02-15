from uuid import UUID

from edcraft_backend.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
    UnauthorizedAccessError,
)
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.models.question_template_bank_question_template import (
    QuestionTemplateBankQuestionTemplate,
)
from edcraft_backend.repositories.question_template_bank_question_template_repository import (
    QuestionTemplateBankQuestionTemplateRepository,
)
from edcraft_backend.repositories.question_template_bank_repository import (
    QuestionTemplateBankRepository,
)
from edcraft_backend.schemas.question_template import CreateQuestionTemplateRequest
from edcraft_backend.schemas.question_template_bank import (
    CreateQuestionTemplateBankRequest,
    QuestionTemplateBankQuestionTemplateResponse,
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
        qt_bank_qt_repository: QuestionTemplateBankQuestionTemplateRepository,
        question_template_service: QuestionTemplateService,
    ):
        self.question_template_bank_repo = question_template_bank_repository
        self.folder_svc = folder_svc
        self.assoc_repo = qt_bank_qt_repository
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
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )
        deleted_bank = await self.question_template_bank_repo.soft_delete(
            question_template_bank
        )
        await self.question_template_svc.cleanup_orphaned_templates(
            question_template_bank.owner_id
        )
        return deleted_bank

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

        # Filter out soft-deleted templates
        templates: list[QuestionTemplateBankQuestionTemplateResponse] = []
        for assoc in question_template_bank.template_associations:
            if assoc.question_template and assoc.question_template.deleted_at is None:
                qt_data = {
                    "id": assoc.question_template.id,
                    "owner_id": assoc.question_template.owner_id,
                    "question_type": assoc.question_template.question_type,
                    "question_text": assoc.question_template.question_text,
                    "description": assoc.question_template.description,
                    "code": assoc.question_template.code,
                    "entry_function": assoc.question_template.entry_function,
                    "num_distractors": assoc.question_template.num_distractors,
                    "output_type": assoc.question_template.output_type,
                    "target_elements": [
                        {
                            "template_id": te.template_id,
                            "order": te.order,
                            "element_type": te.element_type,
                            "id_list": te.id_list,
                            "name": te.name,
                            "line_number": te.line_number,
                            "modifier": te.modifier,
                        }
                        for te in assoc.question_template.target_elements
                    ],
                    "created_at": assoc.question_template.created_at,
                    "updated_at": assoc.question_template.updated_at,
                    "added_at": assoc.added_at,
                }
                templates.append(
                    QuestionTemplateBankQuestionTemplateResponse.model_validate(qt_data)
                )

        return QuestionTemplateBankWithTemplatesResponse(
            id=question_template_bank.id,
            owner_id=question_template_bank.owner_id,
            folder_id=question_template_bank.folder_id,
            title=question_template_bank.title,
            description=question_template_bank.description,
            created_at=question_template_bank.created_at,
            updated_at=question_template_bank.updated_at,
            question_templates=templates,
        )

    async def add_question_template_to_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template: CreateQuestionTemplateRequest,
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Add a question template to a question template bank.

        Args:
            user_id: User UUID
            question_template_bank_id: QuestionTemplateBank UUID
            question_template: CreateQuestionTemplateRequest object

        Returns:
            Updated question template bank with templates

        Raises:
            ResourceNotFoundError: If question template bank not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        # Verify bank exists and ownership
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )

        # Create question template
        template_entity = await self.question_template_svc.create_template(
            user_id, question_template
        )

        # Create association
        assoc = QuestionTemplateBankQuestionTemplate(
            question_template_bank_id=question_template_bank_id,
            question_template_id=template_entity.id,
        )
        await self.assoc_repo.create(assoc)

        # Expire the cached bank to force fresh query
        self.question_template_bank_repo.db.expire(question_template_bank)

        # Return updated bank with templates
        return await self.get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )

    async def link_question_template_to_bank(
        self,
        user_id: UUID,
        question_template_bank_id: UUID,
        question_template_id: UUID,
    ) -> QuestionTemplateBankWithTemplatesResponse:
        """Link an existing question template to a question template bank.

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
        # Verify bank exists and ownership
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, question_template_bank_id
        )

        # Verify template exists and ownership
        await self.question_template_svc.get_owned_template(
            user_id, question_template_id
        )

        # Check for existing association
        existing_assoc = await self.assoc_repo.find_association(
            question_template_bank_id, question_template_id
        )
        if existing_assoc:
            raise DuplicateResourceError(
                "QuestionTemplateBankQuestionTemplate",
                "question_template_id/question_template_bank_id",
                f"question_template_bank={question_template_bank_id}, \
                question_template={question_template_id}",
            )

        # Create association
        assoc = QuestionTemplateBankQuestionTemplate(
            question_template_bank_id=question_template_bank_id,
            question_template_id=question_template_id,
        )
        await self.assoc_repo.create(assoc)

        # Expire the cached bank to force fresh query
        self.question_template_bank_repo.db.expire(question_template_bank)

        # Return updated bank with templates
        return await self.get_question_template_bank_with_templates(
            user_id, question_template_bank_id
        )

    async def remove_question_template_from_bank(
        self,
        user_id: UUID,
        qt_bank_id: UUID,
        qt_id: UUID,
    ) -> None:
        """Remove a question template from a bank and clean up if orphaned.

        Args:
            user_id: User UUID
            qt_bank_id: QuestionTemplateBank UUID
            qt_id: QuestionTemplate UUID

        Raises:
            ResourceNotFoundError: If association not found
            UnauthorizedAccessError: If user doesn't own the question template bank
        """
        question_template_bank = await self.get_owned_question_template_bank(
            user_id, qt_bank_id
        )

        assoc = await self.assoc_repo.find_association(
            qt_bank_id, qt_id
        )
        if not assoc:
            raise ResourceNotFoundError(
                "QuestionTemplateBankQuestionTemplate",
                f"question_template_bank={qt_bank_id}, question_template={qt_id}",
            )

        await self.assoc_repo.hard_delete(assoc)
        await self.question_template_svc.cleanup_orphaned_templates(
            question_template_bank.owner_id
        )
