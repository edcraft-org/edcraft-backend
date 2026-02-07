"""Mock implementations for external dependencies.

This package provides mock implementations for external services and engines used
in the EdCraft backend. Mocks enable isolated testing without external dependencies.

Available Mocks:
    MockQuestionGenerator: Mocks edcraft_engine.question_generator.QuestionGenerator
    MockStaticAnalyser: Mocks edcraft_engine.static_analyser.StaticAnalyser
    MockOAuthClient: Mocks Authlib OAuth client for OAuth testing
    MockOAuthRegistry: Mocks OAuth registry for managing OAuth providers

Usage:
    from tests.mocks import MockQuestionGenerator, MockStaticAnalyser

    # Use in tests or fixtures
    mock_gen = MockQuestionGenerator()
    mock_analyser = MockStaticAnalyser()

    # OAuth testing
    from tests.mocks import MockOAuthRegistry, create_mock_oauth_user_info
    mock_oauth = MockOAuthRegistry()

    # Or use factory helpers for common scenarios
    from tests.mocks.factories import create_static_analyser_with_function

Organization:
    - engine/: Mocks for EdCraft Engine components
    - oauth_client.py: Mocks for OAuth clients
    - factories.py: Helper functions for creating pre-configured mocks
"""

from tests.mocks.engine import MockQuestionGenerator, MockStaticAnalyser
from tests.mocks.oauth_client import (
    MockOAuthClient,
    MockOAuthRegistry,
    create_mock_oauth_user_info,
)

__all__ = [
    "MockQuestionGenerator",
    "MockStaticAnalyser",
    "MockOAuthClient",
    "MockOAuthRegistry",
    "create_mock_oauth_user_info",
]
