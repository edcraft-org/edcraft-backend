"""Dependency injection setup for repositories and services."""

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.database import get_db
from edcraft_backend.models.user import User
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
from edcraft_backend.repositories.oauth_account_repository import OAuthAccountRepository
from edcraft_backend.repositories.one_time_token_repository import (
    OneTimeTokenRepository,
)
from edcraft_backend.repositories.question_bank_question_repository import (
    QuestionBankQuestionRepository,
)
from edcraft_backend.repositories.question_bank_repository import QuestionBankRepository
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.repositories.refresh_token_repository import RefreshTokenRepository
from edcraft_backend.repositories.target_element_repository import (
    TargetElementRepository,
)
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.security import decode_token
from edcraft_backend.services.assessment_service import AssessmentService
from edcraft_backend.services.assessment_template_service import (
    AssessmentTemplateService,
)
from edcraft_backend.services.auth_service import AuthService
from edcraft_backend.services.email_service import EmailService
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.oauth_service import OAuthService
from edcraft_backend.services.question_bank_service import QuestionBankService
from edcraft_backend.services.question_generation_service import (
    QuestionGenerationService,
)
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


def get_question_bank_repository(
    db: AsyncSession = Depends(get_db),
) -> QuestionBankRepository:
    """Get QuestionBankRepository instance."""
    return QuestionBankRepository(db)


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


def get_question_bank_question_repository(
    db: AsyncSession = Depends(get_db),
) -> QuestionBankQuestionRepository:
    """Get QuestionBankQuestionRepository instance."""
    return QuestionBankQuestionRepository(db)


def get_assessment_template_question_template_repository(
    db: AsyncSession = Depends(get_db),
) -> AssessmentTemplateQuestionTemplateRepository:
    """Get AssessmentTemplateQuestionTemplateRepository instance."""
    return AssessmentTemplateQuestionTemplateRepository(db)


def get_target_element_repository(
    db: AsyncSession = Depends(get_db),
) -> TargetElementRepository:
    """Get TargetElementRepository instance."""
    return TargetElementRepository(db)


def get_refresh_token_repository(
    db: AsyncSession = Depends(get_db),
) -> RefreshTokenRepository:
    """Get RefreshTokenRepository instance."""
    return RefreshTokenRepository(db)


def get_oauth_account_repository(
    db: AsyncSession = Depends(get_db),
) -> OAuthAccountRepository:
    """Get OAuthAccountRepository instance."""
    return OAuthAccountRepository(db)


def get_one_time_token_repository(
    db: AsyncSession = Depends(get_db),
) -> OneTimeTokenRepository:
    """Get OneTimeTokenRepository instance."""
    return OneTimeTokenRepository(db)


# Service dependencies
def get_email_service() -> EmailService:
    """Get EmailService instance."""
    return EmailService()


def get_question_service(
    question_repo: QuestionRepository = Depends(get_question_repository),
    assessment_question_repo: AssessmentQuestionRepository = Depends(
        get_assessment_question_repository
    ),
    question_bank_question_repo: QuestionBankQuestionRepository = Depends(
        get_question_bank_question_repository
    ),
) -> QuestionService:
    """Get QuestionService instance."""
    return QuestionService(
        question_repo, assessment_question_repo, question_bank_question_repo
    )


def get_question_template_service(
    template_repo: QuestionTemplateRepository = Depends(
        get_question_template_repository
    ),
    assessment_template_ques_template_repo: AssessmentTemplateQuestionTemplateRepository = Depends(
        get_assessment_template_question_template_repository
    ),
    target_element_repo: TargetElementRepository = Depends(
        get_target_element_repository
    ),
) -> QuestionTemplateService:
    """Get QuestionTemplateService instance."""
    return QuestionTemplateService(
        template_repo, assessment_template_ques_template_repo, target_element_repo
    )


