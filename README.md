# EdCraft Backend

FastAPI wrapper for the EdCraft Engine, providing a REST API for question generation and management.

## Overview

EdCraft Backend is a FastAPI-based web service that exposes the EdCraft Engine functionality through HTTP endpoints. It serves as the backend API for EdCraft applications.

## Features

- FastAPI framework with automatic OpenAPI documentation
- CORS middleware configured via environment variables
- Type-safe API with Pydantic models
- Structured project layout with routers, services, and schemas
- Comprehensive development tooling (pytest, mypy, ruff)

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd edcraft-backend
```

2. Install dependencies using uv:
```bash
uv sync
```

The project depends on the `edcraft-engine` package, which should be located at `../edcraft-engine` relative to this directory (configured as an editable dependency).

3. Set up environment variables:

The application uses environment-specific .env files:

```bash
# Create development environment file
cp .env.example .env.development

# Create test environment file
cp .env.example .env.test

# Edit the files and configure your database credentials
```

Set the `APP_ENV` environment variable to select which configuration to use:

```bash
# For development (default)
export APP_ENV=development

# For testing
export APP_ENV=test

# For production
export APP_ENV=production
```

See the [Configuration](#configuration) section for detailed information about environment management.

4. Start the local PostgreSQL database:
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
uv run alembic upgrade head
```

## Development

### Running the Server

Start the development server with auto-reload:

```bash
# 1. Start the database (runs in background)
docker compose up -d

# 2. Verify database is running
docker compose ps

# 3. Start the FastAPI development server
make dev
# or
uv run uvicorn edcraft_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- Main API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Alternative docs: http://127.0.0.1:8000/redoc

**Note:** The database runs in the background and stays running until you stop it with `docker compose down`. You only need to start it once per session.

### Running Tests

Tests require the test database to be running.

```bash
# Option 1: Automatic - starts test DB, runs tests, stops test DB
make test-with-db

# Option 2: Manual control
make db-test        # Start test database
make test           # Run tests
make db-down        # Stop test database when done
```

Run with coverage:

```bash
make db-test  # Ensure test database is running
uv run pytest --cov=edcraft_backend --cov-report=html
```

**Test Database Configuration:**
- Tests use a separate PostgreSQL container on port 5433
- Configuration is automatically loaded from `.env.test` (set `APP_ENV=test`)
- Each test runs in an isolated transaction that is rolled back after completion
- Test database schema is created once per test session and torn down afterward

### Code Quality

Run all checks (linting, type checking, and tests):

```bash
make all-checks
```

Individual commands:

```bash
# Type checking with mypy
make type-check
# or
uv run mypy .

# Linting with ruff
make lint
# or
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

## Project Structure

```
edcraft-backend/
├── edcraft_backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app initialization
│   ├── database.py              # Database session management
│   ├── exceptions.py            # Custom exception classes
│   ├── forms_config.json        # Form configuration (JSON)
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── environments.py      # Environment enum
│   │   └── settings.py          # Pydantic settings
│   ├── models/                  # SQLAlchemy database models
│   │   ├── user.py
│   │   ├── folder.py
│   │   ├── assessment.py
│   │   ├── assessment_question.py
│   │   ├── question.py
│   │   ├── assessment_template.py
│   │   ├── assessment_template_question_template.py
│   │   └── question_template.py
│   ├── routers/                 # API route handlers
│   │   ├── users.py
│   │   ├── folders.py
│   │   ├── assessments.py
│   │   ├── questions.py
│   │   ├── assessment_templates.py
│   │   ├── question_templates.py
│   │   └── question_generation.py
│   ├── schemas/                 # Pydantic models for validation
│   │   ├── user.py
│   │   ├── folder.py
│   │   ├── assessment.py
│   │   ├── question.py
│   │   ├── assessment_template.py
│   │   ├── question_template.py
│   │   ├── code_info.py
│   │   ├── form_builder.py
│   │   └── question_generation.py
│   └── services/                # Business logic
│       ├── user_service.py
│       ├── folder_service.py
│       ├── assessment_service.py
│       ├── question_service.py
│       ├── assessment_template_service.py
│       ├── question_template_service.py
│       ├── code_analysis_service.py
│       ├── form_builder_service.py
│       └── question_generation_service.py
├── alembic/                     # Database migrations
│   └── versions/
├── tests/                       # Test suite
│   └── __init__.py
├── docker-compose.yml           # PostgreSQL container
├── Makefile                     # Development commands
├── pyproject.toml               # Project configuration
└── README.md
```

