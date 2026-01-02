"""Shared test fixtures and configuration."""

import os
from collections.abc import AsyncGenerator

# Load test environment BEFORE any app imports
os.environ["APP_ENV"] = "test"

# Now we can import the config (it will load .env.test)
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from edcraft_backend.config import settings  # noqa: E402
from edcraft_backend.database import get_db  # noqa: E402
from edcraft_backend.main import app  # noqa: E402
from edcraft_backend.models.base import Base  # noqa: E402
from tests.mocks.mock_form_builder import MockFormBuilderService  # noqa: E402
from tests.mocks.mock_question_generator import MockQuestionGenerationService  # noqa: E402
from tests.mocks.mock_static_analyser import MockCodeAnalysisService  # noqa: E402


@pytest.fixture(scope="session")
def test_engine() -> AsyncEngine:
    """Create test database engine (session scope)."""
    from sqlalchemy.pool import NullPool

    test_db_url = str(settings.database_url)

    engine = create_async_engine(
        test_db_url,
        echo=False,  # Disable SQL logging in tests
        poolclass=NullPool,
    )
    return engine


@pytest_asyncio.fixture(scope="session")
async def test_db_setup(test_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Create all tables before tests, drop after tests (session scope)."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    test_engine: AsyncEngine, test_db_setup: None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide clean database session per test (function scope).

    Each test runs in an isolated transaction that's rolled back for cleanup.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI AsyncClient with overridden dependencies (function scope).

    Overrides:
    - get_db: Use test database session
    - External services: Use mocks
    """

    # Override get_db dependency to use test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Override external service dependencies with mocks
    def override_question_generation_service() -> MockQuestionGenerationService:
        return MockQuestionGenerationService()

    def override_code_analysis_service() -> MockCodeAnalysisService:
        return MockCodeAnalysisService()

    def override_form_builder_service() -> MockFormBuilderService:
        return MockFormBuilderService()

    # Apply dependency overrides
    app.dependency_overrides[get_db] = override_get_db

    # Import services for override
    from edcraft_backend.services.code_analysis import CodeAnalysisService
    from edcraft_backend.services.form_builder import FormBuilderService
    from edcraft_backend.services.question_generation import QuestionGenerationService

    app.dependency_overrides[QuestionGenerationService] = override_question_generation_service
    app.dependency_overrides[CodeAnalysisService] = override_code_analysis_service
    app.dependency_overrides[FormBuilderService] = override_form_builder_service

    # Create async test client
    # Using raise_app_exceptions=False to prevent worker thread issues
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear dependency overrides after test
    app.dependency_overrides.clear()
