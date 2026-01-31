.PHONY: install dev test lint format docker-up docker-down migrate migrate-down migrate-new run-ingestion run-api run-server run-web clean help

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies using uv
	@echo "Installing dependencies with uv..."
	uv sync --all-packages
	@echo "✓ Installation complete"

dev: ## Install dev dependencies and set up pre-commit hooks
	@echo "Installing dev dependencies..."
	uv sync --all-packages
	uv run pre-commit install
	@echo "✓ Dev environment ready"

test: ## Run all tests
	@echo "Running core tests..."
	@uv run pytest packages/core/tests -v --tb=short
	@echo ""
	@echo "Running ingestion tests..."
	@cd packages/ingestion && uv run pytest tests/test_normalizers.py tests/test_otlp.py -v --tb=short
	@echo ""
	@echo "Running analysis tests..."
	@cd packages/analysis && uv run pytest tests/ -v --tb=short
	@echo "✓ All tests passed"

test-unit: ## Run unit tests only (no database required)
	@echo "Running unit tests..."
	@uv run pytest packages/core/tests -v --tb=short
	@cd packages/ingestion && uv run pytest tests/test_normalizers.py tests/test_otlp.py -v --tb=short
	@cd packages/analysis && uv run pytest tests/ -v --tb=short
	@echo "✓ Unit tests passed"

test-integration: ## Run integration tests (requires database)
	@echo "Running integration tests..."
	@echo "⚠ Note: Requires Docker database (make docker-up)"
	@cd packages/ingestion && uv run pytest tests/test_integration.py -v --tb=short
	@echo "✓ Integration tests passed"

lint: ## Run linting checks with ruff
	@echo "Running linters..."
	uv run ruff check packages/
	@echo "✓ Linting complete"

format: ## Format code with ruff
	@echo "Formatting code..."
	uv run ruff format packages/
	uv run ruff check --fix packages/
	@echo "✓ Code formatted"

docker-up: ## Start Docker services (PostgreSQL + TimescaleDB)
	@echo "Starting Docker services..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✓ Docker services started"
	@echo "PostgreSQL available at: localhost:5432"
	@echo "  Database: agenttrace"
	@echo "  User: agenttrace"
	@echo "  Password: dev_password"

docker-down: ## Stop Docker services
	@echo "Stopping Docker services..."
	docker-compose -f docker-compose.dev.yml down
	@echo "✓ Docker services stopped"

docker-logs: ## View Docker service logs
	docker-compose -f docker-compose.dev.yml logs -f

migrate: ## Run database migrations
	@echo "Running migrations..."
	uv run alembic upgrade head
	@echo "✓ Migrations complete"

migrate-down: ## Rollback last migration
	@echo "Rolling back last migration..."
	uv run alembic downgrade -1
	@echo "✓ Rollback complete"

migrate-new: ## Create new migration (use: make migrate-new name="migration name")
	@if [ -z "$(name)" ]; then \
		echo "Error: Please specify migration name: make migrate-new name=\"your migration name\""; \
		exit 1; \
	fi
	uv run alembic revision -m "$(name)"

run-ingestion: ## Start ingestion service (FastAPI)
	@echo "Starting ingestion service on http://localhost:4318"
	uv run uvicorn agenttrace_ingestion.server:app --reload --port 4318

run-api: ## Start analysis API server
	@echo "Starting analysis API on http://localhost:8000"
	@echo "⚠ Note: Ingestion endpoint will be available at http://localhost:8000/v1/traces"
	@echo "⚠ Note: Analysis endpoints available at http://localhost:8000/api/*"
	uv run uvicorn agenttrace_ingestion.server:app --reload --port 8000

run-server: ## Start combined ingestion + analysis server (alias for run-api)
	@$(MAKE) run-api

run-web: ## Start web UI development server
	@echo "Starting web UI on http://localhost:5173"
	@echo "⚠ Note: API must be running on http://localhost:8000 (make run-api)"
	cd web && npm install && npm run dev

clean: ## Clean build artifacts and caches
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned"

verify: ## Verify installation and run basic checks
	@echo "Verifying installation..."
	@uv run python -c "from agenttrace_core.models import Trace, Span, Agent; print('✓ Core models importable')"
	@uv run python -c "from agenttrace_ingestion.server import app; print('✓ Ingestion server importable')"
	@uv run python -c "from agenttrace_analysis import AgentGraph, RuleBasedClassifier; print('✓ Analysis module importable')"
	@echo "✓ Verification complete"