## Database

### Database Setup

The application uses PostgreSQL with async SQLAlchemy for data persistence. There are separate databases for development and testing.

#### Development Database

Using Docker Compose:

```bash
# Start PostgreSQL in the background
docker compose --profile default up -d
# or use the Makefile
make db-dev

# Check database status
docker compose ps

# View database logs
docker compose logs -f postgres

# Stop the database
docker compose down

# Stop and remove all data (destructive!)
docker compose down -v
```

**Accessing the Development Database**

Connect to the database using psql:

```bash
docker exec -it edcraft-postgres psql -U edcraft_dev -d edcraft

# Common psql commands once connected:
# \dt              - List all tables
# \d table_name    - Describe table structure
# SELECT * FROM table_name;  - View table contents
# \q               - Quit psql
```

#### Test Database

The test database runs on a separate container with separate credentials:

```bash
# Start test database
make db-test
# or
docker compose --profile test up -d

# Run tests (assumes test database is running)
make test

# Convenience command: start test DB, run tests, and stop test DB
make test-with-db

# Stop test database
make db-down
```

**Accessing the Test Database:**
```bash
docker exec -it edcraft-postgres-test psql -U edcraft_user -d edcraft_test
```

#### Database Migrations

The project uses Alembic for database migrations. Set `APP_ENV` when running Alembic commands to ensure it connects to the correct database:

```bash
# Run all pending migrations
APP_ENV=development uv run alembic upgrade head

# Create a new migration (after modifying models)
APP_ENV=development uv run alembic revision --autogenerate -m "description of changes"

# Rollback the last migration
APP_ENV=development uv run alembic downgrade -1

# View migration history
APP_ENV=development uv run alembic history

# View current migration version
APP_ENV=development uv run alembic current

# For test database, use APP_ENV=test
APP_ENV=test uv run alembic upgrade head
```

#### Database Schema

The application uses a comprehensive database schema for managing assessments, questions, and organizational structure:

```mermaid
erDiagram
    users ||--o{ folders : "owns"
    users ||--o{ assessments : "owns"
    users ||--o{ assessment_templates : "owns"
    users ||--o{ questions : "owns"
    users ||--o{ question_templates : "owns"

    folders ||--o{ folders : "contains (parent-child)"
    folders ||--o{ assessments : "contains"
    folders ||--o{ assessment_templates : "contains"

    assessments ||--o{ assessment_questions : "has"
    questions ||--o{ assessment_questions : "belongs to"

    assessment_templates ||--o{ assessment_template_question_templates : "has"
    question_templates ||--o{ assessment_template_question_templates : "belongs to"

    question_templates ||--o{ questions : "generates"

    users {
        uuid id PK
        string email UK
        string username UK
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    folders {
        uuid id PK
        uuid owner_id FK
        uuid parent_id FK "nullable"
        string name
        text description "nullable"
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    assessments {
        uuid id PK
        uuid owner_id FK
        uuid folder_id FK "nullable"
        string title
        text description "nullable"
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    questions {
        uuid id PK
        uuid owner_id FK
        uuid template_id FK "nullable, SET NULL"
        string question_type
        text question_text
        json additional_data
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    assessment_questions {
        uuid assessment_id FK,PK
        uuid question_id FK,PK
        int order "unique per assessment"
        datetime created_at
    }

    assessment_templates {
        uuid id PK
        uuid owner_id FK
        uuid folder_id FK "nullable"
        string title
        text description "nullable"
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    question_templates {
        uuid id PK
        uuid owner_id FK
        string question_type
        text question_text
        json template_config
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    assessment_template_question_templates {
        uuid assessment_template_id FK,PK
        uuid question_template_id FK,PK
        int order
        datetime created_at
    }
```

#### Database Models

The application uses a comprehensive database schema for managing assessments, questions, and organizational structure:

- **User** ([user.py](edcraft_backend/models/user.py)) - User accounts
  - Fields: email, username
  - Owns all content (folders, assessments, questions, templates)

- **Folder** ([folder.py](edcraft_backend/models/folder.py)) - Hierarchical folder organization using tree structure
  - Self-referential parent-child relationship
  - Contains sub-folders, assessments and assessment templates
  - Unique constraint: folder names must be unique per parent and user
  - CASCADE delete: 
    - deleting a folder removes all contents, but shared questions/templates are preserved if referenced elsewhere

