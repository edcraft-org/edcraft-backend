from uuid import UUID

from edcraft_backend.exceptions import ResourceNotFoundError, UnauthorizedAccessError
from edcraft_backend.models.enums import CollaboratorRole
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.target_element import TargetElement
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.repositories.target_element_repository import (
    TargetElementRepository,
)
from edcraft_backend.schemas.question_template import (
    CreateQuestionTemplateRequest,
    UpdateQuestionTemplateRequest,
)


class QuestionTemplateService:
    """Service layer for QuestionTemplate business logic."""

    def __init__(
        self,
        question_template_repository: QuestionTemplateRepository,
        target_element_repository: TargetElementRepository,
        collaborator_repository: ResourceCollaboratorRepository,
    ):
        self.template_repo = question_template_repository
        self.target_element_repo = target_element_repository
        self.collaborator_repo = collaborator_repository

    async def create_template(
        self,
        user_id: UUID,
        template_data: CreateQuestionTemplateRequest,
    ) -> QuestionTemplate:
        """Create a new question template.

        Args:
            user_id: User UUID
            template_data: Template creation data

        Returns:
            Created template
        """
        template = QuestionTemplate(
            owner_id=user_id, **template_data.model_dump(exclude={"target_elements"})
        )
        created_template = await self.template_repo.create(template)

        target_elements: list[TargetElement] = []
        for idx, element_data in enumerate(template_data.target_elements):
            element = TargetElement(
                **element_data.model_dump(), template_id=created_template.id, order=idx
            )
            target_elements.append(element)
        await self.target_element_repo.create_many(target_elements)

        await self.template_repo.db.refresh(created_template)
        return created_template

    async def copy_question_template(
        self, source: QuestionTemplate, new_owner_id: UUID
    ) -> QuestionTemplate:
        """Create an independent copy of a question template owned by new_owner_id.

        Args:
            source: Source template to copy
            new_owner_id: User UUID who will own the copy

        Returns:
            Newly created QuestionTemplate with linked_from_template_id set to source.id
        """
        copy = QuestionTemplate(
            owner_id=new_owner_id,
            question_type=source.question_type,
            question_text_template=source.question_text_template,
            text_template_type=source.text_template_type,
            description=source.description,
            code=source.code,
            entry_function=source.entry_function,
            num_distractors=source.num_distractors,
            output_type=source.output_type,
            input_data_config=source.input_data_config,
            code_info=source.code_info,
            linked_from_template_id=source.id,
        )
        created_copy = await self.template_repo.create(copy)

        # Copy target elements
        new_elements: list[TargetElement] = []
        for te in source.target_elements:
            new_te = TargetElement(
                template_id=created_copy.id,
                order=te.order,
                element_type=te.element_type,
                id_list=list(te.id_list),
                name=te.name,
                line_number=te.line_number,
                modifier=te.modifier,
            )
            new_elements.append(new_te)
        if new_elements:
            await self.target_element_repo.create_many(new_elements)
            await self.template_repo.db.refresh(created_copy)

        return created_copy

    async def list_templates(
        self,
        user_id: UUID,
    ) -> list[QuestionTemplate]:
        """List question templates.

        Args:
            user_id: User UUID filter

        Returns:
            List of templates ordered by creation date
        """
        filters: dict[str, UUID] = {}
        if user_id:
            filters["owner_id"] = user_id

        return await self.template_repo.list(
            filters=filters if filters else None,
            order_by=QuestionTemplate.created_at.desc(),
        )

    async def get_template(
        self,
        user_id: UUID,
        template_id: UUID,
        min_role: CollaboratorRole = CollaboratorRole.VIEWER,
    ) -> QuestionTemplate:
        """Get a question template by ID and verify access.

        Args:
            user_id: User UUID
            template_id: Template UUID
            min_role: Minimum required role

        Returns:
            QuestionTemplate entity

        Raises:
            ResourceNotFoundError: If template not found
            UnauthorizedAccessError: If user lacks the required role
        """
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ResourceNotFoundError("QuestionTemplate", str(template_id))

        has_perm = await self.collaborator_repo.check_question_template_permission(
            question_template_id=template_id,
            user_id=user_id,
            min_role=min_role,
        )
        if not has_perm:
            raise UnauthorizedAccessError("QuestionTemplate", str(template_id))

        return template

    async def update_template(
        self,
        user_id: UUID,
        template_id: UUID,
        template_data: UpdateQuestionTemplateRequest,
    ) -> QuestionTemplate:
        """Update a question template.

        Args:
            user_id: User UUID
            template_id: Template UUID
            template_data: Template update data

        Returns:
            Updated template

        Raises:
            ResourceNotFoundError: If template not found
            UnauthorizedAccessError: If user has no edit access
        """
        template = await self.get_template(
            user_id, template_id, min_role=CollaboratorRole.EDITOR
        )
        update_data = template_data.model_dump(
            exclude={"target_elements"}, exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(template, key, value)

        if template_data.target_elements is not None:
            existing_elements = {te.order: te for te in template.target_elements}
            new_elements = []

            for idx, element_data in enumerate(template_data.target_elements):
                if idx in existing_elements:
                    # Update existing element
                    element = existing_elements[idx]
                    for key, value in element_data.model_dump(
                        exclude_unset=True
                    ).items():
                        setattr(element, key, value)
                else:
                    # Create new element
                    new_element = TargetElement(
                        **element_data.model_dump(), template_id=template.id, order=idx
                    )
                    new_elements.append(new_element)

            if new_elements:
                await self.target_element_repo.create_many(new_elements)

            if len(existing_elements) > len(template_data.target_elements):
                # Remove extra elements
                for idx in range(
                    len(template_data.target_elements), len(existing_elements)
                ):
                    await self.target_element_repo.hard_delete(existing_elements[idx])

        return await self.template_repo.update(template)

    async def soft_delete_template(
        self, user_id: UUID, template_id: UUID
    ) -> QuestionTemplate:
        """Soft delete a question template.

        Args:
            user_id: User UUID
            template_id: Template UUID

        Returns:
            Soft-deleted template

        Raises:
            ResourceNotFoundError: If template not found
            UnauthorizedAccessError: If user doesn't own the template
        """
        template = await self.get_template(user_id, template_id, CollaboratorRole.OWNER)
        return await self.template_repo.soft_delete(template)

    async def sync_template(
        self, qt: QuestionTemplate, source: QuestionTemplate
    ) -> QuestionTemplate:
        """Sync content of qt to match source.

        Args:
            qt: QuestionTemplate to be updated
            source: QuestionTemplate to sync from

        Returns:
            Updated question template
        """
        # Overwrite content fields from source
        qt.question_type = source.question_type
        qt.question_text_template = source.question_text_template
        qt.text_template_type = source.text_template_type
        qt.description = source.description
        qt.code = source.code
        qt.entry_function = source.entry_function
        qt.num_distractors = source.num_distractors
        qt.output_type = source.output_type
        qt.input_data_config = source.input_data_config
        qt.code_info = source.code_info
        await self.template_repo.update(qt)

        # Replace target elements
        for te in qt.target_elements:
            await self.target_element_repo.hard_delete(te)

        new_elements = [
            TargetElement(
                template_id=qt.id,
                order=te.order,
                element_type=te.element_type,
                id_list=list(te.id_list),
                name=te.name,
                line_number=te.line_number,
                modifier=te.modifier,
            )
            for te in source.target_elements
        ]
        if new_elements:
            await self.target_element_repo.create_many(new_elements)

        await self.template_repo.db.refresh(qt)
        return qt

    async def cleanup_orphaned_templates(self, owner_id: UUID) -> int:
        """Delete templates not used in any active assessment template.

        Args:
            owner_id: User UUID

        Returns:
            Number of templates deleted
        """
        orphaned = await self.template_repo.get_orphaned_templates(owner_id)
        count = 0

        for template in orphaned:
            await self.template_repo.soft_delete(template)
            count += 1

        return count
