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

## Development

### Running the Server

Start the development server with auto-reload:

```bash
make dev
# or
uv run uvicorn edcraft_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- Main API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Alternative docs: http://127.0.0.1:8000/redoc

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
