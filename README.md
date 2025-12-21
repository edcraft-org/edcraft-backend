# EdCraft Backend

FastAPI wrapper for the EdCraft Engine, providing a REST API for question generation and management.

## Overview

EdCraft Backend is a FastAPI-based web service that exposes the EdCraft Engine functionality through HTTP endpoints. It serves as the backend API for EdCraft applications.

## Features

- FastAPI framework with automatic OpenAPI documentation
- CORS middleware configured for local development
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
```bash
cp .env.example .env
```

Edit `.env` and configure your database credentials if needed.

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

```bash
make test
# or
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=edcraft_backend --cov-report=html
```

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
│   ├── exceptions.py            # Custom exception classes
│   ├── forms_config.json        # Form configuration (JSON)
│   ├── routers/                 # API route handlers
│   │   └── question_generation.py
│   ├── schemas/                 # Pydantic models
│   │   ├── code_info.py
│   │   ├── form_builder.py
│   │   └── question_generation.py
│   └── services/                # Business logic
│       ├── code_analysis.py
│       ├── form_builder.py
│       └── question_generation.py
├── tests/                       # Test suite
│   └── __init__.py
├── Makefile                     # Development commands
├── pyproject.toml               # Project configuration
└── README.md
```

## Database

### Database Setup

The application uses PostgreSQL with async SQLAlchemy for data persistence. The database configuration is managed through environment variables.

#### Starting the Database

Using Docker Compose:

```bash
# Start PostgreSQL in the background
docker-compose up -d

# Check database status
docker-compose ps

# View database logs
docker-compose logs -f postgres

# Stop the database
docker-compose down

# Stop and remove all data (destructive!)
docker-compose down -v
```

#### Accessing the Database

Connect to the PostgreSQL database directly using psql:

```bash
# Connect to the database
docker exec -it edcraft-postgres psql -U edcraft_dev -d edcraft

# Common psql commands once connected:
# \dt              - List all tables
# \d table_name    - Describe table structure
# SELECT * FROM table_name;  - View table contents
# \q               - Quit psql
```

#### Database Migrations

The project uses Alembic for database migrations:

```bash
# Run all pending migrations
uv run alembic upgrade head

# Create a new migration (after modifying models)
uv run alembic revision --autogenerate -m "description of changes"

# Rollback the last migration
uv run alembic downgrade -1

# View migration history
uv run alembic history

# View current migration version
uv run alembic current
```

#### Database Models

Database models will be located in `edcraft_backend/models/`. When creating new models:

1. Create your SQLAlchemy model inheriting from `Base`
2. Import the model in `edcraft_backend/models/__init__.py`
3. Import models in `alembic/env.py` for autogenerate to detect them
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

#### Environment Variables

Database configuration is managed through these environment variables (see `.env.example`):

- `DATABASE_URL` - Full PostgreSQL connection string
- `ENVIRONMENT` - Set to "production" to disable SQL query logging
- `POSTGRES_DB` - Database name (for Docker Compose)
- `POSTGRES_USER` - Database user (for Docker Compose)
- `POSTGRES_PASSWORD` - Database password (for Docker Compose)
- `POSTGRES_PORT` - Database port (for Docker Compose)

## Configuration

### CORS

The application is configured to accept requests from:
- http://localhost:5173
- http://127.0.0.1:5173

Modify the `allow_origins` list in [main.py](edcraft_backend/main.py) to add additional origins.

## API Documentation

Once the server is running, visit http://127.0.0.1:8000/docs for interactive API documentation powered by Swagger UI.

### Available Endpoints

- `GET /` - Health check endpoint
- `POST /question-generation/analyse-code` - Analyze Python code and return code infomation and form schema
- `POST /question-generation/generate-question` - Generate questions based on code analysis and question builder form response

## Architecture

The codebase follows a clean layered architecture:

1. **Routers Layer** (`routers/`) - HTTP request/response handling
2. **Services Layer** (`services/`) - Business logic and orchestration
3. **Schemas Layer** (`schemas/`) - Data models and validation
4. **Exceptions** - Custom error handling

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2025 EdCraft Team
