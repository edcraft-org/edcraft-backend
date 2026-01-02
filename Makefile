.PHONY: install test lint type-check all-checks clean dev db-dev db-test db-all db-down db-status test-with-db

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

type-check:
	uv run mypy .

all-checks: lint type-check test

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name __pycache__ -delete

clean-tool:
	@if [ -d ".mypy_cache" ]; then rm -rf .mypy_cache; fi
	@if [ -d ".pytest_cache" ]; then rm -rf .pytest_cache; fi
	@if [ -d ".ruff_cache" ]; then rm -rf .ruff_cache; fi

update:
	uv lock --upgrade
	uv sync

dev:
	uv run uvicorn edcraft_backend.main:app --host 127.0.0.1 --port 8000 --reload

# Database management targets
db-dev:
	@echo "Starting development database..."
	docker compose up -d postgres

db-test:
	@echo "Starting test database..."
	docker compose --profile test up -d postgres-test

db-all:
	@echo "Starting both development and test databases..."
	docker compose --profile all up -d

db-down:
	@echo "Stopping all databases..."
	docker compose --profile all down

db-status:
	@echo "Database container status:"
	@docker compose --profile all ps

test-with-db:
	@echo "Starting test database..."
	docker compose --profile test up -d postgres-test
	@echo "Waiting for test database to be ready..."
	@sleep 3
	@echo "Running tests..."
	uv run pytest
	@echo ""
	@echo "Stopping test database..."
	docker compose --profile test down
