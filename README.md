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
uv run uvicorn edcraft_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- Main API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Alternative docs: http://127.0.0.1:8000/redoc

### Running Tests

```bash
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=edcraft_backend --cov-report=html
```

### Code Quality

Type checking with mypy:

```bash
uv run mypy edcraft_backend
```

Linting and formatting with ruff:

```bash
# Check code
uv run ruff check .

# Format code
uv run ruff format .
```

## Project Structure

```
edcraft-backend/
├── edcraft_backend/
│   ├── __init__.py
│   ├── main.py           # FastAPI app initialization
│   ├── routers/          # API route handlers
│   ├── schemas/          # Pydantic models
│   └── services/         # Business logic
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
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

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2025 EdCraft Team
