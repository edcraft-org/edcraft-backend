from typing import Literal
from uuid import UUID

from edcraft_backend.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.repositories.assessment_template_repository import (
    AssessmentTemplateRepository,
)
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.schemas.assessment_template import (
    AssessmentTemplateResponse,
    AssessmentTemplateWithQuestionTemplatesResponse,
    CreateAssessmentTemplateRequest,
    QuestionTemplateOrder,
    UpdateAssessmentTemplateRequest,
)
from edcraft_backend.schemas.question_template import CreateQuestionTemplateRequest
from edcraft_backend.services.collaboration_service import CollaborationService
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.question_template_service import QuestionTemplateService


class AssessmentTemplateService:
    """Service layer for AssessmentTemplate business logic."""

    def __init__(
        self,
        assessment_template_repository: AssessmentTemplateRepository,
        folder_svc: FolderService,
        question_template_svc: QuestionTemplateService,
        question_template_repository: QuestionTemplateRepository,
        collaboration_svc: CollaborationService,
    ):
        self.template_repo = assessment_template_repository
        self.folder_svc = folder_svc
        self.question_template_svc = question_template_svc
        self.qt_repo = question_template_repository
        self.collaboration_svc = collaboration_svc

    async def get_template(
        self,
        user_id: UUID,
        template_id: UUID,
        min_role: CollaboratorRole = CollaboratorRole.VIEWER,
    ) -> AssessmentTemplate:
        """Get assessment template and verify the user has at least the given role.

        Raises:
            ResourceNotFoundError: If template not found
            UnauthorizedAccessError: If user lacks the required role
        """
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ResourceNotFoundError("AssessmentTemplate", str(template_id))
        await self.collaboration_svc.check_access(
            ResourceType.ASSESSMENT_TEMPLATE, template_id, user_id, min_role
        )
        return template

    async def _require_question_template_in_assessment_template(
        self, assessment_template_id: UUID, qt_id: UUID
    ) -> QuestionTemplate:
        """Fetch question template and verify it belongs to the given assessment template."""
        qt = await self.qt_repo.get_by_id(qt_id)
        if not qt or qt.assessment_template_id != assessment_template_id:
            raise ResourceNotFoundError(
                "QuestionTemplate",
                f"assessment_template={assessment_template_id}, question_template={qt_id}",
            )
        return qt

    async def create_template(
        self,
        user_id: UUID,
        template_data: CreateAssessmentTemplateRequest,
    ) -> AssessmentTemplate:
        """Create a new assessment template.

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If user doesn't own the folder
        """
        await self.folder_svc.get_owned_folder(user_id, template_data.folder_id)

        template = AssessmentTemplate(
            owner_id=user_id,
            **template_data.model_dump(),
        )
        template = await self.template_repo.create(template)

        collab = ResourceCollaborator(
            resource_type=ResourceType.ASSESSMENT_TEMPLATE,
            resource_id=template.id,
            user_id=user_id,
            role=CollaboratorRole.OWNER,
        )
        await self.collaboration_svc.collaborator_repo.create(collab)

        return template

    async def list_templates(
        self,
        user_id: UUID,
        folder_id: UUID | None = None,
        collab_filter: Literal["all", "owned", "shared"] = "all",
    ) -> list[AssessmentTemplateResponse]:
        """List assessment templates the user has access to via collaborator table.

        Args:
            user_id: User UUID
            folder_id: Optional folder UUID filter
            collab_filter: "all" (any role), "owned" (owner only), "shared" (non-owner)

        Returns:
            List of AssessmentTemplateResponse with my_role populated
        """
        if folder_id and collab_filter == "owned":
            await self.folder_svc.get_owned_folder(user_id, folder_id)

        rows = await self.template_repo.list_by_collaborator(
            user_id=user_id,
            collab_filter=collab_filter,
            folder_id=folder_id,
        )
        return [
            AssessmentTemplateResponse.model_validate(tmpl).model_copy(
                update={"my_role": role}
            )
            for tmpl, role in rows
        ]

    async def _get_template_with_question_templates(
        self,
        user_id: UUID | None,
        assessment_template_id: UUID,
        min_role: CollaboratorRole = CollaboratorRole.VIEWER,
    ) -> AssessmentTemplate:
        """Get assessment template with all question templates loaded and access check."""
        assessment_template = await self.template_repo.get_by_id_with_templates(
            assessment_template_id
        )
        if not assessment_template:
            raise ResourceNotFoundError(
                "AssessmentTemplate", str(assessment_template_id)
            )
        await self.collaboration_svc.check_access(
            ResourceType.ASSESSMENT_TEMPLATE, assessment_template_id, user_id, min_role
        )
        return assessment_template

    async def get_template_with_question_templates(
        self, user_id: UUID | None, assessment_template_id: UUID
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Get assessment template with all question templates loaded.

        Args:
            user_id: User UUID
            assessment_template_id: AssessmentTemplate UUID

        Returns:
            AssessmentTemplate with question templates

        Raises:
            ResourceNotFoundError: If assessment template not found
            UnauthorizedAccessError: If user doesn't own the assessment template
        """
        assessment_template = await self._get_template_with_question_templates(
            user_id, assessment_template_id
        )
        my_role = (
            await self.collaboration_svc.collaborator_repo.get_role(
                ResourceType.ASSESSMENT_TEMPLATE, assessment_template_id, user_id
            )
            if user_id
            else None
        )
        return AssessmentTemplateWithQuestionTemplatesResponse.model_validate(
            assessment_template
        ).model_copy(update={"my_role": my_role})

    async def update_template(
        self,
        user_id: UUID,
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
            UnauthorizedAccessError: If user lacks editor or owner role
        """
        template = await self.get_template(
            user_id, template_id, min_role=CollaboratorRole.EDITOR
        )
        update_data = template_data.model_dump(exclude_unset=True)

        if "folder_id" in update_data and update_data["folder_id"]:
            await self.folder_svc.get_owned_folder(user_id, update_data["folder_id"])

        for key, value in update_data.items():
            setattr(template, key, value)

        return await self.template_repo.update(template)

    async def soft_delete_template(
        self, user_id: UUID, template_id: UUID
    ) -> AssessmentTemplate:
        """Soft delete an assessment template and clean up orphaned question templates.

        Args:
            user_id: User UUID requesting the deletion
            template_id: Template UUID

        Returns:
            Soft-deleted template

        Raises:
            ResourceNotFoundError: If template not found
            UnauthorizedAccessError: If user doesn't own the template
        """
        template = await self._get_template_with_question_templates(
            user_id, template_id, min_role=CollaboratorRole.OWNER
        )
        for qt in template.question_templates:
            qt.assessment_template_id = None
            qt.order = None
            await self.qt_repo.update(qt)
            await self.qt_repo.soft_delete(qt)
        deleted_template = await self.template_repo.soft_delete(template)
        return deleted_template

    async def _attach_question_to_assessment_template(
        self,
        assessment_template: AssessmentTemplate,
        question_template: QuestionTemplate,
        order: int | None,
    ) -> None:
        """Set the question template's FK and order, shifting others if needed."""
        current_count = len(assessment_template.question_templates)

        if order is not None and (order < 0 or order > current_count):
            raise ValidationError(
                f"Order must be between 0 and {current_count}. "
                "Omit order to append to the end."
            )

        if order is None:
            order = current_count

        if order < current_count:
            await self.question_template_svc.template_repo.shift_orders_from(
                assessment_template.id, order
            )

        question_template.assessment_template_id = assessment_template.id
        question_template.order = order

        await self.question_template_svc.template_repo.update(question_template)
        self.template_repo.db.expire(assessment_template)

    async def add_question_template_to_template(
        self,
        user_id: UUID,
        template_id: UUID,
        question_template: CreateQuestionTemplateRequest,
        order: int | None = None,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Add a question template to an assessment template.

        Args:
            user_id: User UUID requesting the resource
            template_id: AssessmentTemplate UUID
            question_template: QuestionTemplateCreate object
            order: Order position for the question template

        Returns:
            Updated template with question templates

        Raises:
            ResourceNotFoundError: If assessment template or question template not found
            UnauthorizedAccessError: If user lacks owner or editor role
        """
        assessment_template = await self.get_template(
            user_id, template_id, min_role=CollaboratorRole.EDITOR
        )
        question_template_entity = await self.question_template_svc.create_template(
            user_id=user_id, template_data=question_template
        )

        await self._attach_question_to_assessment_template(
            assessment_template, question_template_entity, order
        )
        return await self.get_template_with_question_templates(user_id, template_id)

    async def remove_question_template_from_template(
        self,
        user_id: UUID,
        template_id: UUID,
        question_template_id: UUID,
    ) -> None:
        """Remove a question template from an assessment template and soft delete it.

        Args:
            user_id: User UUID
            template_id: Assessment UUID
            question_template_id: QuestionTemplate UUID

        Raises:
            ResourceNotFoundError: If association not found
            UnauthorizedAccessError: If user lacks owner or editor role
        """
        await self.get_template(user_id, template_id, min_role=CollaboratorRole.EDITOR)
        qt = await self._require_question_template_in_assessment_template(
            template_id, question_template_id
        )

        qt.assessment_template_id = None
        qt.order = None
        await self.qt_repo.update(qt)
        await self.qt_repo.normalize_orders(template_id)
        await self.question_template_svc.template_repo.soft_delete(qt)

    async def link_question_template_to_template(
        self,
        user_id: UUID,
        template_id: UUID,
        question_template_id: UUID,
        order: int | None = None,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Copy a question template into an assessment template, linking to source.

        Raises:
            ResourceNotFoundError: If assessment template or question template not found
            UnauthorizedAccessError: If user lacks owner or editor role
        """
        assessment_template = await self.get_template(
            user_id, template_id, min_role=CollaboratorRole.EDITOR
        )
        source = await self.question_template_svc.get_template(
            user_id, question_template_id
        )

        copy = await self.question_template_svc.copy_question_template(
            source, assessment_template.owner_id
        )
        await self._attach_question_to_assessment_template(
            assessment_template, copy, order
        )
        return await self.get_template_with_question_templates(user_id, template_id)

    async def sync_question_template_in_template(
        self,
        user_id: UUID,
        template_id: UUID,
        question_template_id: UUID,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Sync a linked question template's content from its source template.

        Raises:
            ResourceNotFoundError: If template, question template, or source not found
            ValidationError: If question template has no source link
            UnauthorizedAccessError: If user lacks EDITOR+ role
        """
        await self.get_template(user_id, template_id, min_role=CollaboratorRole.EDITOR)
        qt = await self._require_question_template_in_assessment_template(
            template_id, question_template_id
        )

        if not qt.linked_from_template_id:
            raise ValidationError("Question template has no source link to sync from.")

        source = await self.question_template_svc.get_template(
            user_id, qt.linked_from_template_id
        )

        await self.question_template_svc.sync_template(qt, source)
        return await self.get_template_with_question_templates(user_id, template_id)

    async def unlink_question_template_in_template(
        self,
        user_id: UUID,
        template_id: UUID,
        question_template_id: UUID,
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        """Remove the source link from a question template copy (make it independent).

        Raises:
            ResourceNotFoundError: If template or question template not found
            UnauthorizedAccessError: If user lacks EDITOR+ role
        """
        await self.get_template(user_id, template_id, min_role=CollaboratorRole.EDITOR)
        qt = await self._require_question_template_in_assessment_template(
            template_id, question_template_id
        )

        qt.linked_from_template_id = None
        await self.qt_repo.update(qt)

        return await self.get_template_with_question_templates(user_id, template_id)

    async def reorder_question_templates(
        self,
        user_id: UUID,
        template_id: UUID,
        question_template_orders: list[QuestionTemplateOrder],
    ) -> AssessmentTemplateWithQuestionTemplatesResponse:
        assessment_template = await self._get_template_with_question_templates(
            user_id, template_id, min_role=CollaboratorRole.EDITOR
        )

        # Validate full coverage
        current_ids = {qt.id for qt in assessment_template.question_templates}
        requested_ids = {item.question_template_id for item in question_template_orders}

        if current_ids != requested_ids:
            raise ValidationError(
                "Reorder must include ALL question templates in the assessment template."
            )

        # Validate order values
        orders = [item.order for item in question_template_orders]

        if len(set(orders)) != len(orders):
            raise ValidationError("Duplicate order values are not allowed.")

        # Normalize
        sorted_items = sorted(question_template_orders, key=lambda x: x.order)

        qt_map = {qt.id: qt for qt in assessment_template.question_templates}

        for idx, item in enumerate(sorted_items):
            qt_map[item.question_template_id].order = idx

        await self.qt_repo.db.flush()

        return await self.get_template_with_question_templates(user_id, template_id)
