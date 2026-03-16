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
- Async job queue via Nomad — generation endpoints are non-blocking 

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker
- [Nomad](https://developer.hashicorp.com/nomad/install)

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
# 1. Start the database
make db-dev

# 2. Start the Nomad agent
make nomad

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

### WSL2 Setup

When running Docker inside WSL2, the backend container cannot reach Nomad via `localhost` — they are in separate network namespaces. Follow these steps on first-time setup and after each WSL2 restart.

**First-time setup only** — create the Docker network with a subnet that does not overlap with WSL2's network interfaces:

```bash
docker network create --subnet 192.168.100.0/24 edcraft-network
```

Also tag the worker image with a non-`:latest` tag. Nomad always tries to pull `:latest` from the registry even with `force_pull: false`, so a stable local tag is required:

```bash
docker tag edcraft-backend:latest edcraft-backend:local
```

Then set in `.env.development`:
```
NOMAD_CONTAINER_IMAGE=edcraft-backend:local
```

Re-run `docker tag` whenever you rebuild the image.

**Every session** — start things in this order:

1. Start Nomad in a dedicated terminal (runs in the foreground):
   ```bash
   make nomad
   ```

2. Update `NOMAD_HOST` in `.env.development` with the current WSL2 IP:
   ```bash
   sed -i "s/NOMAD_HOST=.*/NOMAD_HOST=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)/" .env.development
   ```
   This is needed because WSL2 assigns a new IP to `eth0` on each restart.

3. Start Docker services in a separate terminal:
   ```bash
   make docker-up
   ```

### Building the Image

```bash
# Build the Docker image
docker compose build backend

### Viewing Logs

```bash
# View logs
docker logs edcraft-backend

# Follow logs in real-time
docker logs -f edcraft-backend

# Or using docker-compose
docker compose logs -f backend
```

## Project Structure

The application follows a layered architecture pattern:

- **`edcraft_backend/`** - Main application package
  - **`config/`** - Environment-based configuration management using Pydantic settings
  - **`models/`** - SQLAlchemy ORM models for database entities (users, assessments, questions, templates, etc.)
  - **`routers/`** - FastAPI route handlers organized by resource (auth, users, assessments, questions, etc.)
  - **`schemas/`** - Pydantic models for request/response validation and serialization
  - **`services/`** - Business logic layer separating concerns from route handlers
  - **`repositories/`** - Database access layer
  - **`executors/`** - Integrations with external systems (Nomad job submission via HTTP API)
  - **`security/`** - JWT authentication and password hashing utilities
  - **`oauth/`** - OAuth 2.0 provider integrations
  - Core files: `main.py` (app initialization), `database.py` (session management), `dependencies.py` (shared dependencies)

- **`worker/`** - Standalone worker entrypoint run inside Nomad-spawned containers; handles all job types and POSTs results back to FastAPI via callback URL
- **`alembic/`** - Database migration scripts managed by Alembic
- **`tests/`** - Test suite
- **Configuration files**: `docker-compose.yml`, `Makefile`, `pyproject.toml`

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
    users ||--o{ question_template_banks : "owns"

    folders ||--o{ folders : "contains (parent-child)"
    folders ||--o{ assessments : "contains"
    folders ||--o{ assessment_templates : "contains"
    folders ||--o{ question_banks : "contains"
    folders ||--o{ question_template_banks : "contains"

    assessments ||--o{ questions : "contains (FK)"
    question_banks ||--o{ questions : "contains (FK)"
    questions ||--o{ questions : "linked_from (self-ref)"

    assessment_templates ||--o{ question_templates : "contains (FK)"
    question_template_banks ||--o{ question_templates : "contains (FK)"
    question_templates ||--o{ question_templates : "linked_from (self-ref)"

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

    question_banks {
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
        uuid assessment_id FK "nullable, SET NULL"
        uuid question_bank_id FK "nullable, SET NULL"
        uuid linked_from_question_id FK "nullable, SET NULL (self-ref)"
        int order "nullable, unique per assessment"
        string question_type
        text question_text
        json additional_data
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }

    question_template_banks {
        uuid id PK
        uuid owner_id FK
        uuid folder_id FK "nullable"
        string title
        text description "nullable"
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
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
        uuid assessment_template_id FK "nullable, SET NULL"
        uuid question_template_bank_id FK "nullable, SET NULL"
        uuid linked_from_template_id FK "nullable, SET NULL (self-ref)"
        int order "nullable, unique per assessment_template"
        string question_type
        string question_text_template
        string text_template_type
        json template_config
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
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
  - Contains sub-folders, assessments, question banks, and assessment templates
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

- **Assessment** ([assessment.py](edcraft_backend/models/assessment.py)) - Ordered collection of questions
  - One-to-many relationship with questions via `assessment_id` FK on `questions`

- **QuestionBank** ([question_bank.py](edcraft_backend/models/question_bank.py)) - Reusable storage for questions
  - One-to-many relationship with questions via `question_bank_id` FK on `questions`

- **Question** ([question.py](edcraft_backend/models/question.py)) - Individual question instances
  - Can be created from a QuestionTemplate (`template_id`)
  - Belongs to exactly one container at a time: either an assessment (`assessment_id`) or a question bank (`question_bank_id`), enforced by a CHECK constraint
  - `linked_from_question_id`: self-referential FK pointing to the source question when a copy was created via the link endpoint (SET NULL on source delete)
  - **Copy-on-Link semantics:** Linking a question into an assessment or question bank creates an independent copy rather than sharing the same record. Each copy can be edited independently. The source link can be used to sync content from the source on demand.
  - **Question Ordering Behavior** (assessments only):
    - Orders are 0-indexed and always consecutive (0, 1, 2, 3...)
    - Insert behavior: Adding a question at a specific order shifts subsequent questions down
    - Valid order range: 0 to current question count (inclusive); omit to append
    - Automatic normalization after deletions to maintain consecutive ordering

- **AssessmentTemplate** ([assessment_template.py](edcraft_backend/models/assessment_template.py)) - Ordered collection of question templates
  - One-to-many relationship with question templates via `assessment_template_id` FK on `question_templates`

- **QuestionTemplateBank** ([question_template_bank.py](edcraft_backend/models/question_template_bank.py)) - Reusable storage for question templates
  - One-to-many relationship with question templates via `question_template_bank_id` FK on `question_templates`

- **QuestionTemplate** ([question_template.py](edcraft_backend/models/question_template.py)) - Blueprint for creating questions
  - Hybrid structure: fixed columns + JSON for flexibility
  - Used to generate Question instances
  - Belongs to exactly one container at a time: either an assessment template (`assessment_template_id`) or a question template bank (`question_template_bank_id`), enforced by a CHECK constraint
  - `linked_from_template_id`: self-referential FK pointing to the source template when a copy was created via the link endpoint (SET NULL on source delete)
  - **Copy-on-Link semantics:** Linking a question template into an assessment template or bank creates an independent copy rather than sharing the same record. Each copy can be edited independently. The source link can be used to sync content from the source on demand.
  - **Question Template Ordering Behavior** (assessment templates only):
    - Orders are 0-indexed and always consecutive (0, 1, 2, 3...)
    - Insert behavior: Adding a template at a specific order shifts subsequent templates down
    - Valid order range: 0 to current template count (inclusive); omit to append
    - Automatic normalization after deletions

- **Job** ([job.py](edcraft_backend/models/job.py)) - Tracks async jobs submitted to Nomad
  - Statuses: `queued` → `running` → `completed` / `failed`
  - Stores `result_json` (serialized result) and `error_message` on completion
  - Optionally linked to the submitting user (`user_id`, nullable)

- **JobToken** ([job.py](edcraft_backend/models/job.py)) - Single-use callback tokens for worker → API result delivery
  - Token is passed to the worker at submission time; worker includes it in the `POST /jobs/callback/{token}` request
  - Consumed (marked used) on first call; revoked tokens are rejected

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

## Async Job Queue (Nomad)

Long-running AI generation endpoints are non-blocking. Instead of waiting for the result, they immediately return `202 Accepted` with a `job_id` that clients use to poll for completion.

### How It Works

1. **Client submits request** → FastAPI creates a `Job` row in the database (status: `queued`), generates a one-time `JobToken`, builds a callback URL, and dispatches a batch job to Nomad.
2. **FastAPI responds** with `202 Accepted`:
   ```json
   { "job_id": "<uuid>", "status_url": "/jobs/<uuid>" }
   ```
3. **Nomad schedules a worker container** using the same `edcraft-backend` Docker image. Job parameters are passed as a base64-encoded env var.
4. **Worker executes** (`python -m worker.entrypoint`), completes the task, and POSTs the result back:
   ```
   POST /jobs/callback/{token}
   { "result": "<json string>" }
   ```
5. **Client polls** `GET /jobs/{job_id}` until `status` is `completed` or `failed`:
   ```json
   { "job_id": "<uuid>", "status": "completed", "result": { ... }, "error": null }
   ```

### Async Endpoints

| Method | Endpoint | Job type |
|--------|----------|----------|
| `POST` | `/question-generation/analyse-code` | `analyse_code` |
| `POST` | `/question-generation/generate-question` | `generate_question` |
| `POST` | `/question-generation/generate-template` | `generate_template` |
| `POST` | `/question-generation/from-template/{template_id}` | `question_from_template` |
| `POST` | `/question-generation/assessment-from-template/{template_id}` | `assessment_from_template` |
| `POST` | `/input-generator/generate` | `generate_inputs` |


### Nomad Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NOMAD_HOST` | `127.0.0.1` | Nomad agent host |
| `NOMAD_PORT` | `4646` | Nomad HTTP API port |
| `NOMAD_TOKEN` | _(none)_ | ACL token — not required in `-dev` mode |
| `NOMAD_NAMESPACE` | _(none)_ | Namespace for job isolation |
| `NOMAD_DATACENTERS` | `["dc1"]` | Datacenters where workers are scheduled |
| `NOMAD_CPU_MHZ` | `500` | CPU reservation per worker task (MHz) |
| `NOMAD_MEMORY_MB` | `512` | Memory reservation per worker task (MB) |
| `NOMAD_CALLBACK_BASE_URL` | `http://host.docker.internal:8000` | Base URL the worker uses to POST results back |
| `NOMAD_CONTAINER_IMAGE` | `edcraft-backend:latest` | Docker image to run as the worker |

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

#### Nomad Settings
See the full variable reference in the [Async Job Queue](#async-job-queue-nomad) section.
- `NOMAD_HOST` - Nomad agent host (default: `127.0.0.1`)
- `NOMAD_PORT` - Nomad HTTP API port (default: `4646`)
- `NOMAD_CALLBACK_BASE_URL` - URL workers use to POST results back (must be reachable from inside a Docker container)
- `NOMAD_CONTAINER_IMAGE` - Worker Docker image (default: `edcraft-backend:latest`)

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

**Assessments** (`/assessments`, all require auth)
- Questions support ordered insertion: omit `order` to append, or specify to insert at position (others shift down)
- Reorder endpoint requires all questions to be included with unique orders

**Question Banks** (`/question-banks`, all require auth)
- Reusable collections of questions without ordering

**Assessment Templates** (`/assessment-templates`, all require auth)
- Question templates support ordered insertion: omit `order` to append, or specify to insert at position (others shift down)
- Reorder endpoints require all items to be included with unique orders

**Question Template Banks** (`/question-template-banks`, all require auth)
- Reusable collections of question templates without ordering

**Question Templates**
- `template_config` structure: `{code, question_spec, generation_options, entry_function}`

**Question Generation**
- All endpoints are **async** — they return `202 Accepted` with `{"job_id": "...", "status_url": "/jobs/..."}`. Poll `GET /jobs/{job_id}` for the result.
- `generate-template` result includes a preview with placeholder values (e.g. `<option_1>`) and `template_config` for future template creation
- `assessment-from-template`: `question_inputs` array length must match the number of question templates in the assessment template; `title`/`description` default to template values if omitted

**Input Generator**
- All endpoints are **async** — same `202 Accepted` + poll pattern as Question Generation
- Generates values for one or more variables from their config

**Jobs** (`/jobs`, requires auth)
- `GET /jobs/{job_id}` — poll for job status; returns `status`, `result` (parsed), and `error`
- Possible statuses: `queued`, `running`, `completed`, `failed`

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2025 EdCraft Team
