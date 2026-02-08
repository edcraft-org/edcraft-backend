"""Question endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from edcraft_backend.dependencies import CurrentUserDep, QuestionServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.question import Question
from edcraft_backend.schemas.assessment import (
    AssessmentResponse,
)
from edcraft_backend.schemas.question import (
    QuestionResponse,
    UpdateQuestionRequest,
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    current_user: CurrentUserDep,
    service: QuestionServiceDep,
) -> list[Question]:
    """List questions by owner."""
    try:
        return await service.list_questions(current_user.id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    current_user: CurrentUserDep, question_id: UUID, service: QuestionServiceDep
) -> Question:
    """Get a question by ID."""
    try:
        return await service.get_question(current_user.id, question_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    current_user: CurrentUserDep,
    question_id: UUID,
    question_data: UpdateQuestionRequest,
    service: QuestionServiceDep,
) -> Question:
    """Update a question."""
    try:
        return await service.update_question(
            current_user.id, question_id, question_data
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_question(
    current_user: CurrentUserDep, question_id: UUID, service: QuestionServiceDep
) -> None:
    """Soft delete a question."""
    try:
        await service.soft_delete_question(current_user.id, question_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{question_id}/assessments", response_model=list[AssessmentResponse])
async def get_assessments_for_question(
    current_user: CurrentUserDep,
    question_id: UUID,
    service: QuestionServiceDep,
) -> list[Assessment]:
    """Get all assessments that include this question."""
    try:
        return await service.get_assessments_for_question(current_user.id, question_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