- **Assessment** ([assessment.py](edcraft_backend/models/assessment.py)) - Collection of questions, also serves as question bank
  - Many-to-many relationship with questions

- **Question** ([question.py](edcraft_backend/models/question.py)) - Individual question instances
  - Hybrid structure: fixed columns + JSON for flexibility
  - Can be created from a QuestionTemplate
  - Reusable across multiple assessments
  - Questions must belong to an assessment

- **AssessmentQuestion** ([assessment_question.py](edcraft_backend/models/assessment_question.py)) - Association table for assessments and questions
  - Tracks question ordering within assessments (0-indexed)
  - Unique constraints:
    - Each question can only be added once per assessment
    - Each order position must be unique within an assessment
  - **Question Ordering Behavior:**
    - Orders are 0-indexed and always consecutive (0, 1, 2, 3...)
    - Insert behavior: Adding a question at a specific order shifts subsequent questions down
    - Valid order range: 0 to current question count (inclusive)
    - Omit order parameter to append to the end
    - Automatic normalization after deletions to maintain consecutive ordering

- **AssessmentTemplate** ([assessment_template.py](edcraft_backend/models/assessment_template.py)) - Collection of question templates, serves as question template bank
  - Many-to-many relationship with question templates

- **QuestionTemplate** ([question_template.py](edcraft_backend/models/question_template.py)) - Blueprint for creating questions
  - Hybrid structure: fixed columns + JSON for flexibility
  - Used to generate Question instances
  - Questions templates must belong to an assessment template

- **AssessmentTemplateQuestionTemplate** ([assessment_template_question_template.py](edcraft_backend/models/assessment_template_question_template.py)) - Association table
  - Tracks template ordering within assessment templates (0-indexed)
  - Unique constraints:
    - Each question template can only be added once per assessment template
    - Each order position must be unique within an assessment template
  - **Question Template Ordering Behavior:**
    - Orders are 0-indexed and always consecutive (0, 1, 2, 3...)
    - Insert behavior: Adding a question template at a specific order shifts subsequent templates down
    - Valid order range: 0 to current question template count (inclusive)
    - Omit order parameter to append to the end
    - Automatic normalization after deletions to maintain consecutive ordering

**Working with Models:**

When creating new models:

1. Create your SQLAlchemy model inheriting from `Base`
2. Import the model in [edcraft_backend/models/\_\_init\_\_.py](edcraft_backend/models/__init__.py)
3. Import models in [alembic/env.py](alembic/env.py) for autogenerate to detect them
4. Generate a migration: `uv run alembic revision --autogenerate -m "add model_name"`
5. Review the generated migration file
6. Apply the migration: `uv run alembic upgrade head`

#### Connection to Database

The application automatically manages database connections through FastAPI's dependency injection:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from edcraft_backend.database import get_db

@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    # Use db session here
    result = await db.execute(select(Item))
    return result.scalars().all()
```

## Configuration

The application uses **Pydantic BaseSettings** for type-safe, environment-based configuration with environment-specific .env files.

### Environment Files

Configuration is loaded from multiple sources in this order (later sources override earlier ones):

1. **Pydantic field defaults** - Hardcoded defaults in [settings.py](edcraft_backend/config/settings.py)
2. **`.env.{APP_ENV}`** (gitignored) - Environment-specific configuration
   - `.env.development` - Development configuration
   - `.env.production` - Production configuration
   - `.env.test` - Test configuration
3. **`.env.local`** (gitignored) - Local overrides (optional)
4. **System environment variables** - Highest priority

### Available Configuration Variables

All configuration variables are documented in [.env.example](.env.example). Key variables include:

#### Application Settings
- `APP_ENV` - Application environment (`development`, `production`, `test`)
- `APP_NAME` - Application name (default: "EdCraft Backend API")
- `APP_VERSION` - Application version (default: "0.1.0")

#### Database Settings
- `DATABASE_URL` - PostgreSQL connection string (required)
  - Format: `postgresql+asyncpg://user:password@host:port/database`
- `DATABASE_ECHO` - Enable SQL query logging (auto-enabled in development)

#### Docker Compose Variables

