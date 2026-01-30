# AgentTrace

**Multi-Agent LLM Debugging & Observability Platform**

AgentTrace is an open-source debugging and observability platform purpose-built for multi-agent LLM systems. Unlike existing tools that treat multi-agent workflows as linear chains, AgentTrace models agent coordination as a first-class concern—visualizing communication graphs, attributing failures to specific agents, and enabling time-travel replay debugging.

## Status

**Phase 1: Core Ingestion & Storage** - Complete

AgentTrace is in active development. The OTLP ingestion pipeline is operational and accepting traces from multi-agent systems. See [agenttrace-design-doc.md](./agenttrace-design-doc.md) for the complete architecture and roadmap.

### Currently Working

- OTLP trace ingestion (HTTP endpoint with protobuf and JSON support)
- Framework-specific normalization for LangGraph, AutoGen, CrewAI, and generic agents
- TimescaleDB-optimized storage for spans, agents, and inter-agent messages
- Batch writing with connection pooling for high-throughput ingestion
- Comprehensive test suite with 48 tests (41 passing unit tests, 7 integration tests)

## Features

**Available Now:**
- **OTLP Native Ingestion** - Production-ready HTTP endpoint accepting OpenTelemetry Protocol traces
- **Framework Agnostic Normalization** - Intelligent parsing for LangGraph, AutoGen, CrewAI, and custom agents
- **Time-Series Optimized Storage** - PostgreSQL with TimescaleDB for efficient span querying
- **Agent Metadata Tracking** - Automatic extraction of agent names, roles, frameworks, and configurations

