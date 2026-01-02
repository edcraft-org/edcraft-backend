"""Schema exports."""

# User schemas
# Assessment schemas
from edcraft_backend.schemas.assessment import (
    AssessmentCreate,
    AssessmentInsertQuestion,
    AssessmentLinkQuestion,
    AssessmentQuestionResponse,
    AssessmentReorderQuestions,
    AssessmentResponse,
    AssessmentUpdate,
    AssessmentWithQuestions,
)

# Assessment Template schemas
from edcraft_backend.schemas.assessment_template import (
    AssessmentTemplateCreate,
    AssessmentTemplateInsertQuestionTemplate,
    AssessmentTemplateLinkQuestionTemplate,
    AssessmentTemplateQuestionTemplateResponse,
    AssessmentTemplateReorderQuestionTemplates,
    AssessmentTemplateResponse,
    AssessmentTemplateUpdate,
    AssessmentTemplateWithQuestionTemplates,
)

# Folder schemas
from edcraft_backend.schemas.folder import (
    FolderCreate,
    FolderList,
    FolderMove,
    FolderPath,
    FolderResponse,
    FolderTree,
    FolderUpdate,
    FolderWithContents,
)

# Question schemas
from edcraft_backend.schemas.question import (
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)

# Question Generation schemas
from edcraft_backend.schemas.question_generation import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    GenerateFromTemplateRequest,
    GenerateIntoAssessmentRequest,
    QuestionGenerationRequest,
)

# Question Template schemas
from edcraft_backend.schemas.question_template import (
    QuestionTemplateCreate,
    QuestionTemplateList,
    QuestionTemplateResponse,
    QuestionTemplateUpdate,
)
from edcraft_backend.schemas.user import (
    UserCreate,
    UserList,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserList",
    "UserResponse",
    "UserUpdate",
    # Folder
    "FolderCreate",
    "FolderList",
    "FolderMove",
    "FolderPath",
    "FolderResponse",
    "FolderTree",
    "FolderUpdate",
    "FolderWithContents",
    # Question
    "QuestionCreate",
    "QuestionResponse",
    "QuestionUpdate",
    # Assessment
    "AssessmentInsertQuestion",
    "AssessmentCreate",
    "AssessmentLinkQuestion",
    "AssessmentReorderQuestions",
    "AssessmentResponse",
    "AssessmentQuestionResponse",
    "AssessmentUpdate",
    "AssessmentWithQuestions",
    # Question Template
    "QuestionTemplateCreate",
    "QuestionTemplateList",
    "QuestionTemplateResponse",
    "QuestionTemplateUpdate",
    # Assessment Template
    "AssessmentTemplateCreate",
    "AssessmentTemplateInsertQuestionTemplate",
    "AssessmentTemplateLinkQuestionTemplate",
    "AssessmentTemplateQuestionTemplateResponse",
    "AssessmentTemplateReorderQuestionTemplates",
    "AssessmentTemplateResponse",
    "AssessmentTemplateUpdate",
    "AssessmentTemplateWithQuestionTemplates",
    # Question Generation
    "CodeAnalysisRequest",
    "CodeAnalysisResponse",
    "GenerateFromTemplateRequest",
    "GenerateIntoAssessmentRequest",
    "QuestionGenerationRequest",
]
