"""Question template endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from edcraft_backend.dependencies import (
    CurrentUserDep,
    CurrentUserOptionalDep,
    QuestionTemplateServiceDep,
)
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.schemas.question_template import (
    QuestionTemplateResponse,
    QuestionTemplateSummaryResponse,
    UpdateQuestionTemplateRequest,
)

router = APIRouter(prefix="/question-templates", tags=["question-templates"])


@router.get("", response_model=list[QuestionTemplateSummaryResponse])
async def list_question_templates(
    current_user: CurrentUserDep,
    service: QuestionTemplateServiceDep,
) -> list[QuestionTemplate]:
    """List question templates by owner."""
    try:
        return await service.list_templates(current_user.id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{template_id}", response_model=QuestionTemplateResponse)
async def get_question_template(
    current_user: CurrentUserOptionalDep,
    template_id: UUID,
    service: QuestionTemplateServiceDep,
) -> QuestionTemplate:
    """Get a question template by ID."""
    try:
        user_id = current_user.id if current_user else None
        return await service.get_template(user_id, template_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{template_id}", response_model=QuestionTemplateResponse)
async def update_question_template(
    current_user: CurrentUserDep,
    template_id: UUID,
    template_data: UpdateQuestionTemplateRequest,
    service: QuestionTemplateServiceDep,
) -> QuestionTemplate:
    """Update a question template."""
    try:
        return await service.update_template(
            current_user.id, template_id, template_data
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_question_template(
    current_user: CurrentUserDep,
    template_id: UUID,
    service: QuestionTemplateServiceDep,
) -> None:
    """Soft delete a question template."""
    try:
        await service.soft_delete_template(current_user.id, template_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