def get_folder_service(
    folder_repo: FolderRepository = Depends(get_folder_repository),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    question_bank_repo: QuestionBankRepository = Depends(get_question_bank_repository),
    assessment_template_repo: AssessmentTemplateRepository = Depends(
        get_assessment_template_repository
    ),
    question_svc: QuestionService = Depends(get_question_service),
    question_template_svc: QuestionTemplateService = Depends(
        get_question_template_service
    ),
) -> FolderService:
    """Get FolderService instance."""
    return FolderService(
        folder_repo,
        assessment_repo,
        question_bank_repo,
        assessment_template_repo,
        question_svc,
        question_template_svc,
    )


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    folder_svc: FolderService = Depends(get_folder_service),
) -> UserService:
    """Get UserService instance."""
    return UserService(user_repo, folder_svc)


def get_assessment_service(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    folder_svc: FolderService = Depends(get_folder_service),
    assessment_question_repo: AssessmentQuestionRepository = Depends(
        get_assessment_question_repository
    ),
    question_svc: QuestionService = Depends(get_question_service),
) -> AssessmentService:
    """Get AssessmentService instance."""
    return AssessmentService(
        assessment_repo, folder_svc, assessment_question_repo, question_svc
    )


def get_question_bank_service(
    question_bank_repo: QuestionBankRepository = Depends(get_question_bank_repository),
    folder_svc: FolderService = Depends(get_folder_service),
    question_bank_question_repo: QuestionBankQuestionRepository = Depends(
        get_question_bank_question_repository
    ),
    question_svc: QuestionService = Depends(get_question_service),
) -> QuestionBankService:
    """Get QuestionBankService instance."""
    return QuestionBankService(
        question_bank_repo, folder_svc, question_bank_question_repo, question_svc
    )


def get_assessment_template_service(
    template_repo: AssessmentTemplateRepository = Depends(
        get_assessment_template_repository
    ),
    folder_svc: FolderService = Depends(get_folder_service),
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
        folder_svc,
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


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    one_time_token_repo: OneTimeTokenRepository = Depends(
        get_one_time_token_repository
    ),
    folder_svc: FolderService = Depends(get_folder_service),
    email_svc: EmailService = Depends(get_email_service),
) -> AuthService:
    """Get AuthService instance."""
    return AuthService(
        user_repo, refresh_token_repo, one_time_token_repo, folder_svc, email_svc
    )


def get_oauth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    oauth_account_repo: OAuthAccountRepository = Depends(get_oauth_account_repository),
    auth_svc: AuthService = Depends(get_auth_service),
    folder_svc: FolderService = Depends(get_folder_service),
) -> OAuthService:
    """Get OAuthService instance."""
    return OAuthService(user_repo, oauth_account_repo, auth_svc, folder_svc)


async def get_current_user(
    user_repo: UserRepository = Depends(get_user_repository),
    access_token: str | None = Cookie(None),
) -> User:
    """Resolve the authenticated user from the access_token httpOnly cookie."""

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = decode_token(access_token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        user = await user_repo.get_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from e


# Type aliases for cleaner router signatures
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
FolderServiceDep = Annotated[FolderService, Depends(get_folder_service)]
QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]
QuestionTemplateServiceDep = Annotated[
    QuestionTemplateService,
    Depends(get_question_template_service),
]
AssessmentServiceDep = Annotated[AssessmentService, Depends(get_assessment_service)]
QuestionBankServiceDep = Annotated[
    QuestionBankService, Depends(get_question_bank_service)
]
AssessmentTemplateServiceDep = Annotated[
    AssessmentTemplateService,
    Depends(get_assessment_template_service),
]
QuestionGenerationServiceDep = Annotated[
    QuestionGenerationService,
    Depends(get_question_generation_service),
]


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

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
QuestionBankRepositoryDep = Annotated[
    QuestionBankRepository, Depends(get_question_bank_repository)
]
AssessmentTemplateRepositoryDep = Annotated[
    AssessmentTemplateRepository,
    Depends(get_assessment_template_repository),
]
OneTimeTokenRepositoryDep = Annotated[
    OneTimeTokenRepository,
    Depends(get_one_time_token_repository),
]
EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
