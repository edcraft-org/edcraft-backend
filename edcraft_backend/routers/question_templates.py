"""Question template endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import QuestionTemplateServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.schemas.question_template import (
    QuestionTemplateList,
    QuestionTemplateResponse,
    QuestionTemplateUpdate,
)

router = APIRouter(prefix="/question-templates", tags=["question-templates"])


@router.get("", response_model=list[QuestionTemplateList])
async def list_question_templates(
    service: QuestionTemplateServiceDep,
    owner_id: UUID = Query(..., description="Owner ID to filter question templates"),
) -> list[QuestionTemplate]:
    """List question templates by owner."""
    try:
        return await service.list_templates(owner_id=owner_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{template_id}", response_model=QuestionTemplateResponse)
async def get_question_template(
    template_id: UUID, service: QuestionTemplateServiceDep
) -> QuestionTemplate:
    """Get a question template by ID."""
    try:
        return await service.get_template(template_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{template_id}", response_model=QuestionTemplateResponse)
async def update_question_template(
    template_id: UUID,
    template_data: QuestionTemplateUpdate,
    service: QuestionTemplateServiceDep,
) -> QuestionTemplate:
    """Update a question template."""
    try:
        return await service.update_template(template_id, template_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_question_template(
    template_id: UUID, service: QuestionTemplateServiceDep
) -> None:
    """Soft delete a question template."""
    try:
        await service.soft_delete_template(template_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
