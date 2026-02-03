from uuid import UUID

from edcraft_backend.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
    UnauthorizedAccessError,
    ValidationError,
)
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.assessment_template_question_template import (
    AssessmentTemplateQuestionTemplate,
)
from edcraft_backend.repositories.assessment_template_question_template_repository import (
    AssessmentTemplateQuestionTemplateRepository,
)
from edcraft_backend.repositories.assessment_template_repository import (
    AssessmentTemplateRepository,
)
from edcraft_backend.repositories.folder_repository import FolderRepository
from edcraft_backend.schemas.assessment_template import (
    AssessmentTemplateQuestionTemplateResponse,
    AssessmentTemplateWithQuestionTemplatesResponse,
    CreateAssessmentTemplateRequest,
    QuestionTemplateOrder,
    UpdateAssessmentTemplateRequest,
)
from edcraft_backend.schemas.question_template import CreateQuestionTemplateRequest
from edcraft_backend.services.question_template_service import QuestionTemplateService


class AssessmentTemplateService:
    """Service layer for AssessmentTemplate business logic."""

    def __init__(
        self,
        assessment_template_repository: AssessmentTemplateRepository,
        folder_repository: FolderRepository,
        question_template_svc: QuestionTemplateService,
        assessment_template_question_template_repository: (
            AssessmentTemplateQuestionTemplateRepository
        ),
    ):
        self.template_repo = assessment_template_repository
        self.folder_repo = folder_repository
        self.question_template_svc = question_template_svc
        self.assoc_repo = assessment_template_question_template_repository

    async def create_template(
        self,
        template_data: CreateAssessmentTemplateRequest,
    ) -> AssessmentTemplate:
        """Create a new assessment template.

        Args:
            template_data: Template creation data

        Returns:
            Created template

        Raises:
            ResourceNotFoundError: If folder not found
        """
        folder = await self.folder_repo.get_by_id(template_data.folder_id)
        if not folder:
            raise ResourceNotFoundError("Folder", str(template_data.folder_id))

        template = AssessmentTemplate(**template_data.model_dump())
        return await self.template_repo.create(template)

    async def list_templates(
        self,
        owner_id: UUID,
        folder_id: UUID | None = None,
    ) -> list[AssessmentTemplate]:
        """List assessment templates within folder or all user templates.

        Args:
            owner_id: Owner UUID
            folder_id: Folder UUID (None for ALL templates owned by user)

        Returns:
            List of templates ordered by updated_at descending
        """
        if folder_id:
            templates = await self.template_repo.get_by_folder(folder_id)
        else:
            templates = await self.template_repo.list(
                filters={"owner_id": owner_id},
                order_by=AssessmentTemplate.updated_at.desc()
            )

        return templates

    async def get_template(self, template_id: UUID) -> AssessmentTemplate:
        """Get an assessment template by ID.

        Args:
            template_id: Template UUID

        Returns:
            AssessmentTemplate entity

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ResourceNotFoundError("AssessmentTemplate", str(template_id))
        return template

    async def update_template(
        self,
        template_id: UUID,
        template_data: UpdateAssessmentTemplateRequest,
    ) -> AssessmentTemplate:
        """Update an assessment template.

        Args:
            template_id: Template UUID
            template_data: Template update data

        Returns:
            Updated template

        Raises:
            ResourceNotFoundError: If template or folder not found
            UnauthorizedAccessError: If user doesn't own resources
        """
        template = await self.get_template(template_id)
        update_data = template_data.model_dump(exclude_unset=True)

        if "folder_id" in update_data and update_data["folder_id"]:
            folder = await self.folder_repo.get_by_id(update_data["folder_id"])
            if not folder:
                raise ResourceNotFoundError("Folder", str(update_data["folder_id"]))
            if folder.owner_id != template.owner_id:
                raise UnauthorizedAccessError(
                    "Folder",
                    str(update_data["folder_id"]),
                )

        for key, value in update_data.items():
            setattr(template, key, value)

        return await self.template_repo.update(template)

    async def soft_delete_template(
        self, template_id: UUID
    ) -> AssessmentTemplate:
        """Soft delete an assessment template and clean up orphaned question templates.

        Args:
            template_id: Template UUID

        Returns:
            Soft-deleted template

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.get_template(template_id)
        deleted_template = await self.template_repo.soft_delete(template)
        await self.question_template_svc.cleanup_orphaned_templates(template.owner_id)
        return deleted_template

    async def get_template_with_question_templates(
        self,
        template_id: UUID,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Get an assessment template with all question templates loaded.

        Args:
            template_id: Template UUID

        Returns:
            AssessmentTemplate with question templates

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.template_repo.get_by_id_with_templates(template_id)
        if not template:
            raise ResourceNotFoundError("AssessmentTemplate", str(template_id))

        # Filter out soft-deleted question templates
        question_templates: list[AssessmentTemplateQuestionTemplateResponse] = []
        for assoc in template.template_associations:
            if assoc.question_template and assoc.question_template.deleted_at is None:
                qt_data = {
                    "id": assoc.question_template.id,
                    "owner_id": assoc.question_template.owner_id,
                    "question_type": assoc.question_template.question_type,
                    "question_text": assoc.question_template.question_text,
                    "description": assoc.question_template.description,
                    "template_config": assoc.question_template.template_config,
                    "created_at": assoc.question_template.created_at,
                    "updated_at": assoc.question_template.updated_at,
                    "order": assoc.order,
                    "added_at": assoc.added_at,
                }
                question_templates.append(
                    AssessmentTemplateQuestionTemplateResponse.model_validate(qt_data)
                )

        return AssessmentTemplateWithQuestionTemplatesResponse(
            id=template.id,
            owner_id=template.owner_id,
            folder_id=template.folder_id,
            title=template.title,
            description=template.description,
            created_at=template.created_at,
            updated_at=template.updated_at,
            question_templates=question_templates,
        )

    async def add_question_template_to_template(
        self,
        template_id: UUID,
        question_template: CreateQuestionTemplateRequest,
        order: int | None = None,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Add a question template to an assessment template.

        Args:
            template_id: AssessmentTemplate UUID
            question_template: QuestionTemplateCreate object
            order: Order position for the question template

        Returns:
            Updated template with question templates

        Raises:
            ResourceNotFoundError: If assessment template or question template not found
            DuplicateResourceError: If order is invalid
        """
        # Verify assessment template exists
        assessment_template = await self.get_template(template_id)

        # Create question
        question_template_entity = await self.question_template_svc.create_template(
            question_template
        )

        # Validate and determine order
        current_count = await self.assoc_repo.get_count(template_id)

        if order is not None and (order < 0 or order > current_count):
            raise ValidationError(
                f"Order must be between 0 and {current_count}. "
                "Omit order to append to the end."
            )

        if order is None:
            order = current_count

        if order < current_count:
            await self.assoc_repo.shift_orders_from(template_id, order)

        # Create association
        assoc = AssessmentTemplateQuestionTemplate(
            assessment_template_id=template_id,
            question_template_id=question_template_entity.id,
            order=order,
        )
        await self.assoc_repo.create(assoc)

        # Expire the cached assessment template to force fresh query
        self.template_repo.db.expire(assessment_template)

        # Return updated assessment template with question templates
        return await self.get_template_with_question_templates(template_id)

    async def link_question_template_to_template(
        self,
        template_id: UUID,
        question_template_id: UUID,
        order: int | None = None,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Link an existing question template to an assessment template.

        Args:
            template_id: AssessmentTemplate UUID
            question_template_id: QuestionTemplate UUID
            order: Order position for the question template

        Returns:
            Updated assessment template with question templates

        Raises:
            ResourceNotFoundError: If assessment template or question template not found
            DuplicateResourceError: If question template already linked to assessment template
            ValidationError: If order is invalid
        """
        # Verify assessment template exists
        assessment_template = await self.get_template(template_id)

        # Verify question template exists
        await self.question_template_svc.get_template(question_template_id)

        # Check for existing association
        existing_assoc = await self.assoc_repo.find_association(
            template_id, question_template_id
        )
        if existing_assoc:
            raise DuplicateResourceError(
                "AssessmentTemplateQuestionTemplate",
                "question_template_id/template_id",
                f"template={template_id}, question_template={question_template_id}",
            )

        # Validate and determine order
        current_count = await self.assoc_repo.get_count(template_id)

        if order is not None and (order < 0 or order > current_count):
            raise ValidationError(
                f"Order must be between 0 and {current_count}. "
                "Omit order to append to the end."
            )

        if order is None:
            order = current_count

        if order < current_count:
            await self.assoc_repo.shift_orders_from(template_id, order)

        # Create association
        assoc = AssessmentTemplateQuestionTemplate(
            assessment_template_id=template_id,
            question_template_id=question_template_id,
            order=order,
        )
        await self.assoc_repo.create(assoc)

        # Expire the cached assessment template to force fresh query
        self.template_repo.db.expire(assessment_template)

        # Return updated assessment template with question templates
        return await self.get_template_with_question_templates(template_id)

    async def remove_question_template_from_template(
        self,
        template_id: UUID,
        question_template_id: UUID,
    ) -> None:
        """Remove a question template from an assessment template and clean up if orphaned.

        Args:
            template_id: AssessmentTemplate UUID
            question_template_id: QuestionTemplate UUID

        Raises:
            ResourceNotFoundError: If association not found
        """
        template = await self.get_template(template_id)

        assoc = await self.assoc_repo.find_association(
            template_id, question_template_id
        )
        if not assoc:
            raise ResourceNotFoundError(
                "AssessmentTemplateQuestionTemplate",
                f"template={template_id}, question_template={question_template_id}",
            )

        await self.assoc_repo.hard_delete(assoc)
        await self.assoc_repo.normalize_orders(template_id)
        await self.question_template_svc.cleanup_orphaned_templates(template.owner_id)

    async def reorder_question_templates(
        self,
        template_id: UUID,
        question_template_orders: list[QuestionTemplateOrder],
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Reorder question templates in an assessment template.

        Args:
            template_id: AssessmentTemplate UUID
            question_template_orders: List of QuestionTemplateOrder objects

        Returns:
            Updated assessment template with question templates

        Raises:
            ResourceNotFoundError: If assessment template not found
            ValidationError: If not all question templates are included in reorder
        """
        # Verify assessment template exists
        await self.get_template(template_id)

        # Get all current associations
        current_assocs = await self.assoc_repo.get_all_for_assessment_template(
            template_id
        )
        current_question_template_ids = {
            assoc.question_template_id for assoc in current_assocs
        }
        # Check that ALL question templates are included
        requested_question_template_ids = {
            item.question_template_id for item in question_template_orders
        }
        if current_question_template_ids != requested_question_template_ids:
            raise ValidationError(
                "Reorder must include ALL question templates in the assessment template."
            )

        # Sort by the requested order to determine final sequence
        sorted_orders = sorted(question_template_orders, key=lambda x: x.order)

        # Temporarily offset all orders to avoid constraint violations
        assoc: AssessmentTemplateQuestionTemplate | None = None
        for assoc in current_assocs:
            assoc.order = -(assoc.order + 1)
            await self.assoc_repo.update(assoc)

        # Flush to commit temporary offsets
        await self.template_repo.db.flush()

        # Apply final normalized orders (0, 1, 2, 3...)
        for idx, item in enumerate(sorted_orders):
            assoc = await self.assoc_repo.find_association(
                template_id, item.question_template_id
            )
            if assoc:
                assoc.order = idx
                await self.assoc_repo.update(assoc)

        # Flush updates
        await self.template_repo.db.flush()

        # Return updated assessment template with question templates
        return await self.get_template_with_question_templates(template_id)
