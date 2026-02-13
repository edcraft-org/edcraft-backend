"""Enum definitions for database models."""

from enum import Enum


class QuestionType(str, Enum):
    """Question types supported by the system."""

    MCQ = "mcq"
    MRQ = "mrq"
    SHORT_ANSWER = "short_answer"

    def __str__(self) -> str:
        return self.value


class OutputType(str, Enum):
    """Output types for question generation."""

    LIST = "list"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"

    def __str__(self) -> str:
        return self.value


class TargetElementType(str, Enum):
    """Types of code elements that can be targeted."""

    FUNCTION = "function"
    LOOP = "loop"
    BRANCH = "branch"
    VARIABLE = "variable"

    def __str__(self) -> str:
        return self.value


class TargetModifier(str, Enum):
    """Modifiers for target elements."""

    ARGUMENTS = "arguments"
    RETURN_VALUE = "return_value"
    LOOP_ITERATIONS = "loop_iterations"
    BRANCH_TRUE = "branch_true"
    BRANCH_FALSE = "branch_false"

    def __str__(self) -> str:
        return self.value
