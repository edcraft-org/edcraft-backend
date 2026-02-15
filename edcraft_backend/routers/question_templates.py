"""Question template endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from edcraft_backend.dependencies import CurrentUserDep, QuestionTemplateServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.schemas.question_template import (
    QuestionTemplateResponse,
    QuestionTemplateSummaryResponse,
    QuestionTemplateUsageResponse,
    UpdateQuestionTemplateRequest,
)
from edcraft_backend.services.question_template_service import QuestionTemplateUsageDict

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
    current_user: CurrentUserDep,
    template_id: UUID,
    service: QuestionTemplateServiceDep,
) -> QuestionTemplate:
    """Get a question template by ID."""
    try:
        return await service.get_template(current_user.id, template_id)
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


@router.get(
    "/{question_template_id}/usage",
    response_model=QuestionTemplateUsageResponse,
)
async def get_question_template_usage(
    current_user: CurrentUserDep,
    question_template_id: UUID,
    service: QuestionTemplateServiceDep,
) -> QuestionTemplateUsageDict:
    """Get all resources that include this question template."""
    try:
        return await service.get_question_template_usage(
            current_user.id, question_template_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
