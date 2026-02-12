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
- JWT-based authentication and OAuth2 support (GitHub)

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

## Docker Deployment

For easy deployment, you can run the entire backend (including database) in Docker containers.

### Quick Start

```bash
# Build and start all services (database + backend)
make docker-up

# Stop all services
make docker-down
```

The backend will be available at http://localhost:8000 with automatic database migrations on startup.

## Project Structure

```
edcraft-backend/
├── edcraft_backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app initialization
│   ├── database.py              # Database session management
│   ├── dependencies.py          # Shared FastAPI dependencies (auth, db)
│   ├── exceptions.py            # Custom exception classes
│   ├── forms_config.json        # Form configuration (JSON)
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── environments.py      # Environment enum
│   │   └── settings.py          # Pydantic settings
│   ├── models/                  # SQLAlchemy database models
│   │   ├── user.py
│   │   ├── refresh_token.py
│   │   ├── oauth_account.py
│   │   ├── folder.py
│   │   ├── assessment.py
│   │   ├── assessment_question.py
│   │   ├── question.py
│   │   ├── assessment_template.py
│   │   ├── assessment_template_question_template.py
│   │   └── question_template.py
│   ├── routers/                 # API route handlers
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── folders.py
│   │   ├── assessments.py
│   │   ├── questions.py
│   │   ├── assessment_templates.py
│   │   ├── question_templates.py
│   │   └── question_generation.py
│   ├── schemas/                 # Pydantic models for validation
│   │   ├── user.py
│   │   ├── auth.py
│   │   ├── folder.py
│   │   ├── assessment.py
│   │   ├── question.py
│   │   ├── assessment_template.py
│   │   ├── question_template.py
│   │   ├── code_info.py
│   │   ├── form_builder.py
│   │   └── question_generation.py
│   ├── services/                # Business logic
│   │   ├── auth_service.py
│   │   ├── oauth_service.py
│   │   ├── user_service.py
│   │   ├── folder_service.py
│   │   ├── assessment_service.py
│   │   ├── question_service.py
│   │   ├── assessment_template_service.py
│   │   ├── question_template_service.py
│   │   ├── code_analysis_service.py
│   │   ├── form_builder_service.py
│   │   └── question_generation_service.py
│   ├── security/                # JWT and password utilities
│   └── oauth/                   # OAuth provider configuration
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
    users ||--o{ refresh_tokens : "has"
    users ||--o{ oauth_accounts : "has"
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
        string name
        string password_hash "nullable (OAuth users)"
        bool is_active
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    refresh_tokens {
        uuid id PK
        uuid user_id FK
        string token_hash UK
        datetime expires_at
        bool is_revoked
        string ip_address "nullable"
        string user_agent "nullable"
        datetime created_at
    }

    oauth_accounts {
        uuid id PK
        uuid user_id FK
        string provider
        string provider_user_id
        datetime created_at
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
  - Fields: email, name, password_hash (nullable for OAuth users), is_active
  - Owns all content (folders, assessments, questions, templates)

- **RefreshToken** ([refresh_token.py](edcraft_backend/models/refresh_token.py)) - Persisted refresh tokens for rotation and revocation
  - Stores a hash of the token (not the token itself)
  - Tracks IP address and user agent for security auditing

- **OAuthAccount** ([oauth_account.py](edcraft_backend/models/oauth_account.py)) - Links OAuth provider identities to users
  - Unique constraint on `(provider, provider_user_id)`
  - Allows one user to link multiple OAuth providers

- **Folder** ([folder.py](edcraft_backend/models/folder.py)) - Hierarchical folder organization using tree structure
  - Self-referential parent-child relationship
  - Contains sub-folders, assessments and assessment templates
  - Unique constraint: folder names must be unique per parent and user
  - Unique constraint: users can only have one root folder (parent_id=NULL)
  - CASCADE delete:
    - deleting a folder removes all contents, but shared questions/templates are preserved if referenced elsewhere

- **Root Folder Behavior**:
  - Every user automatically gets a "My Projects" folder created when their account is created
  - The root folder has `parent_id=None` and serves as the top-level container for all user content
  - Root folders cannot be deleted (attempting to delete returns 403 Forbidden)
  - Root folders can be renamed by the user
  - The root folder is accessible via `GET /users/me/root-folder`

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

## Authentication

The application uses JWT-based authentication with httpOnly cookies and supports both email/password and OAuth (GitHub) login.

### How It Works

**Email/Password Flow:**
1. Sign up via `POST /auth/signup` with email and password (min 12 characters)
2. Log in via `POST /auth/login` to receive access and refresh tokens set as httpOnly cookies
3. Call `POST /auth/refresh` to rotate tokens before the access token expires
4. Call `POST /auth/logout` to revoke the refresh token

**OAuth (GitHub) Flow:**
1. Redirect the user to `GET /auth/oauth/github/authorize`
2. User authorizes on GitHub; GitHub redirects back to `/auth/oauth/github/callback`
3. Backend exchanges the code for an access token, fetches the user's profile and verified email
4. Links the OAuth account to an existing user (by email) or creates a new user
5. Issues access and refresh tokens as httpOnly cookies

### Token Details

| Token | Lifetime | Storage | Purpose |
|-------|----------|---------|---------|
| Access Token | 30 min (default) | httpOnly cookie | Authenticate API requests |
| Refresh Token | 14 days (default) | httpOnly cookie | Obtain new access tokens |

Refresh tokens are stored as hashes in the database, enabling revocation. Token rotation invalidates the previous refresh token on each use.

### Protecting Routes

Protected routes use the `CurrentUserDep` dependency, which reads the `access_token` cookie, validates the JWT, and resolves the user:

```python
from edcraft_backend.dependencies import CurrentUserDep

