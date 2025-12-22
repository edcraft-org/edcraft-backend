"""Background task utilities for non-blocking operations."""

import asyncio
import logging
from uuid import UUID

from edcraft_backend.database import AsyncSessionLocal
from edcraft_backend.services.cleanup import cleanup_orphaned_resources

logger = logging.getLogger(__name__)


def schedule_cleanup_orphaned_resources(owner_id: UUID) -> None:
    """
    Schedule cleanup of orphaned resources in the background.

    This is a fire-and-forget operation that won't block the endpoint response.

    Args:
        owner_id: User ID to limit cleanup to

    Example:
        # In your delete endpoint
        await db.delete(folder)
        await db.commit()

        # Schedule cleanup in background (non-blocking)
        schedule_cleanup_orphaned_resources(user_id)

        # Return immediately
        return {"message": "Folder deleted successfully"}
    """
    asyncio.create_task(_cleanup_orphaned_resources_task(owner_id))


async def _cleanup_orphaned_resources_task(owner_id: UUID) -> None:
    """
    Background task to clean up orphaned resources.

    Creates its own database session to avoid conflicts with the request session.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await cleanup_orphaned_resources(session, owner_id)
            logger.info(
                f"Background cleanup completed for user {owner_id}: "
                f"{result['questions_deleted']} questions, "
                f"{result['question_templates_deleted']} question templates deleted"
            )
    except Exception as e:
        # Log error but don't raise - this is a background task
        logger.error(f"Background cleanup failed for user {owner_id}: {e}", exc_info=True)
