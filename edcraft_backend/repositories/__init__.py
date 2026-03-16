from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.repositories.assessment_template_repository import AssessmentTemplateRepository
from edcraft_backend.repositories.base import AssociationRepository, EntityRepository
from edcraft_backend.repositories.folder_repository import FolderRepository
from edcraft_backend.repositories.job_repository import JobRepository, JobTokenRepository
from edcraft_backend.repositories.question_bank_repository import QuestionBankRepository
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.repositories.question_template_bank_repository import (
    QuestionTemplateBankRepository,
)
from edcraft_backend.repositories.question_template_repository import QuestionTemplateRepository
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.repositories.target_element_repository import TargetElementRepository
from edcraft_backend.repositories.user_repository import UserRepository

__all__ = [
    "EntityRepository",
    "AssociationRepository",
    "UserRepository",
    "FolderRepository",
    "JobRepository",
    "JobTokenRepository",
    "QuestionBankRepository",
    "QuestionRepository",
    "QuestionTemplateRepository",
    "QuestionTemplateBankRepository",
    "AssessmentRepository",
    "AssessmentTemplateRepository",
    "TargetElementRepository",
    "ResourceCollaboratorRepository",
]
