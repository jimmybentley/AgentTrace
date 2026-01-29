# AgentTrace

**Multi-Agent LLM Debugging & Observability Platform**

AgentTrace is an open-source debugging and observability platform purpose-built for multi-agent LLM systems. Unlike existing tools that treat multi-agent workflows as linear chains, AgentTrace models agent coordination as a first-class concern—visualizing communication graphs, attributing failures to specific agents, and enabling time-travel replay debugging.

## Status

🚧 **Phase 0: Project Scaffolding** - In Progress

This project is in active development. Phase 0 (scaffolding) is complete. See [agenttrace-design-doc.md](./agenttrace-design-doc.md) for the full roadmap.

## Features (Planned)

- 🔍 **Agent Communication Graphs** - Visualize how agents interact, not just parent-child relationships
- 🎯 **Failure Attribution** - Pinpoint which agent caused failures in multi-agent pipelines
- ⏮️ **Time-Travel Replay** - Debug from arbitrary checkpoints, not just from the start
- 🔌 **Framework Agnostic** - Support for LangGraph, AutoGen, CrewAI, and custom agents
- 📊 **OTLP Native** - Built on OpenTelemetry for standardized trace ingestion

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Docker and Docker Compose (for local development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AgentTrace.git
cd AgentTrace
```

2. Install dependencies:
```bash
make install
```

3. Start development services:
```bash
make docker-up
```

This will start:
- PostgreSQL with TimescaleDB extension on `localhost:5432`
  - Database: `agenttrace`
  - User: `agenttrace`
  - Password: `dev_password`

### Verify Installation

```bash
# Run tests
make test

# Run linting
make lint

# Verify imports work
make verify
```

Expected output:
```
✓ Core models importable
✓ Ingestion server importable
✓ All tests passed
```

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

### Available Make Commands

```bash
make help         # Show all available commands
make install      # Install all dependencies
make dev          # Set up dev environment with pre-commit hooks
make test         # Run all tests
make lint         # Run linting checks
make format       # Format code with ruff
make docker-up    # Start Docker services
make docker-down  # Stop Docker services
make clean        # Clean build artifacts
make verify       # Verify installation
```

### Running Tests

```bash
# Run all tests
make test

# Run tests for a specific package
uv run pytest packages/core/tests -v

# Run with coverage
uv run pytest packages/core/tests --cov=agenttrace_core
```

### Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check formatting
make lint

# Auto-format code
make format
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

AgentTrace uses PostgreSQL with the TimescaleDB extension for time-series optimization.

### Local Development Database

```bash
# Start database
make docker-up

# Connect with psql
psql postgresql://agenttrace:dev_password@localhost:5432/agenttrace

# Stop database
make docker-down
```

## Roadmap

- [x] **Phase 0** (Week 1) - Project scaffolding ← **Current**
- [ ] **Phase 1** (Weeks 2-3) - Core ingestion & storage
- [ ] **Phase 2** (Weeks 4-5) - Analysis engine & graph construction
- [ ] **Phase 3** (Weeks 6-8) - Web UI
- [ ] **Phase 4** (Weeks 9-11) - Replay engine
- [ ] **Phase 5** (Weeks 12-14) - SDK & integrations

## Contributing

This project is in early development. Contributions will be welcome once Phase 1 is complete.

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
