"""Assessment template endpoints with question template association management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import AssessmentTemplateServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.schemas.assessment_template import (
    AssessmentTemplateResponse,
    AssessmentTemplateWithQuestionTemplatesResponse,
    CreateAssessmentTemplateRequest,
    InsertQuestionTemplateIntoAssessmentTemplateRequest,
    LinkQuestionTemplateToAssessmentTemplateRequest,
    ReorderQuestionTemplatesInAssessmentTemplateRequest,
    UpdateAssessmentTemplateRequest,
)

router = APIRouter(prefix="/assessment-templates", tags=["assessment-templates"])


@router.post(
    "", response_model=AssessmentTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def create_assessment_template(
    template_data: CreateAssessmentTemplateRequest, service: AssessmentTemplateServiceDep
) -> AssessmentTemplate:
    """Create a new assessment template."""
    try:
        return await service.create_template(template_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[AssessmentTemplateResponse])
async def list_assessment_templates(
    service: AssessmentTemplateServiceDep,
    owner_id: UUID = Query(..., description="Owner ID to filter assessment templates"),
    folder_id: UUID | None = Query(None, description="Filter by folder ID"),
) -> list[AssessmentTemplate]:
    """List assessment templates by owner, optionally filtered by folder."""
    try:
        return await service.list_templates(owner_id=owner_id, folder_id=folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{template_id}", response_model=AssessmentTemplateWithQuestionTemplatesResponse)
async def get_assessment_template(
    template_id: UUID, service: AssessmentTemplateServiceDep
) -> AssessmentTemplateWithQuestionTemplatesResponse:
    """Get assessment template with question templates in order."""
    try:
        return await service.get_template_with_question_templates(template_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{template_id}", response_model=AssessmentTemplateResponse)
async def update_assessment_template(
    template_id: UUID,
    template_data: UpdateAssessmentTemplateRequest,
    service: AssessmentTemplateServiceDep,
) -> AssessmentTemplate:
    """Update assessment template metadata."""
    try:
        return await service.update_template(template_id, template_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_assessment_template(
    template_id: UUID,
    service: AssessmentTemplateServiceDep,
) -> None:
    """Soft delete an assessment template and clean up orphaned question templates."""
    try:
        await service.soft_delete_template(template_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{template_id}/question-templates",
    response_model=AssessmentTemplateWithQuestionTemplatesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_question_template_to_assessment_template(
    template_id: UUID,
    question_template_data: InsertQuestionTemplateIntoAssessmentTemplateRequest,
    service: AssessmentTemplateServiceDep,
) -> AssessmentTemplateWithQuestionTemplatesResponse:
    """Add a question template to an assessment template.

    Question templates are ordered using 0-indexed consecutive integers (0, 1, 2, 3...).
    When adding a question template with a specified order, templates at or after that
    position are automatically shifted down. Omit order to append to the end.

    Valid order range: 0 to current question template count (inclusive).
    """
    try:
        return await service.add_question_template_to_template(
            template_id,
            question_template_data.question_template,
            question_template_data.order,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{template_id}/question-templates/link",
    response_model=AssessmentTemplateWithQuestionTemplatesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_question_template_to_assessment_template(
    template_id: UUID,
    link_data: LinkQuestionTemplateToAssessmentTemplateRequest,
    service: AssessmentTemplateServiceDep,
) -> AssessmentTemplateWithQuestionTemplatesResponse:
    """Link an existing question template to an assessment template.

    Question templates are ordered using 0-indexed consecutive integers (0, 1, 2, 3...).
    When linking a question template with a specified order, templates at or after that
    position are automatically shifted down. Omit order to append to the end.

    Valid order range: 0 to current question template count (inclusive).
    """
    try:
        return await service.link_question_template_to_template(
            template_id,
            link_data.question_template_id,
            link_data.order,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete(
    "/{template_id}/question-templates/{question_template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_question_template_from_assessment_template(
    template_id: UUID,
    question_template_id: UUID,
    service: AssessmentTemplateServiceDep,
) -> None:
    """Remove a question template from an assessment template and clean up if orphaned."""
    try:
        await service.remove_question_template_from_template(
            template_id, question_template_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch(
    "/{template_id}/question-templates/reorder",
    response_model=AssessmentTemplateWithQuestionTemplatesResponse,
)
async def reorder_question_templates(
    template_id: UUID,
    reorder_data: ReorderQuestionTemplatesInAssessmentTemplateRequest,
    service: AssessmentTemplateServiceDep,
) -> AssessmentTemplateWithQuestionTemplatesResponse:
    """Reorder question templates in an assessment template."""
    try:
        return await service.reorder_question_templates(
            template_id, reorder_data.question_template_orders
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
