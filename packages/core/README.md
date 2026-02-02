# AgentTrace Core

Shared data models, configuration, and utilities for AgentTrace.

## Overview

The `agenttrace-core` package provides foundational data structures used across all AgentTrace services. It defines the canonical models for traces, spans, agents, messages, and failures using Pydantic for validation and serialization.

## Features

- **Pydantic Models** - Type-safe data structures with validation
- **Database Models** - SQLAlchemy ORM models for PostgreSQL storage
- **Configuration Management** - Centralized configuration with environment variable support
- **Custom Exceptions** - Domain-specific exceptions for error handling
- **Utilities** - Common helper functions for ID generation, time handling, etc.

## Installation

```bash
pip install agenttrace-core
```

Or as part of the monorepo:

```bash
uv sync --package agenttrace-core
```

## Core Models

### Trace

Represents a complete execution flow of an agent system:

```python
from agenttrace_core.models import Trace

trace = Trace(
    trace_id="trace-123",
    name="customer_support_workflow",
    start_time=datetime.utcnow(),
    service_name="support-bot",
    metadata={"user_id": "user-456", "session": "abc"}
)
```

### Span

Represents a single unit of work (agent execution, tool call, etc.):

```python
from agenttrace_core.models import Span

span = Span(
    trace_id="trace-123",
    span_id="span-456",
    parent_span_id=None,
    name="planner_agent",
    start_time=datetime.utcnow(),
    end_time=datetime.utcnow(),
    attributes={
        "agent.name": "Planner",
        "agent.role": "planner",
        "agent.model": "gpt-4"
    },
    events=[],
    status="ok"
)
```

### Agent

Represents metadata about an agent in the system:

```python
from agenttrace_core.models import Agent

agent = Agent(
    agent_id="agent-789",
    name="Planner",
    role="planner",
    framework="langgraph",
    model="gpt-4",
    configuration={"temperature": 0.7}
)
```

### AgentMessage

Represents communication between agents:

```python
from agenttrace_core.models import AgentMessage

message = AgentMessage(
    trace_id="trace-123",
    from_agent="Planner",
    to_agent="Executor",
    message_type="handoff",
    content={"task": "execute_plan", "plan": [...]}
)
```

### FailureAnnotation

Represents a classified failure using MAST taxonomy:

```python
from agenttrace_core.models import FailureAnnotation

annotation = FailureAnnotation(
    trace_id="trace-123",
    span_id="span-456",
    category="reasoning",
    subcategory="planning_error",
    severity="high",
    description="Agent failed to consider edge case"
)
```

## Configuration

The package provides centralized configuration management:

```python
from agenttrace_core.config import get_config

config = get_config()
print(config.database_url)
print(config.otlp_endpoint)
```

Configuration is loaded from environment variables:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/agenttrace
OTLP_HTTP_PORT=4318
API_PORT=8000
```

## Database Schema

The package includes SQLAlchemy ORM models for PostgreSQL storage:

```python
from agenttrace_core.db import Base, TraceModel, SpanModel

# All models inherit from Base
# Use with Alembic migrations for schema management
```

**Tables:**
- `traces` - Top-level trace metadata
- `spans` - Individual execution units (TimescaleDB hypertable)
- `agents` - Agent metadata
- `agent_messages` - Inter-agent communication
- `checkpoints` - State snapshots for replay
- `failure_annotations` - MAST taxonomy classifications

## Usage in Services

### Ingestion Service

```python
from agenttrace_core.models import Trace, Span
from agenttrace_core.db import SpanModel

# Parse OTLP trace
trace = Trace.from_otlp(otlp_trace)

# Store in database
span_model = SpanModel(**span.model_dump())
db.add(span_model)
```

### Analysis Service

```python
from agenttrace_core.models import AgentMessage
from agenttrace_core.db import AgentMessageModel

# Query agent messages for graph construction
messages = db.query(AgentMessageModel).filter_by(trace_id=trace_id).all()
```

## Development

Run tests:

```bash
pytest packages/core/tests -v
```

Type checking:

```bash
uv run mypy packages/core
```

## License

MIT - see root LICENSE file for details
