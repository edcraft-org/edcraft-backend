.PHONY: install test lint type-check all-checks clean dev

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
