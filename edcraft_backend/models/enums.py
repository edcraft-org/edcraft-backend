"""Enum definitions for database models."""

from enum import StrEnum


class QuestionType(StrEnum):
    """Question types supported by the system."""

    MCQ = "mcq"
    MRQ = "mrq"
    SHORT_ANSWER = "short_answer"


class OutputType(StrEnum):
    """Output types for question generation."""

    LIST = "list"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"


class TargetElementType(StrEnum):
    """Types of code elements that can be targeted."""

    FUNCTION = "function"
    LOOP = "loop"
    BRANCH = "branch"
    VARIABLE = "variable"


class TargetModifier(StrEnum):
    """Modifiers for target elements."""

    ARGUMENTS = "arguments"
    RETURN_VALUE = "return_value"
    LOOP_ITERATIONS = "loop_iterations"
    BRANCH_TRUE = "branch_true"
    BRANCH_FALSE = "branch_false"


class TextTemplateType(StrEnum):
    """Template types for question text templates."""

    BASIC = "basic"
    MUSTACHE = "mustache"


class ResourceVisibility(StrEnum):
    """Visibility settings for resources (assessments, etc.)."""

    PRIVATE = "private"
    PUBLIC = "public"


class CollaboratorRole(StrEnum):
    """Roles for resource collaborators."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"

    @property
    def _level(self) -> int:
        return {"owner": 2, "editor": 1, "viewer": 0}[self.value]

    def __ge__(self, other: object) -> bool:
        if isinstance(other, CollaboratorRole):
            return self._level >= other._level
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, CollaboratorRole):
            return self._level > other._level
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, CollaboratorRole):
            return self._level <= other._level
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, CollaboratorRole):
            return self._level < other._level
        return NotImplemented


class ResourceType(StrEnum):
    """Resource types for the generic collaborator table."""

    ASSESSMENT = "assessment"
    QUESTION_BANK = "question_bank"
    QUESTION_TEMPLATE_BANK = "question_template_bank"
    ASSESSMENT_TEMPLATE = "assessment_template"

    @property
    def resource_name(self) -> str:
        name_map = {
            ResourceType.ASSESSMENT: "Assessment",
            ResourceType.QUESTION_BANK: "Question Bank",
            ResourceType.QUESTION_TEMPLATE_BANK: "Question Template Bank",
            ResourceType.ASSESSMENT_TEMPLATE: "Assessment Template",
        }
        return name_map[self]
