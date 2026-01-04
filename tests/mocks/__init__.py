"""Mock implementations for external dependencies.

This package provides mock implementations for external services and engines used
in the EdCraft backend. Mocks enable isolated testing without external dependencies.

Available Mocks:
    MockQuestionGenerator: Mocks edcraft_engine.question_generator.QuestionGenerator
    MockStaticAnalyser: Mocks edcraft_engine.static_analyser.StaticAnalyser

Usage:
    from tests.mocks import MockQuestionGenerator, MockStaticAnalyser

    # Use in tests or fixtures
    mock_gen = MockQuestionGenerator()
    mock_analyser = MockStaticAnalyser()

    # Or use factory helpers for common scenarios
    from tests.mocks.factories import create_static_analyser_with_function

Organization:
    - engine/: Mocks for EdCraft Engine components
    - factories.py: Helper functions for creating pre-configured mocks
"""

from tests.mocks.engine import MockQuestionGenerator, MockStaticAnalyser

__all__ = ["MockQuestionGenerator", "MockStaticAnalyser"]
