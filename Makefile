.PHONY: install dev test lint format docker-up docker-down clean help

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
	@echo "Running tests..."
	uv run pytest packages/core/tests -v
	@echo "✓ All tests passed"

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
	@echo "✓ Verification complete"
