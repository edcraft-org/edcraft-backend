"""Question bank endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import CurrentUserDep, QuestionBankServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.schemas.question_bank import (
    CreateQuestionBankRequest,
    InsertQuestionIntoQuestionBankRequest,
    LinkQuestionToQuestionBankRequest,
    QuestionBankResponse,
    QuestionBankWithQuestionsResponse,
    UpdateQuestionBankRequest,
)

router = APIRouter(prefix="/question-banks", tags=["question-banks"])


@router.post(
    "", response_model=QuestionBankResponse, status_code=status.HTTP_201_CREATED
)
async def create_question_bank(
    current_user: CurrentUserDep,
    question_bank_data: CreateQuestionBankRequest,
    service: QuestionBankServiceDep,
) -> QuestionBank:
    """Create a new question bank."""
    try:
        return await service.create_question_bank(current_user.id, question_bank_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[QuestionBankResponse])
async def list_question_banks(
    current_user: CurrentUserDep,
    service: QuestionBankServiceDep,
    folder_id: UUID | None = Query(None, description="Filter by folder ID"),
) -> list[QuestionBank]:
    """List question banks by owner, optionally filtered by folder."""
    try:
        return await service.list_question_banks(
            user_id=current_user.id, folder_id=folder_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{question_bank_id}", response_model=QuestionBankWithQuestionsResponse)
async def get_question_bank(
    current_user: CurrentUserDep,
    question_bank_id: UUID,
    service: QuestionBankServiceDep,
) -> QuestionBankWithQuestionsResponse:
    """Get question bank with questions in order."""
    try:
        return await service.get_question_bank_with_questions(
            user_id=current_user.id, question_bank_id=question_bank_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{question_bank_id}", response_model=QuestionBankResponse)
async def update_question_bank(
    current_user: CurrentUserDep,
    question_bank_id: UUID,
    question_bank_data: UpdateQuestionBankRequest,
    service: QuestionBankServiceDep,
) -> QuestionBank:
    """Update question bank metadata."""
    try:
        return await service.update_question_bank(
            user_id=current_user.id,
            question_bank_id=question_bank_id,
            question_bank_data=question_bank_data,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{question_bank_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_question_bank(
    current_user: CurrentUserDep,
    question_bank_id: UUID,
    service: QuestionBankServiceDep,
) -> None:
    """Soft delete a question bank and clean up orphaned questions."""
    try:
        await service.soft_delete_question_bank(
            user_id=current_user.id, question_bank_id=question_bank_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{question_bank_id}/questions",
    response_model=QuestionBankWithQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_question_into_question_bank(
    current_user: CurrentUserDep,
    question_bank_id: UUID,
    question_data: InsertQuestionIntoQuestionBankRequest,
    service: QuestionBankServiceDep,
) -> QuestionBankWithQuestionsResponse:
    """Insert a question to a question bank."""
    try:
        return await service.add_question_to_question_bank(
            current_user.id,
            question_bank_id,
            question_data.question,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{question_bank_id}/questions/link",
    response_model=QuestionBankWithQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_question_into_question_bank(
    current_user: CurrentUserDep,
    question_bank_id: UUID,
    question_data: LinkQuestionToQuestionBankRequest,
    service: QuestionBankServiceDep,
) -> QuestionBankWithQuestionsResponse:
    """Link an existing question into a question bank."""
    try:
        return await service.link_question_to_question_bank(
            current_user.id,
            question_bank_id,
            question_data.question_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete(
    "/{question_bank_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_question_from_question_bank(
    current_user: CurrentUserDep,
    question_bank_id: UUID,
    question_id: UUID,
    service: QuestionBankServiceDep,
) -> None:
    """Remove a question from a question bank and clean up if orphaned."""
    try:
        await service.remove_question_from_question_bank(
            current_user.id, question_bank_id, question_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
