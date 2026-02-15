"""Question template bank endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import (
    CurrentUserDep,
    QuestionTemplateBankServiceDep,
)
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.schemas.question_template_bank import (
    CreateQuestionTemplateBankRequest,
    InsertQuestionTemplateIntoQuestionTemplateBankRequest,
    LinkQuestionTemplateToQuestionTemplateBankRequest,
    QuestionTemplateBankResponse,
    QuestionTemplateBankWithTemplatesResponse,
    UpdateQuestionTemplateBankRequest,
)

router = APIRouter(prefix="/question-template-banks", tags=["question-template-banks"])


@router.post(
    "", response_model=QuestionTemplateBankResponse, status_code=status.HTTP_201_CREATED
)
async def create_question_template_bank(
    current_user: CurrentUserDep,
    question_template_bank_data: CreateQuestionTemplateBankRequest,
    service: QuestionTemplateBankServiceDep,
) -> QuestionTemplateBank:
    """Create a new question template bank."""
    try:
        return await service.create_question_template_bank(
            current_user.id, question_template_bank_data
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[QuestionTemplateBankResponse])
async def list_question_template_banks(
    current_user: CurrentUserDep,
    service: QuestionTemplateBankServiceDep,
    folder_id: UUID | None = Query(None, description="Filter by folder ID"),
) -> list[QuestionTemplateBank]:
    """List question template banks by owner, optionally filtered by folder."""
    try:
        return await service.list_question_template_banks(
            user_id=current_user.id, folder_id=folder_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/{question_template_bank_id}",
    response_model=QuestionTemplateBankWithTemplatesResponse,
)
async def get_question_template_bank(
    current_user: CurrentUserDep,
    question_template_bank_id: UUID,
    service: QuestionTemplateBankServiceDep,
) -> QuestionTemplateBankWithTemplatesResponse:
    """Get question template bank with all question templates."""
    try:
        return await service.get_question_template_bank_with_templates(
            user_id=current_user.id,
            question_template_bank_id=question_template_bank_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch(
    "/{question_template_bank_id}", response_model=QuestionTemplateBankResponse
)
async def update_question_template_bank(
    current_user: CurrentUserDep,
    question_template_bank_id: UUID,
    question_template_bank_data: UpdateQuestionTemplateBankRequest,
    service: QuestionTemplateBankServiceDep,
) -> QuestionTemplateBank:
    """Update question template bank metadata."""
    try:
        return await service.update_question_template_bank(
            user_id=current_user.id,
            question_template_bank_id=question_template_bank_id,
            question_template_bank_data=question_template_bank_data,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{question_template_bank_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_question_template_bank(
    current_user: CurrentUserDep,
    question_template_bank_id: UUID,
    service: QuestionTemplateBankServiceDep,
) -> None:
    """Soft delete a question template bank and clean up orphaned templates."""
    try:
        await service.soft_delete_question_template_bank(
            user_id=current_user.id,
            question_template_bank_id=question_template_bank_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{question_template_bank_id}/question-templates",
    response_model=QuestionTemplateBankWithTemplatesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_question_template_into_bank(
    current_user: CurrentUserDep,
    question_template_bank_id: UUID,
    question_template_data: InsertQuestionTemplateIntoQuestionTemplateBankRequest,
    service: QuestionTemplateBankServiceDep,
) -> QuestionTemplateBankWithTemplatesResponse:
    """Insert a question template to a question template bank."""
    try:
        return await service.add_question_template_to_bank(
            current_user.id,
            question_template_bank_id,
            question_template_data.question_template,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{question_template_bank_id}/question-templates/link",
    response_model=QuestionTemplateBankWithTemplatesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_question_template_to_bank(
    current_user: CurrentUserDep,
    question_template_bank_id: UUID,
    question_template_data: LinkQuestionTemplateToQuestionTemplateBankRequest,
    service: QuestionTemplateBankServiceDep,
) -> QuestionTemplateBankWithTemplatesResponse:
    """Link an existing question template to a question template bank."""
    try:
        return await service.link_question_template_to_bank(
            current_user.id,
            question_template_bank_id,
            question_template_data.question_template_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete(
    "/{question_template_bank_id}/question-templates/{question_template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_question_template_from_bank(
    current_user: CurrentUserDep,
    question_template_bank_id: UUID,
    question_template_id: UUID,
    service: QuestionTemplateBankServiceDep,
) -> None:
    """Remove a question template from a bank and clean up if orphaned."""
    try:
        await service.remove_question_template_from_bank(
            current_user.id, question_template_bank_id, question_template_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