**Coming Soon:**
- **Agent Communication Graphs** - Visual representation of agent interactions and message flows
- **Failure Attribution** - Root cause analysis pinpointing which agent caused pipeline failures
- **Time-Travel Replay** - Checkpoint-based debugging to replay from arbitrary points in execution
- **Web UI** - Interactive dashboard for exploring traces and debugging multi-agent systems

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Docker and Docker Compose (for local development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jimmybentley/AgentTrace.git
cd AgentTrace
```

2. Install all dependencies:
```bash
make install
```

3. Start the database:
```bash
make docker-up
```

This starts PostgreSQL with TimescaleDB on `localhost:5432`:
- Database: `agenttrace`
- User: `agenttrace`
- Password: `dev_password`

4. Run database migrations:
```bash
make migrate
```

5. Start the ingestion service:
```bash
make run-ingestion
```

The OTLP ingestion endpoint is now available at `http://localhost:4318/v1/traces`.

### Verify Installation

Run the test suite to verify everything is working:

```bash
# Unit tests (no database required)
make test

# Integration tests (requires database)
make test-integration

# Linting and formatting
make lint

# Verify all imports
make verify
```

Expected output:
```
✓ 41 unit tests passing
✓ 7 integration tests passing
✓ All imports verified
```

### Sending Your First Trace

Once the ingestion service is running, you can send OTLP traces via HTTP:

```bash
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{
    "resourceSpans": [{
      "resource": {
        "attributes": [
          {"key": "service.name", "value": {"stringValue": "my-agent-system"}},
          {"key": "agent.framework", "value": {"stringValue": "langgraph"}}
        ]
      },
      "scopeSpans": [{
        "spans": [{
          "traceId": "0102030405060708090a0b0c0d0e0f10",
          "spanId": "0102030405060708",
          "name": "agent_execution",
          "startTimeUnixNano": "1640000000000000000",
          "endTimeUnixNano": "1640000001000000000"
        }]
      }]
    }]
  }'
```

The trace will be normalized, stored in TimescaleDB, and available for querying.

## Project Structure

```
agenttrace/
├── packages/
│   ├── core/                    # Shared data models and utilities
│   │   └── agenttrace_core/
│   │       ├── models.py        # Pydantic models (Trace, Span, Agent)
│   │       ├── config.py        # Configuration management
│   │       └── exceptions.py    # Custom exceptions
│   │
│   ├── ingestion/               # OTLP ingestion service
│   │   └── agenttrace_ingestion/
│   │       ├── server.py        # FastAPI app
│   │       └── normalizers/     # Framework-specific normalizers
│   │
│   ├── analysis/                # Analysis engine
│   │   └── agenttrace_analysis/
│   │       └── mast/            # MAST taxonomy implementation
│   │
│   ├── replay/                  # Replay engine
│   │   └── agenttrace_replay/
│   │
│   └── sdk/python/              # Python SDK for instrumentation
│       └── agenttrace/
│           └── integrations/    # LangGraph, AutoGen, CrewAI
│
├── web/                         # React frontend (Phase 3)
├── migrations/                  # Database migrations
├── docker-compose.dev.yml       # Local development setup
└── Makefile                     # Development commands
```

## Development

### Available Commands

The project includes a comprehensive Makefile for common development tasks:

```bash
make help              # Show all available commands
make install           # Install all dependencies
make dev               # Set up development environment with pre-commit hooks
make test              # Run unit tests (41 tests)
make test-integration  # Run integration tests (7 tests, requires database)
make lint              # Run linting and format checks
make format            # Auto-format code with ruff
make migrate           # Run database migrations
make run-ingestion     # Start the OTLP ingestion service
make docker-up         # Start PostgreSQL with TimescaleDB
make docker-down       # Stop all Docker services
make docker-logs       # View database logs
make clean             # Clean build artifacts and caches
make verify            # Verify installation and imports
```

### Running Tests

AgentTrace has 48 tests organized into unit and integration suites. See [TESTING.md](./TESTING.md) for detailed testing documentation.

```bash
# Run all unit tests (no database required)
make test

# Run integration tests (requires database)
make docker-up
make migrate
make test-integration

# Run tests for a specific package
uv run pytest packages/core/tests -v
cd packages/ingestion && uv run pytest tests/test_normalizers.py -v

# Run with coverage
uv run pytest packages/ --cov=agenttrace_core --cov=agenttrace_ingestion
```

### Code Quality

The project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting with strict type checking:

```bash
# Check code quality
make lint

# Auto-format all code
make format

# Check for security issues
uv run ruff check packages/ --select S
```

## Architecture

AgentTrace is built as a Python monorepo using `uv` workspace management:

- **Core** - Shared Pydantic models and utilities
- **Ingestion** - FastAPI service for receiving OTLP traces
- **Analysis** - Graph construction and failure classification
- **Replay** - Checkpoint management and replay debugging
- **SDK** - Client libraries for instrumentation

See [agenttrace-design-doc.md](./agenttrace-design-doc.md) for detailed architecture.

## Database

AgentTrace uses PostgreSQL 16 with the TimescaleDB extension for time-series optimization on span data.

### Schema

The database includes 6 core tables:

- **traces** - Top-level trace metadata with session and user context
- **spans** - Individual execution units (TimescaleDB hypertable partitioned by start_time)
- **agents** - Agent metadata (name, role, framework, configuration)
- **agent_messages** - Inter-agent communication records
- **checkpoints** - State snapshots for time-travel replay
- **failure_annotations** - MAST taxonomy failure classifications

Migrations are managed with Alembic and located in `migrations/versions/`.

### Local Development

```bash
# Start PostgreSQL with TimescaleDB
make docker-up

# Run migrations
make migrate

# Connect with psql
psql postgresql://agenttrace:dev_password@localhost:5432/agenttrace

# View migration history
uv run alembic history

# Stop database
make docker-down
```

### Environment Variables

Database connection can be configured via environment variables:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
make migrate
```

## Roadmap

- [x] **Phase 0** - Project scaffolding and workspace setup
- [x] **Phase 1** - Core ingestion & storage (OTLP endpoint, normalizers, TimescaleDB schema) ← **Current**
- [ ] **Phase 2** - Analysis engine & graph construction (communication graphs, MAST taxonomy)
- [ ] **Phase 3** - Web UI (React dashboard, trace visualization, debugging interface)
- [ ] **Phase 4** - Replay engine (checkpoint management, state reconstruction)
- [ ] **Phase 5** - SDK & integrations (Python SDK, framework-specific instrumentation)

See [agenttrace-design-doc.md](./agenttrace-design-doc.md) for detailed specifications of each phase.

## Contributing

AgentTrace is in active development. The ingestion pipeline is operational and contributions are welcome.

Before contributing:
1. Review the [design document](./agenttrace-design-doc.md) for architecture context
2. Check existing issues and PRs to avoid duplication
3. Run `make test` and `make lint` to ensure code quality
4. Follow the existing code style (Ruff formatting, type hints required)

Areas where contributions would be particularly valuable:
- Additional framework normalizers (Semantic Kernel, Haystack, etc.)
- Test coverage improvements
- Documentation and examples
- Performance optimizations for high-throughput ingestion

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [LangSmith](https://www.langchain.com/langsmith) - LangChain's observability platform
- [Langfuse](https://langfuse.com/) - Open-source LLM observability
- [Arize Phoenix](https://phoenix.arize.com/) - ML observability platform
- [OpenTelemetry](https://opentelemetry.io/) - Observability standard

## Acknowledgments

- Design inspired by the [MAST taxonomy](https://arxiv.org/abs/2503.13657) for multi-agent system failures
- Built on [OpenTelemetry](https://opentelemetry.io/) semantic conventions