The docker-compose.yml uses `env_file` directives to load environment-specific configurations:
- Development database (`postgres`) loads from `.env.development`
- Test database (`postgres-test`) loads from `.env.test`

** Database Variables:**
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- Port: Fixed in docker-compose.yml
  - `5432` for development db
  - `5433` for test db


#### CORS Settings
- `CORS_ORIGINS` - JSON array of allowed origins (default: `["http://localhost:5173","http://127.0.0.1:5173"]`)
- `CORS_ALLOW_CREDENTIALS` - Allow credentials in CORS requests (default: `true`)

#### Server Settings
- `SERVER_HOST` - Server host (default: `127.0.0.1`, use `0.0.0.0` for production)
- `SERVER_PORT` - Server port (default: `5000`)
- `LOG_LEVEL` - Logging level (`debug`, `info`, `warning`, `error`, `critical`)


## API Documentation

Once the server is running, visit http://127.0.0.1:8000/docs for interactive API documentation powered by Swagger UI.

### Available Endpoints

The API provides comprehensive CRUD operations for all resources, along with endpoints for question generation.

#### Users (`/users`)

Manage user accounts.

- `POST /users` - Create a new user
  - Body: `{email: string, username: string}`
  - Returns: Created user with ID and timestamps

- `GET /users` - List all users (excluding soft-deleted)
  - Returns: Array of users

- `GET /users/{user_id}` - Get user by ID
  - Returns: User details

- `PATCH /users/{user_id}` - Update user
  - Body: `{email?: string, username?: string}`
  - Returns: Updated user

- `DELETE /users/{user_id}` - Soft delete user
  - Sets `deleted_at` timestamp

- `DELETE /users/{user_id}/hard` - Hard delete user
  - Permanently deletes user and cascades to all owned content

#### Folders (`/folders`)

Hierarchical folder management.

- `POST /folders` - Create a folder
  - Body: `{owner_id: UUID, parent_id?: UUID, name: string, description?: string}`
  - Returns: Created folder

- `GET /folders?owner_id={uuid}&parent_id={uuid}` - List folders
  - Query params: `owner_id` (required), `parent_id` (optional, null for root folders)
  - Returns: Array of folders

- `GET /folders/{folder_id}` - Get folder by ID
  - Returns: Folder details

- `GET /folders/{folder_id}/tree` - Get folder with full subtree
  - Returns: Nested folder structure with all descendants
  - Useful for rendering folder trees in UI

- `GET /folders/{folder_id}/path` - Get folder path from root
  - Returns: Array of folders from root to current folder

- `GET /folders/{folder_id}/contents` - Get folder with contents
  - Returns: Folder details plus complete Assessment and AssessmentTemplate objects
  - Response includes: assessments array and assessment_templates array

- `PATCH /folders/{folder_id}` - Update folder
  - Body: `{name?: string, description?: string}`
  - Returns: Updated folder

- `PATCH /folders/{folder_id}/move` - Move folder to different parent
  - Body: `{parent_id: UUID | null}`
  - Validates against circular references
  - Returns: Updated folder

- `DELETE /folders/{folder_id}` - Soft delete folder
  - Cascades to all children and contained assessments/templates

#### Questions (`/questions`)

Manage individual question instances.

- `GET /questions?owner_id={uuid}&question_type={string}` - List questions
  - Query params: `owner_id` (required), `question_type` (optional)
  - Returns: Array of questions

- `GET /questions/{question_id}` - Get question by ID
  - Returns: Question details with additional_data

- `PATCH /questions/{question_id}` - Update question
  - Body: `{question_type?: string, question_text?: string, additional_data?: object}`
  - Returns: Updated question

- `DELETE /questions/{question_id}` - Soft delete question
  - Removes question from all assessments

- `GET /questions/{question_id}/assessments?owner_id={uuid}` - Get assessments that include this question
  - Query params: `owner_id` (required, must match question owner)
  - Returns: Array of assessments using this question

#### Assessments (`/assessments`)

Manage assessments (collections of questions).

- `POST /assessments` - Create an assessment
  - Body: `{owner_id: UUID, folder_id?: UUID, title: string, description?: string}`
  - Returns: Created assessment

- `GET /assessments?owner_id={uuid}&folder_id={uuid}` - List assessments
  - Query params: `owner_id` (required), `folder_id` (optional)
  - Returns: Array of assessments

