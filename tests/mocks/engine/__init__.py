"""Mock implementations for EdCraft Engine components.

This module provides mock implementations of external EdCraft Engine components:
- MockQuestionGenerator: Mocks the question generation
- MockStaticAnalyser: Mocks the static code analysis

These mocks enable testing backend services without depending on the external engine.
"""

from tests.mocks.engine.question_generator import MockQuestionGenerator
from tests.mocks.engine.static_analyser import MockStaticAnalyser

__all__ = ["MockQuestionGenerator", "MockStaticAnalyser"]
