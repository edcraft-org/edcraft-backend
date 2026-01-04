"""Dependency injection setup for repositories and services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.database import get_db
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.repositories.assessment_template_question_template_repository import (
    AssessmentTemplateQuestionTemplateRepository,
)
from edcraft_backend.repositories.assessment_template_repository import (
    AssessmentTemplateRepository,
)
from edcraft_backend.repositories.folder_repository import FolderRepository
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.services.assessment_service import AssessmentService
from edcraft_backend.services.assessment_template_service import (
    AssessmentTemplateService,
)
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.question_generation_service import QuestionGenerationService
from edcraft_backend.services.question_service import QuestionService
from edcraft_backend.services.question_template_service import QuestionTemplateService
from edcraft_backend.services.user_service import UserService


# Repository dependencies
def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get UserRepository instance."""
    return UserRepository(db)


def get_folder_repository(db: AsyncSession = Depends(get_db)) -> FolderRepository:
    """Get FolderRepository instance."""
    return FolderRepository(db)


def get_question_repository(db: AsyncSession = Depends(get_db)) -> QuestionRepository:
    """Get QuestionRepository instance."""
    return QuestionRepository(db)


def get_question_template_repository(
    db: AsyncSession = Depends(get_db),
) -> QuestionTemplateRepository:
    """Get QuestionTemplateRepository instance."""
    return QuestionTemplateRepository(db)


def get_assessment_repository(
    db: AsyncSession = Depends(get_db),
) -> AssessmentRepository:
    """Get AssessmentRepository instance."""
    return AssessmentRepository(db)


def get_assessment_template_repository(
    db: AsyncSession = Depends(get_db),
) -> AssessmentTemplateRepository:
    """Get AssessmentTemplateRepository instance."""
    return AssessmentTemplateRepository(db)


def get_assessment_question_repository(
    db: AsyncSession = Depends(get_db),
) -> AssessmentQuestionRepository:
    """Get AssessmentQuestionRepository instance."""
    return AssessmentQuestionRepository(db)


def get_assessment_template_question_template_repository(
    db: AsyncSession = Depends(get_db),
) -> AssessmentTemplateQuestionTemplateRepository:
    """Get AssessmentTemplateQuestionTemplateRepository instance."""
    return AssessmentTemplateQuestionTemplateRepository(db)


# Service dependencies
def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Get UserService instance."""
    return UserService(user_repo)


def get_folder_service(
    folder_repo: FolderRepository = Depends(get_folder_repository),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    assessment_template_repo: AssessmentTemplateRepository = Depends(
        get_assessment_template_repository
    ),
) -> FolderService:
    """Get FolderService instance."""
    return FolderService(folder_repo, assessment_repo, assessment_template_repo)


def get_question_service(
    question_repo: QuestionRepository = Depends(get_question_repository),
) -> QuestionService:
    """Get QuestionService instance."""
    return QuestionService(question_repo)


def get_question_template_service(
    template_repo: QuestionTemplateRepository = Depends(
        get_question_template_repository
    ),
) -> QuestionTemplateService:
    """Get QuestionTemplateService instance."""
    return QuestionTemplateService(template_repo)


def get_assessment_service(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    assessment_question_repo: AssessmentQuestionRepository = Depends(
        get_assessment_question_repository
    ),
    question_svc: QuestionService = Depends(get_question_service),
) -> AssessmentService:
    """Get AssessmentService instance."""
    return AssessmentService(
        assessment_repo, folder_repo, assessment_question_repo, question_svc
    )


def get_assessment_template_service(
    template_repo: AssessmentTemplateRepository = Depends(
        get_assessment_template_repository
    ),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    question_template_svc: QuestionTemplateService = Depends(
        get_question_template_service
    ),
    assoc_repo: AssessmentTemplateQuestionTemplateRepository = Depends(
        get_assessment_template_question_template_repository
    ),
) -> AssessmentTemplateService:
    """Get AssessmentTemplateService instance."""
    return AssessmentTemplateService(
        template_repo,
        folder_repo,
        question_template_svc,
        assoc_repo,
    )

def get_question_generation_service(
    question_template_svc: QuestionTemplateService = Depends(
        get_question_template_service
    ),
    assessment_template_svc: AssessmentTemplateService = Depends(
        get_assessment_template_service
    ),
    assessment_svc: AssessmentService = Depends(get_assessment_service),
) -> QuestionGenerationService:
    """Get QuestionGenerationService instance."""
    return QuestionGenerationService(
        question_template_svc,
        assessment_template_svc,
        assessment_svc,
    )


# Type aliases for cleaner router signatures
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
FolderServiceDep = Annotated[FolderService, Depends(get_folder_service)]
QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]
QuestionTemplateServiceDep = Annotated[
    QuestionTemplateService,
    Depends(get_question_template_service),
]
AssessmentServiceDep = Annotated[AssessmentService, Depends(get_assessment_service)]
AssessmentTemplateServiceDep = Annotated[
    AssessmentTemplateService,
    Depends(get_assessment_template_service),
]
QuestionGenerationServiceDep = Annotated[
    QuestionGenerationService,
    Depends(get_question_generation_service),
]

# Repository type aliases
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
FolderRepositoryDep = Annotated[FolderRepository, Depends(get_folder_repository)]
QuestionRepositoryDep = Annotated[QuestionRepository, Depends(get_question_repository)]
QuestionTemplateRepositoryDep = Annotated[
    QuestionTemplateRepository,
    Depends(get_question_template_repository),
]
AssessmentRepositoryDep = Annotated[
    AssessmentRepository, Depends(get_assessment_repository)
]
AssessmentTemplateRepositoryDep = Annotated[
    AssessmentTemplateRepository,
    Depends(get_assessment_template_repository),
]
