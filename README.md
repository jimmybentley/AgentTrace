# AgentTrace

**Multi-Agent LLM Debugging & Observability Platform**

AgentTrace is an open-source debugging and observability platform purpose-built for multi-agent LLM systems. Unlike existing tools that treat multi-agent workflows as linear chains, AgentTrace models agent coordination as a first-class concern—visualizing communication graphs, attributing failures to specific agents, and enabling time-travel replay debugging.

## Overview

AgentTrace is a complete, production-ready debugging and observability platform for multi-agent LLM systems. The entire platform is operational and ready to use.

## Features

### Core Capabilities

- **🔌 OTLP Native Ingestion** - Production-ready HTTP endpoint accepting OpenTelemetry Protocol traces
- **🔄 Framework Agnostic** - Intelligent parsing for LangGraph, AutoGen, CrewAI, and custom agents
- **⚡ Time-Series Optimized Storage** - PostgreSQL with TimescaleDB for efficient span querying
- **🤖 Agent Metadata Tracking** - Automatic extraction of agent names, roles, frameworks, and configurations

### Visualization & Analysis

- **📊 Agent Communication Graphs** - D3.js force-directed graph showing agent interactions and message flows
- **🔍 Failure Attribution** - MAST taxonomy-based classification of multi-agent system failures
- **📈 Interactive Timeline View** - Gantt-style span execution visualization
- **🎯 Trace Explorer** - Paginated trace list with filtering and search
- **⚠️ Failure Analysis Panel** - Display and filter failure annotations by category

### Debugging Tools

- **⏪ Time-Travel Replay** - Checkpoint-based debugging to replay execution from arbitrary points
- **🔄 State Reconstruction** - Recreate agent state at any checkpoint for debugging
- **📝 Diff Visualization** - Compare original vs. replay outputs to identify issues

### SDK & Integrations

- **🐍 Python SDK** - Manual and auto-instrumentation with decorators
- **🔧 Framework Auto-Instrumentation** - Automatic tracing for LangGraph, AutoGen, and CrewAI
- **📡 OpenTelemetry-Based** - Standard OTLP export to any compatible backend

## Architecture

AgentTrace consists of five main components that work together to provide comprehensive observability:

```mermaid
graph LR
    A[Your Agent App] -->|OTLP Traces| B[Ingestion Service]
    B -->|Normalized Data| C[(PostgreSQL + TimescaleDB)]
    C --> D[Analysis API]
    D --> E[Web UI]
    D -->|Graphs & Metrics| E
    D -->|Replay Engine| F[Checkpoint Manager]
    F --> C

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#f0e1ff
    style D fill:#e1ffe1
    style E fill:#ffe1e1
    style F fill:#fffacd
```

**Component Overview:**

- **Ingestion Service** (`packages/ingestion`) - OTLP HTTP endpoint that receives traces and normalizes them for storage
- **Core Models** (`packages/core`) - Shared data models (Trace, Span, Agent) used across all services
- **Analysis Engine** (`packages/analysis`) - Builds agent communication graphs and classifies failures using MAST taxonomy
- **Replay Engine** (`packages/replay`) - Manages checkpoints and enables time-travel debugging
- **Python SDK** (`packages/sdk/python`) - Client library for instrumenting agent applications
- **Web UI** (`web`) - React dashboard for visualizing traces, graphs, and debugging

## Quick Start

Get AgentTrace running in under 5 minutes:

```bash
# 1. Clone and navigate to the repository
git clone https://github.com/jimmybentley/AgentTrace.git
cd AgentTrace

# 2. Start the full stack with Docker Compose
docker compose up -d

# 3. Open the web UI
open http://localhost:3000
```

That's it! The full stack is now running:
- **Web UI**: http://localhost:3000
- **Analysis API**: http://localhost:8000/api
- **OTLP Ingestion**: http://localhost:4318/v1/traces
- **Database**: localhost:5432 (agenttrace/agenttrace/dev_password)

### Send Your First Trace

Instrument your agent application with the Python SDK:

```bash
pip install agenttrace
```

```python
import agenttrace

# Auto-instrument your framework
agenttrace.instrument(["langgraph"])

# Or use manual instrumentation
from agenttrace import AgentTracer

tracer = AgentTracer(endpoint="http://localhost:4318")

@tracer.agent("Planner", role="planner")
async def plan(task: str) -> str:
    return f"Plan for: {task}"
```

Traces will automatically appear in the web UI at http://localhost:3000.

### Development Setup

For local development with hot reloading:

```bash
# Install dependencies
make install

# Start database only
make docker-up && make migrate

# Start API server (with hot reload)
make run-api

# Start web UI (with hot reload)
make run-web
```

## Screenshots

### Trace List
![Trace List](docs/screenshots/trace-list.png)
*Browse all traces with filtering, search, and status indicators*

### Agent Communication Graph
![Agent Graph](docs/screenshots/agent-graph.png)
*D3.js force-directed graph showing agent interactions and message flows*

### Span Timeline
![Timeline View](docs/screenshots/timeline.png)
*Gantt-style timeline view of span execution with nested relationships*

### Failure Analysis
![Failure Panel](docs/screenshots/failure-panel.png)
*MAST taxonomy-based failure classification and filtering*

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
├── web/                         # React frontend
│   ├── src/
│   │   ├── api/                 # API client and type definitions
│   │   ├── hooks/               # React Query hooks
│   │   ├── components/          # React components
│   │   │   ├── AgentGraph/      # D3.js graph visualization
│   │   │   ├── TraceList/       # Trace list and filters
│   │   │   ├── TraceDetail/     # Trace detail view
│   │   │   ├── SpanTimeline/    # Gantt-style timeline
│   │   │   └── FailurePanel/    # Failure annotations
│   │   ├── pages/               # Page components
│   │   └── utils/               # Utility functions
│   └── package.json
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

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Getting Started Guide](docs/getting-started.md)** - Step-by-step setup instructions
- **[Architecture Overview](docs/architecture.md)** - System design and component interaction
- **[API Reference](docs/api-reference.md)** - Complete REST API documentation
- **[SDK Guide](docs/sdk-guide.md)** - Python SDK usage and examples
- **[Deployment Guide](docs/deployment.md)** - Docker Compose, Kubernetes, and production setup

Package-specific documentation:
- [Core Models](packages/core/README.md)
- [Ingestion Service](packages/ingestion/README.md)
- [Analysis Engine](packages/analysis/README.md)
- [Replay Engine](packages/replay/README.md)
- [Python SDK](packages/sdk/python/README.md)
- [Web UI](web/README.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

**Quick start for contributors:**

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/AgentTrace.git
cd AgentTrace

# Install development dependencies
make dev

# Run tests
make test

# Format code
make format
```

Areas where contributions are especially valuable:
- Additional framework integrations (Semantic Kernel, Haystack, etc.)
- Performance optimizations
- Documentation and examples
- Bug fixes and issue resolution

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
