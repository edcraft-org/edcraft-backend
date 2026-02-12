"""Database models."""

from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.assessment_template_question_template import (
    AssessmentTemplateQuestionTemplate,
)
from edcraft_backend.models.base import AssociationBase, Base, EntityBase
from edcraft_backend.models.folder import Folder
from edcraft_backend.models.oauth_account import OAuthAccount
from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_data import MCQData, MRQData, ShortAnswerData
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.refresh_token import RefreshToken
from edcraft_backend.models.user import User

__all__ = [
    "User",
    "Folder",
    "Assessment",
    "AssessmentQuestion",
    "Question",
    "MCQData",
    "MRQData",
    "ShortAnswerData",
    "AssessmentTemplate",
    "AssessmentTemplateQuestionTemplate",
    "QuestionTemplate",
    "OAuthAccount",
    "RefreshToken",
    "OneTimeToken",
    "TokenType",
    "Base",
    "AssociationBase",
    "EntityBase",
]