- `GET /assessments/{assessment_id}` - Get assessment with questions
  - Returns: Assessment with questions ordered by their position

- `PATCH /assessments/{assessment_id}` - Update assessment metadata
  - Body: `{title?: string, description?: string, folder_id?: UUID}`
  - Returns: Updated assessment

- `DELETE /assessments/{assessment_id}` - Soft delete assessment
  - Questions are preserved and can be reused in other assessments
  - Orphaned questions (not in any assessment) are automatically cleaned up

- `POST /assessments/{assessment_id}/questions` - Create and insert new question
  - Body: `{question: {owner_id: UUID, template_id?: UUID, question_type: string, question_text: string, additional_data: object}, order?: number}`
  - Creates a new question and adds it to the assessment
  - Order is optional; omit to append to the end
  - Valid order range: 0 to current question count (inclusive)
  - Questions at or after specified order are automatically shifted down
  - Returns: Assessment with updated questions

- `POST /assessments/{assessment_id}/questions/link` - Link existing question to assessment
  - Body: `{question_id: UUID, order?: number}`
  - Links an existing question to the assessment
  - Order is optional; omit to append to the end
  - Valid order range: 0 to current question count (inclusive)
  - Questions at or after specified order are automatically shifted down
  - Prevents duplicate questions in the same assessment
  - Returns: Assessment with updated questions

- `DELETE /assessments/{assessment_id}/questions/{question_id}` - Remove question from assessment
  - Removes the association only (question itself is preserved)
  - Automatically normalizes remaining question orders to be consecutive (0, 1, 2...)

- `PATCH /assessments/{assessment_id}/questions/reorder` - Reorder all questions
  - Body: `{question_orders: [{question_id: UUID, order: number}, ...]}`
  - Must include all questions currently in the assessment
  - Orders are validated to be unique
  - Returns: Assessment with reordered questions

#### Question Templates (`/question-templates`)

Manage question template blueprints.

**QuestionTemplateConfig Structure:**
```json
{
  "code": "string",
  "question_spec": "QuestionSpec object",
  "generation_options": "GenerationOptions object",
  "entry_function": "string"
}
```

- `GET /question-templates?owner_id={uuid}` - List templates
  - Query params: `owner_id` (required)
  - Returns: Array of templates

- `GET /question-templates/{template_id}` - Get template by ID
  - Returns: Template details with template_config

- `PATCH /question-templates/{template_id}` - Update template
  - Body: `{question_type?: string, question_text?: string, description?: string, template_config?: QuestionTemplateConfig}`
  - Returns: Updated template

- `DELETE /question-templates/{template_id}` - Soft delete template
  - Questions created from this template are preserved

- `GET /question-templates/{question_template_id}/assessment-templates?owner_id={uuid}` - Get assessment templates that include this question template
  - Query params: `owner_id` (required, must match question template owner)
  - Returns: Array of assessment templates using this question template

#### Assessment Templates (`/assessment-templates`)

Manage assessment template collections.

- `POST /assessment-templates` - Create an assessment template
  - Body: `{owner_id: UUID, folder_id?: UUID, title: string, description?: string}`
  - Returns: Created template

- `GET /assessment-templates?owner_id={uuid}&folder_id={uuid}` - List templates
  - Query params: `owner_id` (required), `folder_id` (optional)
  - Returns: Array of assessment templates

- `GET /assessment-templates/{template_id}` - Get template with question templates
  - Returns: Assessment template with question templates in order

- `PATCH /assessment-templates/{template_id}` - Update template metadata
  - Body: `{title?: string, description?: string, folder_id?: UUID}`
  - Returns: Updated template

- `DELETE /assessment-templates/{template_id}` - Soft delete template
  - Question templates are preserved

- `POST /assessment-templates/{template_id}/question-templates` - Create and insert new question template
  - Body: `{question_template: {owner_id: UUID, question_type: string, question_text: string, additional_data: object}, order?: number}`
  - Creates a new question template and adds it to the assessment template
  - Order is optional; omit to append to the end
  - Valid order range: 0 to current question template count (inclusive)
  - Question templates at or after specified order are automatically shifted down
  - Returns: Assessment template with updated question templates

- `POST /assessment-templates/{template_id}/question-templates/link` - Link existing question template
  - Body: `{question_template_id: UUID, order?: number}`
  - Links an existing question template to the assessment template
  - Order is optional; omit to append to the end
  - Valid order range: 0 to current question template count (inclusive)
  - Question templates at or after specified order are automatically shifted down
  - Prevents duplicate templates in the same assessment template
  - Returns: Assessment template with updated question templates

