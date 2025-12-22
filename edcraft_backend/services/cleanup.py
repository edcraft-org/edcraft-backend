"""Cleanup utilities for database maintenance."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question import Question
from edcraft_backend.models.question_template import QuestionTemplate


async def delete_orphaned_questions(session: AsyncSession, owner_id: UUID | None = None) -> int:
    """
    Delete questions that are not associated with any assessments.

    Args:
        session: Database session
        owner_id: Optional user ID to limit cleanup to specific user's questions.
                 If None, cleans up orphaned questions for all users.

    Returns:
        Number of questions deleted

    Example:
        # Clean up all orphaned questions for a specific user
        deleted_count = await delete_orphaned_questions(session, user_id)

        # Clean up all orphaned questions globally (admin operation)
        deleted_count = await delete_orphaned_questions(session)
    """
    # Subquery to find questions that have at least one assessment association
    questions_with_assessments = (
        select(Question.id)
        .join(Question.assessment_associations)
        .where(Question.deleted_at.is_(None))
    )

    if owner_id:
        questions_with_assessments = questions_with_assessments.where(Question.owner_id == owner_id)

    # Build delete query for questions NOT in the subquery
    delete_query = delete(Question).where(
        Question.id.not_in(questions_with_assessments),
        Question.deleted_at.is_(None),
    )

    if owner_id:
        delete_query = delete_query.where(Question.owner_id == owner_id)

    # Execute delete and return count
    result = await session.execute(delete_query)
    await session.commit()

    return result.rowcount # type: ignore[attr-defined]


async def delete_orphaned_question_templates(
    session: AsyncSession, owner_id: UUID | None = None
) -> int:
    """
    Delete question templates that are not associated with any assessment templates.

    Args:
        session: Database session
        owner_id: Optional user ID to limit cleanup to specific user's templates.
                 If None, cleans up orphaned templates for all users.

    Returns:
        Number of question templates deleted

    Example:
        # Clean up all orphaned question templates for a specific user
        deleted_count = await delete_orphaned_question_templates(session, user_id)
    """
    # Subquery to find question templates that have at least one assessment template association
    templates_with_assessments = (
        select(QuestionTemplate.id)
        .join(QuestionTemplate.assessment_template_associations)
        .where(QuestionTemplate.deleted_at.is_(None))
    )

    if owner_id:
        templates_with_assessments = templates_with_assessments.where(
            QuestionTemplate.owner_id == owner_id
        )

    # Build delete query for question templates NOT in the subquery
    delete_query = delete(QuestionTemplate).where(
        QuestionTemplate.id.not_in(templates_with_assessments),
        QuestionTemplate.deleted_at.is_(None),
    )

    if owner_id:
        delete_query = delete_query.where(QuestionTemplate.owner_id == owner_id)

    # Execute delete and return count
    result = await session.execute(delete_query)
    await session.commit()

    return result.rowcount # type: ignore[attr-defined]


async def cleanup_orphaned_resources(
    session: AsyncSession, owner_id: UUID | None = None
) -> dict[str, int]:
    """
    Clean up all orphaned resources (questions and question templates).

    This function should be called:
    1. After deleting folders, assessments, or assessment templates
    2. Periodically as a background job

    Args:
        session: Database session
        owner_id: Optional user ID to limit cleanup to specific user

    Returns:
        Dictionary with counts of deleted resources:
        {
            "questions_deleted": int,
            "question_templates_deleted": int,
            "total_deleted": int
        }

    Example:
        # Clean up after deleting a folder
        result = await cleanup_orphaned_resources(session, user_id)
        print(f"Cleaned up {result['total_deleted']} orphaned resources")
    """
    questions_deleted = await delete_orphaned_questions(session, owner_id)
    templates_deleted = await delete_orphaned_question_templates(session, owner_id)

    return {
        "questions_deleted": questions_deleted,
        "question_templates_deleted": templates_deleted,
        "total_deleted": questions_deleted + templates_deleted,
    }
