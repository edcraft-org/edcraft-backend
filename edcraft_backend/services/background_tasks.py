"""Background task utilities for non-blocking operations."""

import asyncio
import logging
from uuid import UUID

from edcraft_backend.database import AsyncSessionLocal
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.services.enums import ResourceType
from edcraft_backend.services.question_service import QuestionService
from edcraft_backend.services.question_template_service import QuestionTemplateService

logger = logging.getLogger(__name__)


def schedule_cleanup_orphaned_resources(owner_id: UUID, resource_type: ResourceType) -> None:
    """
    Schedule cleanup of orphaned resources in the background.

    This is a fire-and-forget operation that won't block the endpoint response.

    Args:
        owner_id: User ID to limit cleanup to
        resource_type: Type of resource to clean up

    Example:
        # In your delete service method
        deleted_assessment = await service.soft_delete_assessment(assessment_id)

        # Schedule cleanup in background (non-blocking)
        schedule_cleanup_orphaned_resources(user_id, resource_type=ResourceType.ASSESSMENTS)

        # Return immediately
        return deleted_assessment
    """
    if resource_type == ResourceType.QUESTIONS:
        asyncio.create_task(_cleanup_orphaned_questions_task(owner_id))
    elif resource_type == ResourceType.TEMPLATES:
        asyncio.create_task(_cleanup_orphaned_question_templates_task(owner_id))
    else:
        logger.error(f"Unknown resource type for cleanup: {resource_type}")


async def _cleanup_orphaned_questions_task(owner_id: UUID) -> None:
    """
    Background task to clean up orphaned questions using repository layer.

    Creates its own database session to avoid conflicts with the request session.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Create repository instance
            question_repo = QuestionRepository(session)

            # Create service instance
            question_svc = QuestionService(question_repo)

            # Call service cleanup method
            questions_deleted = await question_svc.cleanup_orphaned_questions(owner_id)

            logger.info(
                f"Background cleanup completed for user {owner_id}: "
                f"{questions_deleted} questions deleted"
            )
    except Exception as e:
        # Log error but don't raise - this is a background task
        logger.error(
            f"Background cleanup failed for user {owner_id}: {e}", exc_info=True
        )


async def _cleanup_orphaned_question_templates_task(owner_id: UUID) -> None:
    """
    Background task to clean up orphaned question templates using repository layer.

    Creates its own database session to avoid conflicts with the request session.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Create repository instance
            question_template_repo = QuestionTemplateRepository(session)

            # Create service instance
            template_svc = QuestionTemplateService(question_template_repo)

            # Call service cleanup method
            templates_deleted = await template_svc.cleanup_orphaned_templates(owner_id)

            logger.info(
                f"Background cleanup completed for user {owner_id}: "
                f"{templates_deleted} question templates deleted"
            )
    except Exception as e:
        # Log error but don't raise - this is a background task
        logger.error(
            f"Background cleanup failed for user {owner_id}: {e}", exc_info=True
        )