@router.get("/items")
async def get_items(current_user: CurrentUserDep):
    # current_user is the authenticated User model instance
    ...
```

### Setting Up OAuth (GitHub)

1. Create a GitHub OAuth App at https://github.com/settings/developers
2. Set the callback URL to `http://localhost:8000/auth/oauth/github/callback` (development)
3. Add the client ID and secret to your `.env.development`:
   ```
   OAUTH_GITHUB_CLIENT_ID=<your-client-id>
   OAUTH_GITHUB_CLIENT_SECRET=<your-client-secret>
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

#### JWT Settings
- `JWT_SECRET` - Secret key for signing tokens (generate with `openssl rand -hex 32`)
- `JWT_ALGORITHM` - Signing algorithm (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token lifetime (default: `30`)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token lifetime (default: `14`)
- `JWT_ISSUER` - JWT issuer claim (default: `edcraft`)
- `JWT_AUDIENCE` - JWT audience claim (default: `edcraft`)

#### Session Settings
- `SESSION_SECRET` - Secret key for signing session cookies (generate with `openssl rand -hex 32`)
  - Required for OAuth flows (Authlib stores state in sessions)

#### OAuth Settings
- `OAUTH_GITHUB_CLIENT_ID` - GitHub OAuth app client ID
- `OAUTH_GITHUB_CLIENT_SECRET` - GitHub OAuth app client secret
- `OAUTH_GITHUB_REDIRECT_URI` - GitHub OAuth callback URL

#### Authentication Settings
- `PASSWORD_MIN_LENGTH` - Minimum password length (default: `12`)
- `FRONTEND_URL` - Frontend URL for OAuth redirects (default: `http://localhost:5173`)

#### CORS Settings
- `CORS_ORIGINS` - JSON array of allowed origins (default: `["http://localhost:5173","http://127.0.0.1:5173"]`)
- `CORS_ALLOW_CREDENTIALS` - Allow credentials in CORS requests (default: `true`)

#### Server Settings
- `SERVER_HOST` - Server host (default: `127.0.0.1`, use `0.0.0.0` for production)
- `SERVER_PORT` - Server port (default: `8000`)
- `LOG_LEVEL` - Logging level (`debug`, `info`, `warning`, `error`, `critical`)


## API Documentation

Once the server is running, visit http://127.0.0.1:8000/docs for interactive API documentation powered by Swagger UI.

### Available Endpoints

Full endpoint reference is auto-generated at http://127.0.0.1:8000/docs. Key non-obvious behaviors:

**Users** (`/users`, all require auth)
- A root folder is automatically created for each user on registration (`GET /users/me/root-folder` to retrieve it)
- Soft delete (`DELETE /users/me`) soft deletes all owned content

**Folders** (`/folders`, all require auth)
- `GET /folders` without `parent_id` returns all folders owned by the user; with `parent_id` returns only direct children
- Root folders (`parent_id=null`) cannot be deleted — returns 403
- Move (`PATCH /folders/{folder_id}/move`) validates against circular references

**Assessments & Assessment Templates** (all require auth)
- Questions/question templates support ordered insertion: omit `order` to append, or specify to insert at position (others shift down)
- Reorder endpoints require all items to be included with unique orders
- Deleting an assessment preserves its questions; orphaned questions (no longer in any assessment) are cleaned up automatically

**Question Templates**
- `template_config` structure: `{code, question_spec, generation_options, entry_function}`

**Question Generation**
- `generate-template` returns a preview with placeholder values (e.g. `<option_1>`) and `template_config` for future template creation
- `assessment-from-template`: `question_inputs` array length must match the number of question templates in the assessment template; `title`/`description` default to template values if omitted

## Architecture

The codebase follows a clean layered architecture:

1. **Routers Layer** (`routers/`) - HTTP request/response handling
2. **Services Layer** (`services/`) - Business logic and orchestration
3. **Schemas Layer** (`schemas/`) - Data models and validation
4. **Models Layer** (`models/`) - Database models and ORM mappings
5. **Repositories Layer** (`repositories/`) - Data access and database operations
6. **Security** (`security/`) - JWT creation/validation and password hashing
7. **OAuth** (`oauth/`) - OAuth provider configuration and user info fetching
8. **Exceptions** - Custom error handling

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2025 EdCraft Team
