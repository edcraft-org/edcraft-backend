.PHONY: setup update run test lint typecheck check clean clean-all db-up db-test docker-down nomad

# --- Core setup ---
setup:
	uv sync

update:
	uv lock --upgrade && uv sync

# --- Run app ---
run:
	uv run uvicorn edcraft_backend.main:app --reload

# --- Quality checks ---
test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

check: lint typecheck test

# --- Cleaning ---
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

clean-all: clean
	rm -rf .mypy_cache .pytest_cache .ruff_cache

# --- Database ---
db-up:
	docker compose up -d postgres

db-test:
	docker compose --profile test up -d postgres-test

docker-down:
	docker compose down

# --- Nomad ---
nomad:
	nomad agent -dev -bind=0.0.0.0 -log-level=INFO