from uuid import UUID

from edcraft_backend.exceptions import ResourceNotFoundError, UnauthorizedAccessError
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.repositories.assessment_template_question_template_repository import (
    AssessmentTemplateQuestionTemplateRepository,
)
from edcraft_backend.repositories.question_template_repository import QuestionTemplateRepository
from edcraft_backend.schemas.question_template import (
    CreateQuestionTemplateRequest,
    UpdateQuestionTemplateRequest,
)


class QuestionTemplateService:
    """Service layer for QuestionTemplate business logic."""

    def __init__(
        self,
        question_template_repository: QuestionTemplateRepository,
        assessment_template_ques_template_repository: AssessmentTemplateQuestionTemplateRepository,
    ):
        self.template_repo = question_template_repository
        self.assoc_repo = assessment_template_ques_template_repository

    async def create_template(
        self,
        template_data: CreateQuestionTemplateRequest,
    ) -> QuestionTemplate:
        """Create a new question template.

        Args:
            template_data: Template creation data

        Returns:
            Created template
        """
        template = QuestionTemplate(**template_data.model_dump())
        return await self.template_repo.create(template)

    async def list_templates(
        self,
        owner_id: UUID,
    ) -> list[QuestionTemplate]:
        """List question templates.

        Args:
            owner_id: Optional owner filter
            question_type: Optional question type filter

        Returns:
            List of templates ordered by creation date
        """
        filters: dict[str, UUID] = {}
        if owner_id:
            filters["owner_id"] = owner_id

        return await self.template_repo.list(
            filters=filters if filters else None,
            order_by=QuestionTemplate.created_at.desc(),
        )

    async def get_template(self, template_id: UUID) -> QuestionTemplate:
        """Get a question template by ID.

        Args:
            template_id: Template UUID

        Returns:
            QuestionTemplate entity

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ResourceNotFoundError("QuestionTemplate", str(template_id))
        return template

    async def update_template(
        self,
        template_id: UUID,
        template_data: UpdateQuestionTemplateRequest,
    ) -> QuestionTemplate:
        """Update a question template.

        Args:
            template_id: Template UUID
            template_data: Template update data

        Returns:
            Updated template

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.get_template(template_id)
        update_data = template_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(template, key, value)

        return await self.template_repo.update(template)

    async def soft_delete_template(self, template_id: UUID) -> QuestionTemplate:
        """Soft delete a question template.

        Args:
            template_id: Template UUID

        Returns:
            Soft-deleted template

        Raises:
            ResourceNotFoundError: If template not found
        """
        template = await self.get_template(template_id)
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

    async def get_assessment_templates_for_question_template(
        self,
        question_template_id: UUID,
        requesting_user_id: UUID,
    ) -> list[AssessmentTemplate]:
        """Get all assessment templates that include this question template.

        Args:
            question_template_id: QuestionTemplate UUID
            requesting_user_id: User UUID making the request

        Returns:
            List of assessment templates that include this question template

        Raises:
            ResourceNotFoundError: If question template not found
            UnauthorizedAccessError: If user doesn't own the question template
        """
        template = await self.get_template(question_template_id)
        if template.owner_id != requesting_user_id:
            raise UnauthorizedAccessError("QuestionTemplate", str(question_template_id))

        return await self.assoc_repo.get_assessment_templates_by_question_template_id(
            question_template_id
        )
