"""Question endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import QuestionServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.question import Question
from edcraft_backend.schemas.assessment import (
    AssessmentResponse,
)
from edcraft_backend.schemas.question import (
    QuestionResponse,
    QuestionUpdate,
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    service: QuestionServiceDep,
    owner_id: UUID = Query(..., description="Owner ID to filter questions"),
) -> list[Question]:
    """List questions by owner."""
    try:
        return await service.list_questions(owner_id=owner_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: UUID, service: QuestionServiceDep) -> Question:
    """Get a question by ID."""
    try:
        return await service.get_question(question_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID, question_data: QuestionUpdate, service: QuestionServiceDep
) -> Question:
    """Update a question."""
    try:
        return await service.update_question(question_id, question_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_question(question_id: UUID, service: QuestionServiceDep) -> None:
    """Soft delete a question."""
    try:
        await service.soft_delete_question(question_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{question_id}/assessments", response_model=list[AssessmentResponse])
async def get_assessments_for_question(
    question_id: UUID,
    service: QuestionServiceDep,
    owner_id: UUID = Query(..., description="Owner ID to verify ownership"),
) -> list[Assessment]:
    """Get all assessments that include this question.

    The user must own the question to see which assessments use it.
    """
    try:
        return await service.get_assessments_for_question(question_id, owner_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