- `DELETE /assessment-templates/{template_id}/question-templates/{qt_id}` - Remove template
  - Removes the association only

- `PATCH /assessment-templates/{template_id}/question-templates/reorder` - Reorder templates
  - Body: `{question_template_orders: [{question_template_id: UUID, order: number}, ...]}`
  - Must include all question templates currently in the assessment template
  - Orders are validated to be unique
  - Returns: Assessment template with reordered question templates

#### Question Generation (`/question-generation`)

Question generation endpoints.

- `POST /question-generation/analyse-code` - Analyze Python code
  - Body: `{code: string}`
  - Returns: Code information and form schema for question builder

- `POST /question-generation/generate-question` - Generate a question
  - Body: `{code: string, question_spec: object, execution_spec: object, generation_options: object}`
  - Returns: Generated question (not persisted to database)

- `POST /question-generation/generate-template` - Generate a template preview
  - Body: `{code: string, entry_function: string, question_spec: object, generation_options: object}`
  - Creates a question template preview without database persistence
  - Returns: `{question_text: string, question_type: string, template_config: object, preview_question: object}`
  - The `template_config` contains all configuration needed for future template creation
  - The `preview_question` contains placeholder values (e.g., `<option_1>`, `<placeholder_answer>`)

- `POST /question-generation/generate-into-assessment` - Generate and persist to assessment
  - Body: `{assessment_id: UUID, owner_id: UUID, code: string, question_spec: object, execution_spec: object, generation_options: object}`
  - Generates question using engine, creates Question record, links to Assessment
  - Returns: Created question record

- `POST /question-generation/question-templates/{template_id}/generate` - Generate from template
  - Body: `{owner_id: UUID, code: string, assessment_id: UUID}`
  - Uses template configuration to generate question
  - Adds generated question to the specified assessment
  - Returns: Created question record linked to template

- `POST /question-generation/from-template/{template_id}` - Generate question from template
  - Path param: `template_id` (UUID of QuestionTemplate)
  - Body: `{input_data: object}`
  - Returns: Generated question
  - Example request:
    ```json
    {
      "input_data": {"n": 5, "arr": [1, 2, 3, 4, 5]}
    }
    ```

- `POST /question-generation/assessment-from-template/{template_id}` - Generate assessment from template
  - Path param: `template_id` (UUID of AssessmentTemplate)
  - Body: `{assessment_metadata: object, question_inputs: array}`
  - Creates new assessment with all questions generated from templates
  - Returns: Created assessment with all questions
  - Example request:
    ```json
    {
      "assessment_metadata": {
        "owner_id": "uuid",
        "folder_id": "uuid",
        "title": "Custom Assessment Title",
        "description": "Custom description"
      },
      "question_inputs": [
        {"n": 5, "arr": [1, 2, 3, 4, 5]},
        {"n": 10, "arr": [5, 4, 3, 2, 1]}
      ]
    }
    ```
  - Note: `question_inputs` array length must match number of question templates in the assessment template
  - Note: `title` and `description` are optional; defaults to assessment template values if not provided

### Orphaned Resource Cleanup

When assessments, assessment templates, or folders are deleted, a background cleanup process automatically removes orphaned questions and question templates that are no longer associated with any active assessments or templates.

**Key behaviors:**
- **Automatic cleanup**: Triggered when deleting assessments, assessment templates, or folders
- **Background processing**: Runs asynchronously without blocking the deletion response
- **Preservation of shared resources**: Questions/templates used in multiple assessments/templates are only deleted when they become completely orphaned (not used anywhere)
- **User-scoped**: Cleanup only affects resources owned by the same user

This ensures the database remains clean without accumulating unused questions or templates while preserving resources that are still in use.

## Architecture

The codebase follows a clean layered architecture:

1. **Routers Layer** (`routers/`) - HTTP request/response handling
2. **Services Layer** (`services/`) - Business logic and orchestration
3. **Schemas Layer** (`schemas/`) - Data models and validation
4. **Models Layer** (`models/`) - Database models and ORM mappings
5. **Repositories Layer** (`repositories/`) - Data access and database operations
6. **Exceptions** - Custom error handling

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2025 EdCraft Team
