from typing import TypedDict
from uuid import UUID

from edcraft_backend.exceptions import ResourceNotFoundError, UnauthorizedAccessError
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.models.target_element import TargetElement
from edcraft_backend.repositories.assessment_template_question_template_repository import (
    AssessmentTemplateQuestionTemplateRepository,
)
from edcraft_backend.repositories.question_template_bank_question_template_repository import (
    QuestionTemplateBankQuestionTemplateRepository,
)
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.repositories.target_element_repository import (
    TargetElementRepository,
)
from edcraft_backend.schemas.question_template import (
    CreateQuestionTemplateRequest,
    UpdateQuestionTemplateRequest,
)


class QuestionTemplateUsageDict(TypedDict):
    """Dict type for question template usage."""

    assessment_templates: list[AssessmentTemplate]
    question_template_banks: list[QuestionTemplateBank]


class QuestionTemplateService:
    """Service layer for QuestionTemplate business logic."""

    def __init__(
        self,
        question_template_repository: QuestionTemplateRepository,
        assessment_template_qt_repository: AssessmentTemplateQuestionTemplateRepository,
        target_element_repository: TargetElementRepository,
        qt_bank_qt_repository: QuestionTemplateBankQuestionTemplateRepository,
    ):
        self.template_repo = question_template_repository
        self.assessment_template_assoc_repo = assessment_template_qt_repository
        self.target_element_repo = target_element_repository
        self.qt_bank_assoc_repo = qt_bank_qt_repository

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

    async def list_templates(
        self,
        user_id: UUID,
    ) -> list[QuestionTemplate]:
        """List question templates.

        Args:
            user_id: User UUID filter
            question_type: Optional question type filter

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

    async def get_owned_template(
        self, user_id: UUID, template_id: UUID
    ) -> QuestionTemplate:
        """Get a question template by ID.

        Args:
            user_id: User UUID
            template_id: Template UUID

        Returns:
            QuestionTemplate entity

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ResourceNotFoundError("QuestionTemplate", str(template_id))
        if template.owner_id != user_id:
            raise UnauthorizedAccessError("QuestionTemplate", str(template_id))
        return template

    async def get_template(
        self,
        user_id: UUID,
        template_id: UUID,
    ) -> QuestionTemplate:
        """Get a question template by ID.

        Args:
            user_id: User UUID
            template_id: Template UUID

        Returns:
            QuestionTemplate entity

        Raises:
            ResourceNotFoundError: If template not found
            UnauthorizedAccessError: If user doesn't own the template
        """
        return await self.get_owned_template(user_id, template_id)

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
            UnauthorizedAccessError: If user doesn't own the template
        """
        template = await self.get_owned_template(user_id, template_id)
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
        template = await self.get_owned_template(user_id, template_id)
        return await self.template_repo.soft_delete(template)

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

    async def get_question_template_usage(
        self,
        user_id: UUID,
        question_template_id: UUID,
    ) -> QuestionTemplateUsageDict:
        """Get all resources that include this question template.

        Args:
            user_id: User UUID requesting resources
            question_template_id: QuestionTemplate UUID

        Returns:
            Dict containing lists of associated resources

        Raises:
            ResourceNotFoundError: If question template not found
            UnauthorizedAccessError: If user doesn't own the question template
        """
        await self.get_owned_template(user_id, question_template_id)
        assessment_templates = await (
            self.assessment_template_assoc_repo
            .get_assessment_templates_by_question_template_id(question_template_id)
        )
        question_template_banks = await (
            self.qt_bank_assoc_repo
            .get_question_template_banks_by_question_template_id(question_template_id)
        )
        return {
            "assessment_templates": assessment_templates,
            "question_template_banks": question_template_banks,
        }
