"""Schema exports."""

# User schemas
# Assessment schemas
from edcraft_backend.schemas.assessment import (
    AssessmentQuestionResponse,
    AssessmentResponse,
    AssessmentWithQuestionsResponse,
    CreateAssessmentRequest,
    InsertQuestionIntoAssessmentRequest,
    LinkQuestionToAssessmentRequest,
    ReorderQuestionsInAssessmentRequest,
    UpdateAssessmentRequest,
)

# Assessment Template schemas
from edcraft_backend.schemas.assessment_template import (
    AssessmentTemplateQuestionTemplateResponse,
    AssessmentTemplateResponse,
    AssessmentTemplateWithQuestionTemplatesResponse,
    CreateAssessmentTemplateRequest,
    InsertQuestionTemplateIntoAssessmentTemplateRequest,
    LinkQuestionTemplateToAssessmentTemplateRequest,
    ReorderQuestionTemplatesInAssessmentTemplateRequest,
    UpdateAssessmentTemplateRequest,
)

# Folder schemas
from edcraft_backend.schemas.folder import (
    CreateFolderRequest,
    FolderPathResponse,
    FolderResponse,
    FolderTreeResponse,
    FolderWithContentsResponse,
    MoveFolderRequest,
    UpdateFolderRequest,
)

# Question schemas
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    QuestionResponse,
    UpdateQuestionRequest,
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
    CreateQuestionTemplateRequest,
    QuestionTemplateResponse,
    QuestionTemplateSummaryResponse,
    UpdateQuestionTemplateRequest,
)
from edcraft_backend.schemas.user import (
    UpdateUserRequest,
    UserResponse,
)

__all__ = [
    # User
    "UserResponse",
    "UpdateUserRequest",
    # Folder
    "CreateFolderRequest",
    "MoveFolderRequest",
    "FolderPathResponse",
    "FolderResponse",
    "FolderTreeResponse",
    "UpdateFolderRequest",
    "FolderWithContentsResponse",
    # Question
    "CreateQuestionRequest",
    "QuestionResponse",
    "UpdateQuestionRequest",
    # Assessment
    "InsertQuestionIntoAssessmentRequest",
    "CreateAssessmentRequest",
    "LinkQuestionToAssessmentRequest",
    "ReorderQuestionsInAssessmentRequest",
    "AssessmentResponse",
    "AssessmentQuestionResponse",
    "UpdateAssessmentRequest",
    "AssessmentWithQuestionsResponse",
    # Question Template
    "CreateQuestionTemplateRequest",
    "QuestionTemplateSummaryResponse",
    "QuestionTemplateResponse",
    "UpdateQuestionTemplateRequest",
    # Assessment Template
    "CreateAssessmentTemplateRequest",
    "InsertQuestionTemplateIntoAssessmentTemplateRequest",
    "LinkQuestionTemplateToAssessmentTemplateRequest",
    "AssessmentTemplateQuestionTemplateResponse",
    "ReorderQuestionTemplatesInAssessmentTemplateRequest",
    "AssessmentTemplateResponse",
    "UpdateAssessmentTemplateRequest",
    "AssessmentTemplateWithQuestionTemplatesResponse",
    # Question Generation
    "CodeAnalysisRequest",
    "CodeAnalysisResponse",
    "GenerateFromTemplateRequest",
    "GenerateIntoAssessmentRequest",
    "QuestionGenerationRequest",
]
