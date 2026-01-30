# AgentTrace Testing Guide

This document describes how to run tests for AgentTrace.

## Test Structure

```
packages/
├── core/tests/                      # Core model tests
│   ├── test_exceptions.py          # Exception tests (3 tests)
│   └── test_models.py               # Model tests (6 tests)
└── ingestion/tests/                 # Ingestion pipeline tests
    ├── test_normalizers.py          # Normalizer tests (15 tests)
    ├── test_otlp.py                 # OTLP helper tests (17 tests)
    └── test_integration.py          # Integration tests (require DB)
```

**Total:** 41 unit tests, 7 integration tests

## Prerequisites

- Python 3.11+
- `uv` package manager
- Docker (for integration tests only)

## Running Tests

### All Unit Tests (No Database Required)

```bash
make test
```

This runs:
- 9 core model tests
- 32 ingestion unit tests

**Expected output:** `41 passed`

### Core Tests Only

```bash
uv run pytest packages/core/tests -v
```

### Ingestion Tests Only

```bash
cd packages/ingestion
uv run pytest tests/test_normalizers.py tests/test_otlp.py -v
```

### Integration Tests (Requires Database)

Integration tests require a running PostgreSQL database with TimescaleDB:

```bash
# 1. Start database
make docker-up

# 2. Wait for DB to be ready (check health)
docker ps

# 3. Run migrations
make migrate

# 4. Run integration tests
make test-integration
```

Integration tests verify:
- Health and readiness endpoints
- OTLP trace ingestion (JSON format)
- Database writes (spans, agents, messages)
- Error handling

## Test Coverage

### Normalizers (`test_normalizers.py`)

Tests all 4 framework normalizers:

- **LangGraphNormalizer** (3 tests)
  - Basic span normalization with `langgraph.node` extraction
  - LLM call detection and cost estimation
  - Handoff/edge message extraction

- **AutoGenNormalizer** (2 tests)
  - Agent name and role extraction
  - Inter-agent message extraction

- **CrewAINormalizer** (1 test)
  - Crew/agent/task hierarchy extraction

- **GenericNormalizer** (4 tests)
  - Fallback normalization with standard OTEL attributes
  - Resource attribute fallback
  - LLM call kind inference
  - Tool call kind inference

- **Normalizer Factory** (5 tests)
  - Framework-specific normalizer selection
  - Case-insensitive matching
  - Fallback to generic normalizer

### OTLP Helpers (`test_otlp.py`)

Tests OTLP protocol parsing:

- **Resource Attributes** (6 tests)
  - String, int, bool, double attribute extraction
  - Multiple attributes
  - Empty/null handling

- **Framework Detection** (7 tests)
  - Explicit framework attribute
  - Service name inference (LangGraph, AutoGen, CrewAI)
  - Default to generic
  - Case-insensitive detection

- **Request Parsing** (4 tests)
  - JSON format parsing
  - Content type validation
  - Error handling
  - Case-insensitive content-type matching

### Integration Tests (`test_integration.py`)

End-to-end ingestion tests:

- **Health Endpoints** (2 tests)
  - `/health` check
  - `/ready` check with DB connection

- **OTLP Ingestion** (3 tests)
  - Single span ingestion
  - Multiple spans batching
  - Agent message extraction

- **Error Handling** (3 tests)
  - Empty request body
  - Invalid JSON
  - Unsupported content type

## Test Markers

Integration tests are marked with `pytest.mark.asyncio` and require a database.

To skip integration tests:

```bash
uv run pytest packages/ -m "not integration"
```

## Continuous Integration

GitHub Actions CI runs:

```yaml
jobs:
  test:
    - Install dependencies
    - Run linters (ruff)
    - Run unit tests (no DB required)
    - Verify imports

  # Integration tests run only when PR is ready for merge
```

## Writing New Tests

### Unit Tests

For normalizers or OTLP helpers:

```python
from agenttrace_ingestion.normalizers import LangGraphNormalizer

def test_my_feature():
    normalizer = LangGraphNormalizer()
    # Create mock span
    result = normalizer.normalize(mock_span, {})
    assert result.agent.name == "ExpectedName"
```

### Integration Tests

For end-to-end ingestion:

```python
@pytest.mark.asyncio
async def test_my_integration(app_client, clean_database):
    response = await app_client.post("/v1/traces", json=otlp_data)
    assert response.status_code == 200
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError` when running tests:

```bash
# Solution: Run tests from package directory
cd packages/ingestion
uv run pytest tests/ -v
```

### Database Connection Errors

If integration tests fail with connection errors:

```bash
# Check if database is running
docker ps

# Check logs
make docker-logs

# Restart database
make docker-down && make docker-up
```

### Slow Tests

If tests are slow, run only specific tests:

```bash
# Run specific test file
uv run pytest packages/ingestion/tests/test_normalizers.py -v

# Run specific test
uv run pytest packages/ingestion/tests/test_normalizers.py::TestLangGraphNormalizer::test_normalize_basic_span -v
```

## Test Metrics

| Category | Tests | Status |
|----------|-------|--------|
| Core Models | 9 | ✅ Passing |
| Normalizers | 15 | ✅ Passing |
| OTLP Helpers | 17 | ✅ Passing |
| Integration | 7 | ⚠️ Requires DB |
| **Total** | **48** | **41 Passing** |

All unit tests pass without external dependencies.
Integration tests require Docker and PostgreSQL with TimescaleDB.
