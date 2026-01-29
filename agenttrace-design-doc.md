# AgentTrace: Multi-Agent LLM Debugging & Observability Platform

**Author:** James  
**Status:** Draft  
**Last Updated:** January 2026  

---

## 1. Executive Summary

AgentTrace is an open-source debugging and observability platform purpose-built for multi-agent LLM systems. Unlike existing tools (LangSmith, Langfuse, Arize Phoenix) that treat multi-agent workflows as linear chains, AgentTrace models agent coordination as a first-class concern—visualizing communication graphs, attributing failures to specific agents, and enabling time-travel replay debugging.

**Key Insight:** 79% of multi-agent system failures stem from specification problems and coordination failures, not infrastructure issues. Current observability tools miss these entirely.

---

## 2. Problem Statement

### 2.1 Current State

Multi-agent LLM systems (built with LangGraph, AutoGen, CrewAI, etc.) fail at rates of 41-86% in production. Developers have no effective way to:

1. **Understand agent interactions** — Existing trace views show parent-child hierarchies, but agents communicate laterally, share resources, and have emergent coordination patterns
2. **Attribute failures** — When a 5-agent pipeline fails, which agent caused it? At what step?
3. **Replay and debug** — Traditional "re-run from start" is expensive and non-deterministic; developers need to replay from specific agent states
4. **Handle heterogeneous agents** — Production systems mix Claude, GPT, open-source models; tools assume homogeneous stacks

### 2.2 Target Users

- **Primary:** ML engineers building multi-agent systems (LangGraph, AutoGen, CrewAI)
- **Secondary:** Platform teams providing internal agent infrastructure
- **Tertiary:** Researchers studying agent coordination

---

## 3. Goals & Non-Goals

### 3.1 Goals

| Priority | Goal |
|----------|------|
| P0 | Ingest and store traces from multi-agent systems via OpenTelemetry |
| P0 | Visualize agent communication as a directed graph (not just a call tree) |
| P0 | Attribute failures to specific agents with actionable diagnostics |
| P1 | Enable replay debugging from arbitrary checkpoints |
| P1 | Framework-agnostic: support LangGraph, AutoGen, CrewAI, and custom agents |
| P2 | Classify failures using MAST taxonomy (specification, coordination, verification) |
| P2 | Cost and latency analysis per agent |

### 3.2 Non-Goals (V1)

- Real-time alerting (integrate with existing tools like PagerDuty)
- Prompt management / versioning (use Langfuse, LangSmith)
- Fine-tuning data pipelines
- Hosted SaaS offering (open-source self-hosted only)
- Mobile UI

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AgentTrace                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Ingestion  │    │    Core      │    │     Web      │                   │
│  │   Service    │───▶│   Storage    │◀───│     UI       │                   │
│  │  (OTLP/HTTP) │    │ (Postgres +  │    │   (React)    │                   │
│  └──────────────┘    │  TimescaleDB)│    └──────────────┘                   │
│         ▲            └──────────────┘           │                           │
│         │                   │                   │                           │
│         │            ┌──────▼──────┐            │                           │
│         │            │  Analysis   │            │                           │
│         │            │   Engine    │◀───────────┘                           │
│         │            │ (Python)    │                                        │
│         │            └─────────────┘                                        │
│         │                   │                                               │
│         │            ┌──────▼──────┐                                        │
│         │            │   Replay    │                                        │
│         │            │   Engine    │                                        │
│         │            └─────────────┘                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ▲                    ▲                    ▲
        │                    │                    │
   OTLP/gRPC            HTTP/REST              WebSocket
        │                    │                    │
┌───────┴────────┐  ┌────────┴───────┐  ┌────────┴───────┐
│   LangGraph    │  │    AutoGen     │  │    CrewAI      │
│   Application  │  │   Application  │  │   Application  │
└────────────────┘  └────────────────┘  └────────────────┘
```

### 4.1 Component Overview

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Ingestion Service** | Receive OTLP traces, normalize agent-specific attributes, batch writes | Python (FastAPI) + OTLP receiver |
| **Core Storage** | Store traces, spans, agent states, checkpoints | PostgreSQL + TimescaleDB extension |
| **Analysis Engine** | Failure classification, graph construction, metrics aggregation | Python |
| **Replay Engine** | Checkpoint management, state restoration, re-execution orchestration | Python |
| **Web UI** | Visualization, debugging interface, search | React + TypeScript + D3.js |

---

## 5. Data Model

### 5.1 Core Entities

```sql
-- A single multi-agent execution (e.g., one user request)
CREATE TABLE traces (
    trace_id        UUID PRIMARY KEY,
    name            TEXT,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,
    status          TEXT CHECK (status IN ('running', 'completed', 'failed', 'timeout')),
    metadata        JSONB,
    
    -- Aggregated metrics
    total_tokens    INTEGER,
    total_cost_usd  DECIMAL(10, 6),
    total_latency_ms INTEGER,
    agent_count     INTEGER,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Individual operations within a trace
CREATE TABLE spans (
    span_id         UUID PRIMARY KEY,
    trace_id        UUID REFERENCES traces(trace_id),
    parent_span_id  UUID REFERENCES spans(span_id),
    agent_id        UUID REFERENCES agents(agent_id),
    
    name            TEXT NOT NULL,
    kind            TEXT CHECK (kind IN ('llm_call', 'tool_call', 'agent_message', 'checkpoint', 'handoff')),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,
    status          TEXT CHECK (status IN ('ok', 'error', 'timeout')),
    
    -- LLM-specific
    model           TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        DECIMAL(10, 6),
    
    -- Content (encrypted at rest)
    input           JSONB,
    output          JSONB,
    error           JSONB,
    
    attributes      JSONB,  -- OpenTelemetry semantic attributes
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Agent definitions within a trace
CREATE TABLE agents (
    agent_id        UUID PRIMARY KEY,
    trace_id        UUID REFERENCES traces(trace_id),
    
    name            TEXT NOT NULL,
    role            TEXT,           -- e.g., "planner", "coder", "reviewer"
    model           TEXT,           -- e.g., "claude-3-opus", "gpt-4"
    framework       TEXT,           -- e.g., "langgraph", "autogen", "crewai"
    
    config          JSONB,          -- Agent-specific configuration
    
    -- Aggregated metrics for this agent in this trace
    total_spans     INTEGER,
    total_tokens    INTEGER,
    total_cost_usd  DECIMAL(10, 6),
    error_count     INTEGER,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(trace_id, name)
);

-- Inter-agent communication edges
CREATE TABLE agent_messages (
    message_id      UUID PRIMARY KEY,
    trace_id        UUID REFERENCES traces(trace_id),
    span_id         UUID REFERENCES spans(span_id),
    
    from_agent_id   UUID REFERENCES agents(agent_id),
    to_agent_id     UUID REFERENCES agents(agent_id),
    
    message_type    TEXT CHECK (message_type IN ('request', 'response', 'broadcast', 'handoff')),
    content         JSONB,
    timestamp       TIMESTAMPTZ NOT NULL,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Checkpoints for replay
CREATE TABLE checkpoints (
    checkpoint_id   UUID PRIMARY KEY,
    trace_id        UUID REFERENCES traces(trace_id),
    span_id         UUID REFERENCES spans(span_id),
    agent_id        UUID REFERENCES agents(agent_id),
    
    name            TEXT,
    state           JSONB NOT NULL,     -- Serialized agent state
    timestamp       TIMESTAMPTZ NOT NULL,
    
    -- Replay metadata
    replay_count    INTEGER DEFAULT 0,
    last_replayed   TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Failure classifications
CREATE TABLE failure_annotations (
    annotation_id   UUID PRIMARY KEY,
    trace_id        UUID REFERENCES traces(trace_id),
    span_id         UUID REFERENCES spans(span_id),
    agent_id        UUID REFERENCES agents(agent_id),
    
    -- MAST taxonomy
    category        TEXT CHECK (category IN ('specification', 'coordination', 'verification')),
    failure_mode    TEXT,           -- e.g., "role_ambiguity", "handoff_failure", "output_validation"
    confidence      DECIMAL(3, 2),  -- 0.00 - 1.00
    
    -- Source
    source          TEXT CHECK (source IN ('auto', 'manual', 'llm_judge')),
    reasoning       TEXT,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_spans_trace_id ON spans(trace_id);
CREATE INDEX idx_spans_agent_id ON spans(agent_id);
CREATE INDEX idx_spans_start_time ON spans(start_time DESC);
CREATE INDEX idx_agent_messages_trace ON agent_messages(trace_id);
CREATE INDEX idx_checkpoints_trace ON checkpoints(trace_id);

-- TimescaleDB hypertable for time-series queries
SELECT create_hypertable('spans', 'start_time', if_not_exists => TRUE);
```

### 5.2 OpenTelemetry Semantic Conventions

We extend OTEL semantic conventions for multi-agent systems:

```yaml
# Agent identification
agent.id: string           # Unique agent identifier within trace
agent.name: string         # Human-readable name (e.g., "CodeReviewer")
agent.role: string         # Functional role (e.g., "planner", "executor")
agent.model: string        # LLM model used (e.g., "claude-3-opus-20240229")
agent.framework: string    # Framework (e.g., "langgraph", "autogen")

# Inter-agent communication
message.from_agent: string
message.to_agent: string
message.type: string       # request | response | broadcast | handoff
message.content_hash: string  # For deduplication

# Coordination events
coordination.type: string  # tool_lock | resource_wait | consensus | vote
coordination.participants: string[]
coordination.outcome: string

# Checkpoint markers
checkpoint.name: string
checkpoint.state_size_bytes: int
checkpoint.restorable: bool
```

---

## 6. Implementation Phases

---

## Phase 0: Project Scaffolding (Week 1)

### Objectives
- Set up monorepo structure
- Configure development environment
- Establish CI/CD pipeline

### Directory Structure

```
agenttrace/
├── README.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile
├── pyproject.toml
│
├── packages/
│   ├── core/                    # Shared utilities, data models
│   │   ├── agenttrace_core/
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Pydantic models
│   │   │   ├── config.py        # Configuration management
│   │   │   └── exceptions.py
│   │   ├── pyproject.toml
│   │   └── tests/
│   │
│   ├── ingestion/               # OTLP ingestion service
│   │   ├── agenttrace_ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── server.py        # FastAPI app
│   │   │   ├── otlp.py          # OTLP protocol handling
│   │   │   ├── normalizers/     # Framework-specific normalizers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── langgraph.py
│   │   │   │   ├── autogen.py
│   │   │   │   └── crewai.py
│   │   │   └── writers.py       # Database writers
│   │   ├── pyproject.toml
│   │   └── tests/
│   │
│   ├── analysis/                # Analysis engine
│   │   ├── agenttrace_analysis/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py         # Graph construction
│   │   │   ├── classifier.py    # Failure classification
│   │   │   ├── metrics.py       # Aggregation
│   │   │   └── mast/            # MAST taxonomy implementation
│   │   │       ├── __init__.py
│   │   │       ├── taxonomy.py
│   │   │       └── rules.py
│   │   ├── pyproject.toml
│   │   └── tests/
│   │
│   ├── replay/                  # Replay engine
│   │   ├── agenttrace_replay/
│   │   │   ├── __init__.py
│   │   │   ├── checkpoint.py
│   │   │   ├── executor.py
│   │   │   └── differ.py
│   │   ├── pyproject.toml
│   │   └── tests/
│   │
│   └── sdk/                     # Client SDK for instrumentation
│       ├── python/
│       │   ├── agenttrace/
│       │   │   ├── __init__.py
│       │   │   ├── tracer.py
│       │   │   ├── decorators.py
│       │   │   └── integrations/
│       │   │       ├── langgraph.py
│       │   │       ├── autogen.py
│       │   │       └── crewai.py
│       │   ├── pyproject.toml
│       │   └── tests/
│       └── typescript/          # Future
│
├── web/                         # React frontend
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TraceList/
│   │   │   ├── AgentGraph/
│   │   │   ├── SpanDetail/
│   │   │   ├── ReplayControls/
│   │   │   └── FailurePanel/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   └── tests/
│
├── migrations/                  # Database migrations (Alembic)
│   ├── alembic.ini
│   └── versions/
│
├── deploy/
│   ├── kubernetes/
│   └── docker/
│
└── docs/
    ├── getting-started.md
    ├── sdk-reference.md
    └── architecture.md
```

### Tasks

1. **Initialize monorepo**
   ```bash
   # Use uv for Python package management
   uv init agenttrace
   cd agenttrace
   
   # Create workspace structure
   mkdir -p packages/{core,ingestion,analysis,replay,sdk/python}
   mkdir -p web migrations deploy docs
   ```

2. **Configure shared tooling**
   - `pyproject.toml` with workspace configuration
   - Ruff for linting/formatting
   - pytest configuration
   - Pre-commit hooks

3. **Set up Docker Compose for local development**
   ```yaml
   # docker-compose.dev.yml
   services:
     postgres:
       image: timescale/timescaledb:latest-pg16
       environment:
         POSTGRES_DB: agenttrace
         POSTGRES_USER: agenttrace
         POSTGRES_PASSWORD: dev_password
       ports:
         - "5432:5432"
       volumes:
         - pgdata:/var/lib/postgresql/data
     
     ingestion:
       build:
         context: .
         dockerfile: packages/ingestion/Dockerfile
       ports:
         - "4317:4317"  # OTLP gRPC
         - "4318:4318"  # OTLP HTTP
       environment:
         DATABASE_URL: postgresql://agenttrace:dev_password@postgres:5432/agenttrace
       depends_on:
         - postgres
     
     web:
       build:
         context: ./web
       ports:
         - "3000:3000"
       environment:
         API_URL: http://localhost:8000
   
   volumes:
     pgdata:
   ```

4. **Set up GitHub Actions CI**
   - Lint and type-check on PR
   - Run tests
   - Build Docker images

### Deliverables
- [ ] Monorepo structure with all packages initialized
- [ ] Docker Compose working locally
- [ ] CI pipeline running
- [ ] README with setup instructions

---

## Phase 1: Core Ingestion & Storage (Weeks 2-3)

### Objectives
- Accept OTLP traces from any source
- Normalize agent-specific attributes
- Store in PostgreSQL with efficient indexing

### 1.1 OTLP Ingestion Service

```python
# packages/ingestion/agenttrace_ingestion/server.py

from fastapi import FastAPI, Request
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
from opentelemetry.proto.trace.v1 import trace_pb2

from agenttrace_core.models import Trace, Span, Agent, AgentMessage
from .normalizers import get_normalizer
from .writers import DatabaseWriter

app = FastAPI(title="AgentTrace Ingestion")

@app.post("/v1/traces")
async def receive_traces(request: Request):
    """
    OTLP HTTP endpoint for trace ingestion.
    
    Accepts: application/x-protobuf or application/json
    """
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    
    if "protobuf" in content_type:
        export_request = trace_service_pb2.ExportTraceServiceRequest()
        export_request.ParseFromString(body)
    else:
        # JSON handling
        export_request = trace_service_pb2.ExportTraceServiceRequest()
        Parse(body, export_request)
    
    # Process each resource span
    for resource_spans in export_request.resource_spans:
        resource_attrs = _extract_attributes(resource_spans.resource.attributes)
        framework = resource_attrs.get("agent.framework", "unknown")
        
        # Get framework-specific normalizer
        normalizer = get_normalizer(framework)
        
        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                normalized = normalizer.normalize(span, resource_attrs)
                await writer.write(normalized)
    
    return {"status": "ok"}


@app.post("/v1/traces/grpc")
async def receive_traces_grpc():
    """gRPC endpoint - implement with grpcio"""
    pass
```

### 1.2 Framework Normalizers

```python
# packages/ingestion/agenttrace_ingestion/normalizers/langgraph.py

from typing import Any
from opentelemetry.proto.trace.v1 import trace_pb2
from agenttrace_core.models import NormalizedSpan, AgentInfo, MessageInfo

class LangGraphNormalizer:
    """
    Normalize LangGraph traces to AgentTrace format.
    
    LangGraph uses:
    - "langgraph.node" for agent names
    - "langgraph.step" for execution order
    - Parent-child relationships for subgraph calls
    """
    
    FRAMEWORK = "langgraph"
    
    def normalize(
        self, 
        span: trace_pb2.Span, 
        resource_attrs: dict[str, Any]
    ) -> NormalizedSpan:
        attrs = _extract_attributes(span.attributes)
        
        # Extract agent information
        agent_info = None
        if "langgraph.node" in attrs:
            agent_info = AgentInfo(
                name=attrs["langgraph.node"],
                role=attrs.get("langgraph.node_type", "unknown"),
                model=attrs.get("llm.model", attrs.get("gen_ai.request.model")),
            )
        
        # Extract inter-agent messages
        messages = []
        if span.name == "langgraph.edge":
            messages.append(MessageInfo(
                from_agent=attrs.get("langgraph.source_node"),
                to_agent=attrs.get("langgraph.target_node"),
                message_type="handoff",
                content=attrs.get("langgraph.state", {}),
            ))
        
        # Determine span kind
        kind = self._determine_kind(span, attrs)
        
        return NormalizedSpan(
            span_id=span.span_id.hex(),
            trace_id=span.trace_id.hex(),
            parent_span_id=span.parent_span_id.hex() if span.parent_span_id else None,
            name=span.name,
            kind=kind,
            start_time=_ns_to_datetime(span.start_time_unix_nano),
            end_time=_ns_to_datetime(span.end_time_unix_nano),
            status=self._map_status(span.status),
            agent=agent_info,
            messages=messages,
            model=attrs.get("llm.model") or attrs.get("gen_ai.request.model"),
            input_tokens=attrs.get("llm.token_count.prompt") or attrs.get("gen_ai.usage.input_tokens"),
            output_tokens=attrs.get("llm.token_count.completion") or attrs.get("gen_ai.usage.output_tokens"),
            input=self._extract_input(attrs),
            output=self._extract_output(attrs),
            error=self._extract_error(span),
            attributes=attrs,
        )
    
    def _determine_kind(self, span: trace_pb2.Span, attrs: dict) -> str:
        name = span.name.lower()
        if "llm" in name or "chat" in name or "gen_ai" in attrs.get("gen_ai.operation.name", ""):
            return "llm_call"
        if "tool" in name:
            return "tool_call"
        if "edge" in name:
            return "handoff"
        if "checkpoint" in name:
            return "checkpoint"
        return "agent_message"
```

### 1.3 Database Writer

```python
# packages/ingestion/agenttrace_ingestion/writers.py

import asyncpg
from contextlib import asynccontextmanager
from agenttrace_core.models import NormalizedSpan

class DatabaseWriter:
    def __init__(self, database_url: str, batch_size: int = 100):
        self.database_url = database_url
        self.batch_size = batch_size
        self._pool: asyncpg.Pool | None = None
        self._batch: list[NormalizedSpan] = []
    
    async def connect(self):
        self._pool = await asyncpg.create_pool(self.database_url, min_size=5, max_size=20)
    
    async def write(self, span: NormalizedSpan):
        """Buffer spans and batch write for efficiency."""
        self._batch.append(span)
        
        if len(self._batch) >= self.batch_size:
            await self._flush()
    
    async def _flush(self):
        if not self._batch:
            return
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Upsert traces
                traces = {s.trace_id: s for s in self._batch}
                await conn.executemany(
                    """
                    INSERT INTO traces (trace_id, name, start_time, status, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (trace_id) DO UPDATE SET
                        end_time = GREATEST(traces.end_time, EXCLUDED.end_time),
                        status = EXCLUDED.status
                    """,
                    [(t.trace_id, t.name, t.start_time, "running", {}) for t in traces.values()]
                )
                
                # Upsert agents
                agents = [s for s in self._batch if s.agent]
                if agents:
                    await conn.executemany(
                        """
                        INSERT INTO agents (agent_id, trace_id, name, role, model, framework)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (trace_id, name) DO NOTHING
                        """,
                        [
                            (s.agent.id, s.trace_id, s.agent.name, s.agent.role, s.agent.model, s.agent.framework)
                            for s in agents
                        ]
                    )
                
                # Insert spans
                await conn.executemany(
                    """
                    INSERT INTO spans (
                        span_id, trace_id, parent_span_id, agent_id, name, kind,
                        start_time, end_time, status, model, input_tokens, output_tokens,
                        cost_usd, input, output, error, attributes
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    ON CONFLICT (span_id) DO NOTHING
                    """,
                    [self._span_to_tuple(s) for s in self._batch]
                )
                
                # Insert agent messages
                messages = [m for s in self._batch for m in s.messages]
                if messages:
                    await conn.executemany(
                        """
                        INSERT INTO agent_messages (
                            message_id, trace_id, span_id, from_agent_id, to_agent_id,
                            message_type, content, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        [self._message_to_tuple(m) for m in messages]
                    )
        
        self._batch = []
```

### 1.4 Tasks

1. **Implement OTLP receiver**
   - HTTP endpoint (JSON + Protobuf)
   - gRPC endpoint
   - Health check endpoint

2. **Implement normalizers**
   - LangGraph normalizer (priority)
   - AutoGen normalizer
   - CrewAI normalizer
   - Generic fallback normalizer

3. **Implement database writer**
   - Connection pooling
   - Batch writes
   - Retry logic with exponential backoff

4. **Write database migrations**
   - All tables from data model
   - Indexes
   - TimescaleDB hypertable setup

5. **Integration tests**
   - End-to-end: send OTLP → verify in database
   - Test each normalizer with sample traces

### Deliverables
- [ ] Ingestion service accepting OTLP over HTTP and gRPC
- [ ] LangGraph, AutoGen, CrewAI normalizers
- [ ] Database schema deployed via migrations
- [ ] Integration test suite passing
- [ ] Basic health metrics exposed

---

## Phase 2: Analysis Engine & Graph Construction (Weeks 4-5)

### Objectives
- Build agent communication graph from traces
- Implement failure classification (rule-based)
- Aggregate metrics per agent

### 2.1 Graph Construction

```python
# packages/analysis/agenttrace_analysis/graph.py

from dataclasses import dataclass
from typing import Iterator
import networkx as nx
from agenttrace_core.models import Trace, Span, Agent, AgentMessage

@dataclass
class AgentNode:
    agent_id: str
    name: str
    role: str
    model: str
    
    # Metrics
    span_count: int
    total_tokens: int
    total_cost_usd: float
    error_count: int
    avg_latency_ms: float

@dataclass
class CommunicationEdge:
    from_agent: str
    to_agent: str
    message_count: int
    message_types: list[str]
    total_tokens_transferred: int
    avg_latency_ms: float

class AgentGraph:
    """
    Represents the communication topology of agents in a trace.
    
    Unlike a call tree (parent-child), this captures:
    - Lateral communication between peer agents
    - Broadcast messages
    - Handoff patterns
    - Resource contention
    """
    
    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self._graph = nx.DiGraph()
    
    @classmethod
    async def from_trace(cls, trace_id: str, db) -> "AgentGraph":
        """Build graph from stored trace data."""
        graph = cls(trace_id)
        
        # Load agents
        agents = await db.fetch(
            """
            SELECT 
                agent_id, name, role, model,
                total_spans, total_tokens, total_cost_usd, error_count
            FROM agents
            WHERE trace_id = $1
            """,
            trace_id
        )
        
        for agent in agents:
            graph.add_agent(AgentNode(
                agent_id=agent["agent_id"],
                name=agent["name"],
                role=agent["role"],
                model=agent["model"],
                span_count=agent["total_spans"],
                total_tokens=agent["total_tokens"],
                total_cost_usd=float(agent["total_cost_usd"] or 0),
                error_count=agent["error_count"],
                avg_latency_ms=0,  # Compute separately
            ))
        
        # Load messages and build edges
        messages = await db.fetch(
            """
            SELECT 
                from_agent_id, to_agent_id, message_type,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (
                    SELECT MIN(s2.start_time) - m.timestamp
                    FROM spans s2 
                    WHERE s2.agent_id = m.to_agent_id 
                    AND s2.start_time > m.timestamp
                )) * 1000) as avg_latency_ms
            FROM agent_messages m
            WHERE trace_id = $1 AND from_agent_id IS NOT NULL AND to_agent_id IS NOT NULL
            GROUP BY from_agent_id, to_agent_id, message_type
            """,
            trace_id
        )
        
        # Aggregate edges
        edge_data: dict[tuple, CommunicationEdge] = {}
        for msg in messages:
            key = (msg["from_agent_id"], msg["to_agent_id"])
            if key not in edge_data:
                edge_data[key] = CommunicationEdge(
                    from_agent=msg["from_agent_id"],
                    to_agent=msg["to_agent_id"],
                    message_count=0,
                    message_types=[],
                    total_tokens_transferred=0,
                    avg_latency_ms=0,
                )
            edge_data[key].message_count += msg["count"]
            edge_data[key].message_types.append(msg["message_type"])
        
        for edge in edge_data.values():
            graph.add_edge(edge)
        
        return graph
    
    def add_agent(self, agent: AgentNode):
        self._graph.add_node(agent.agent_id, data=agent)
    
    def add_edge(self, edge: CommunicationEdge):
        self._graph.add_edge(
            edge.from_agent, 
            edge.to_agent, 
            data=edge
        )
    
    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "trace_id": self.trace_id,
            "nodes": [
                {
                    "id": node_id,
                    **self._graph.nodes[node_id]["data"].__dict__
                }
                for node_id in self._graph.nodes
            ],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    **self._graph.edges[u, v]["data"].__dict__
                }
                for u, v in self._graph.edges
            ],
            "metrics": {
                "node_count": self._graph.number_of_nodes(),
                "edge_count": self._graph.number_of_edges(),
                "density": nx.density(self._graph),
                "has_cycles": not nx.is_directed_acyclic_graph(self._graph),
            }
        }
    
    def find_bottlenecks(self) -> list[str]:
        """Identify agents that are potential bottlenecks."""
        bottlenecks = []
        
        # High in-degree = many agents depend on this one
        in_degrees = dict(self._graph.in_degree())
        avg_in = sum(in_degrees.values()) / len(in_degrees) if in_degrees else 0
        
        for node_id, in_deg in in_degrees.items():
            if in_deg > avg_in * 2:
                bottlenecks.append(node_id)
        
        return bottlenecks
    
    def find_isolated_agents(self) -> list[str]:
        """Find agents with no communication."""
        return [n for n in self._graph.nodes if self._graph.degree(n) == 0]
```

### 2.2 Failure Classification (Rule-Based)

```python
# packages/analysis/agenttrace_analysis/mast/rules.py

from dataclasses import dataclass
from enum import Enum
from typing import Callable
from agenttrace_core.models import Trace, Span, Agent

class FailureCategory(Enum):
    SPECIFICATION = "specification"
    COORDINATION = "coordination"
    VERIFICATION = "verification"

@dataclass
class FailureMode:
    category: FailureCategory
    name: str
    description: str

# MAST taxonomy failure modes
FAILURE_MODES = {
    # Specification failures (41.77% of failures)
    "role_ambiguity": FailureMode(
        FailureCategory.SPECIFICATION,
        "role_ambiguity",
        "Agent role or responsibilities unclear, leading to task confusion"
    ),
    "incomplete_spec": FailureMode(
        FailureCategory.SPECIFICATION,
        "incomplete_spec",
        "Task specification missing required details"
    ),
    "conflicting_instructions": FailureMode(
        FailureCategory.SPECIFICATION,
        "conflicting_instructions",
        "Multiple agents received contradictory instructions"
    ),
    
    # Coordination failures (36.94% of failures)
    "handoff_failure": FailureMode(
        FailureCategory.COORDINATION,
        "handoff_failure",
        "Information lost or corrupted during agent handoff"
    ),
    "resource_contention": FailureMode(
        FailureCategory.COORDINATION,
        "resource_contention",
        "Multiple agents competed for shared resource"
    ),
    "deadlock": FailureMode(
        FailureCategory.COORDINATION,
        "deadlock",
        "Agents waiting on each other indefinitely"
    ),
    "infinite_loop": FailureMode(
        FailureCategory.COORDINATION,
        "infinite_loop",
        "Agent repeatedly performing same action without progress"
    ),
    
    # Verification failures (16.29% of failures)
    "output_validation": FailureMode(
        FailureCategory.VERIFICATION,
        "output_validation",
        "Agent output failed validation checks"
    ),
    "hallucination": FailureMode(
        FailureCategory.VERIFICATION,
        "hallucination",
        "Agent produced factually incorrect information"
    ),
    "format_error": FailureMode(
        FailureCategory.VERIFICATION,
        "format_error",
        "Output format doesn't match expected schema"
    ),
}

@dataclass
class ClassificationResult:
    failure_mode: str
    category: FailureCategory
    confidence: float
    reasoning: str
    span_id: str | None
    agent_id: str | None

class RuleBasedClassifier:
    """
    Rule-based failure classifier.
    
    Applies heuristic rules to identify common failure patterns.
    For V1, this is deterministic and fast. V2 will add LLM-as-judge.
    """
    
    def __init__(self):
        self.rules: list[Callable] = [
            self._check_infinite_loop,
            self._check_handoff_failure,
            self._check_resource_contention,
            self._check_format_error,
            self._check_timeout_pattern,
        ]
    
    async def classify(self, trace: Trace, spans: list[Span], agents: list[Agent]) -> list[ClassificationResult]:
        """Run all classification rules and return findings."""
        results = []
        
        for rule in self.rules:
            findings = await rule(trace, spans, agents)
            results.extend(findings)
        
        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)
        
        return results
    
    async def _check_infinite_loop(
        self, trace: Trace, spans: list[Span], agents: list[Agent]
    ) -> list[ClassificationResult]:
        """
        Detect infinite loops by looking for:
        - Same agent called >N times with similar inputs
        - Cyclic handoff patterns (A→B→A→B...)
        """
        results = []
        
        # Group spans by agent
        spans_by_agent: dict[str, list[Span]] = {}
        for span in spans:
            if span.agent_id:
                spans_by_agent.setdefault(span.agent_id, []).append(span)
        
        for agent_id, agent_spans in spans_by_agent.items():
            # Check for repeated similar inputs
            input_hashes = [hash(str(s.input)) for s in agent_spans if s.input]
            
            if len(input_hashes) > 5:
                # Check for high repetition
                from collections import Counter
                counts = Counter(input_hashes)
                max_count = max(counts.values())
                
                if max_count > 3:
                    results.append(ClassificationResult(
                        failure_mode="infinite_loop",
                        category=FailureCategory.COORDINATION,
                        confidence=min(0.9, 0.5 + (max_count - 3) * 0.1),
                        reasoning=f"Agent called {max_count} times with identical/similar input",
                        span_id=agent_spans[-1].span_id,
                        agent_id=agent_id,
                    ))
        
        return results
    
    async def _check_handoff_failure(
        self, trace: Trace, spans: list[Span], agents: list[Agent]
    ) -> list[ClassificationResult]:
        """
        Detect handoff failures:
        - Agent B errors immediately after receiving from A
        - Required context missing in handoff message
        """
        results = []
        
        # Find handoff spans followed by errors
        handoff_spans = [s for s in spans if s.kind == "handoff"]
        
        for handoff in handoff_spans:
            # Find next span from target agent
            target_agent = handoff.attributes.get("message.to_agent")
            if not target_agent:
                continue
            
            subsequent = [
                s for s in spans 
                if s.agent_id == target_agent 
                and s.start_time > handoff.end_time
            ]
            
            if subsequent and subsequent[0].status == "error":
                results.append(ClassificationResult(
                    failure_mode="handoff_failure",
                    category=FailureCategory.COORDINATION,
                    confidence=0.75,
                    reasoning=f"Agent errored immediately after receiving handoff",
                    span_id=subsequent[0].span_id,
                    agent_id=target_agent,
                ))
        
        return results
    
    async def _check_resource_contention(
        self, trace: Trace, spans: list[Span], agents: list[Agent]
    ) -> list[ClassificationResult]:
        """
        Detect resource contention:
        - Multiple agents calling same tool simultaneously
        - Long waits on tool calls
        """
        results = []
        
        tool_spans = [s for s in spans if s.kind == "tool_call"]
        
        # Group by tool name
        by_tool: dict[str, list[Span]] = {}
        for span in tool_spans:
            tool_name = span.name
            by_tool.setdefault(tool_name, []).append(span)
        
        for tool_name, tool_uses in by_tool.items():
            # Check for overlapping time ranges
            for i, span_a in enumerate(tool_uses):
                for span_b in tool_uses[i+1:]:
                    if span_a.end_time > span_b.start_time and span_b.end_time > span_a.start_time:
                        # Overlapping!
                        results.append(ClassificationResult(
                            failure_mode="resource_contention",
                            category=FailureCategory.COORDINATION,
                            confidence=0.8,
                            reasoning=f"Multiple agents accessed {tool_name} simultaneously",
                            span_id=span_b.span_id,
                            agent_id=span_b.agent_id,
                        ))
        
        return results
    
    async def _check_format_error(
        self, trace: Trace, spans: list[Span], agents: list[Agent]
    ) -> list[ClassificationResult]:
        """Detect format/schema errors in outputs."""
        results = []
        
        for span in spans:
            if span.error:
                error_msg = str(span.error).lower()
                if any(kw in error_msg for kw in ["json", "parse", "schema", "format", "validation"]):
                    results.append(ClassificationResult(
                        failure_mode="format_error",
                        category=FailureCategory.VERIFICATION,
                        confidence=0.85,
                        reasoning=f"Output format error: {span.error.get('message', 'unknown')[:100]}",
                        span_id=span.span_id,
                        agent_id=span.agent_id,
                    ))
        
        return results
    
    async def _check_timeout_pattern(
        self, trace: Trace, spans: list[Span], agents: list[Agent]
    ) -> list[ClassificationResult]:
        """Detect timeout-related failures."""
        results = []
        
        for span in spans:
            if span.status == "timeout":
                results.append(ClassificationResult(
                    failure_mode="deadlock",  # Timeouts often indicate deadlock
                    category=FailureCategory.COORDINATION,
                    confidence=0.6,
                    reasoning="Span timed out - possible deadlock or resource starvation",
                    span_id=span.span_id,
                    agent_id=span.agent_id,
                ))
        
        return results
```

### 2.3 Tasks

1. **Implement graph construction**
   - `AgentGraph.from_trace()` builder
   - Node and edge metrics computation
   - Bottleneck detection
   - Cycle detection

2. **Implement rule-based classifier**
   - All rules in 2.2
   - Add tests with known failure patterns

3. **Create analysis API**
   ```
   GET  /api/traces/{trace_id}/graph
   GET  /api/traces/{trace_id}/failures
   POST /api/traces/{trace_id}/classify  (re-run classification)
   ```

4. **Background job for classification**
   - Automatically classify failed traces
   - Store results in `failure_annotations`

### Deliverables
- [ ] Graph construction from trace data
- [ ] 5+ rule-based failure classifiers
- [ ] Analysis API endpoints
- [ ] Background classification job
- [ ] Unit tests for each classifier

---

## Phase 3: Web UI - Trace Viewer & Graph Visualization (Weeks 6-8)

### Objectives
- Trace list with filtering and search
- Agent communication graph visualization (D3.js force-directed)
- Span detail panel
- Failure annotations display

### 3.1 Component Architecture

```
src/
├── components/
│   ├── Layout/
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   │
│   ├── TraceList/
│   │   ├── TraceList.tsx         # Main list component
│   │   ├── TraceRow.tsx          # Individual trace row
│   │   ├── TraceFilters.tsx      # Filter controls
│   │   └── TraceSearch.tsx       # Search input
│   │
│   ├── TraceDetail/
│   │   ├── TraceDetail.tsx       # Container for trace view
│   │   ├── TraceHeader.tsx       # Trace metadata, status
│   │   ├── TraceTabs.tsx         # Tab navigation
│   │   └── TraceMetrics.tsx      # Cost, latency, tokens
│   │
│   ├── AgentGraph/
│   │   ├── AgentGraph.tsx        # D3 force-directed graph
│   │   ├── AgentNode.tsx         # Node component
│   │   ├── AgentEdge.tsx         # Edge component
│   │   ├── GraphControls.tsx     # Zoom, layout controls
│   │   └── GraphLegend.tsx
│   │
│   ├── SpanTimeline/
│   │   ├── SpanTimeline.tsx      # Gantt-style timeline
│   │   ├── SpanBar.tsx           # Individual span bar
│   │   └── TimelineControls.tsx
│   │
│   ├── SpanDetail/
│   │   ├── SpanDetail.tsx        # Span info panel
│   │   ├── SpanInput.tsx         # Input viewer (JSON)
│   │   ├── SpanOutput.tsx        # Output viewer
│   │   └── SpanError.tsx         # Error display
│   │
│   ├── FailurePanel/
│   │   ├── FailurePanel.tsx      # Failure annotations
│   │   ├── FailureCard.tsx       # Individual failure
│   │   └── FailureFilter.tsx     # Filter by category
│   │
│   └── common/
│       ├── JsonViewer.tsx
│       ├── CopyButton.tsx
│       ├── StatusBadge.tsx
│       └── Tooltip.tsx
│
├── hooks/
│   ├── useTraces.ts              # Trace list fetching
│   ├── useTrace.ts               # Single trace fetching
│   ├── useGraph.ts               # Graph data
│   └── useWebSocket.ts           # Real-time updates
│
├── api/
│   ├── client.ts                 # API client setup
│   ├── traces.ts                 # Trace endpoints
│   └── analysis.ts               # Analysis endpoints
│
└── types/
    ├── trace.ts
    ├── span.ts
    ├── agent.ts
    └── failure.ts
```

### 3.2 Agent Graph Component

```tsx
// src/components/AgentGraph/AgentGraph.tsx

import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { AgentNode, CommunicationEdge } from '@/types/agent';

interface AgentGraphProps {
  nodes: AgentNode[];
  edges: CommunicationEdge[];
  onNodeClick?: (node: AgentNode) => void;
  onEdgeClick?: (edge: CommunicationEdge) => void;
  highlightedAgent?: string;
  failedAgents?: string[];
}

export const AgentGraph: React.FC<AgentGraphProps> = ({
  nodes,
  edges,
  onNodeClick,
  onEdgeClick,
  highlightedAgent,
  failedAgents = [],
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  
  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const { width, height } = dimensions;
    
    // Create container with zoom
    const container = svg
      .append('g')
      .attr('class', 'graph-container');
    
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });
    
    svg.call(zoom);
    
    // Create force simulation
    const simulation = d3.forceSimulation(nodes as d3.SimulationNodeDatum[])
      .force('link', d3.forceLink(edges)
        .id((d: any) => d.id)
        .distance(150)
      )
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(60));
    
    // Draw edges
    const edgeGroup = container.append('g').attr('class', 'edges');
    
    const edgeElements = edgeGroup
      .selectAll('g')
      .data(edges)
      .enter()
      .append('g')
      .attr('class', 'edge')
      .style('cursor', 'pointer')
      .on('click', (event, d) => onEdgeClick?.(d));
    
    // Edge lines with arrows
    edgeElements
      .append('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', (d) => Math.min(4, 1 + d.message_count / 2))
      .attr('marker-end', 'url(#arrowhead)');
    
    // Edge labels (message count)
    edgeElements
      .append('text')
      .attr('class', 'edge-label')
      .attr('text-anchor', 'middle')
      .attr('dy', -5)
      .attr('fill', '#64748b')
      .attr('font-size', '11px')
      .text((d) => d.message_count > 1 ? `×${d.message_count}` : '');
    
    // Draw nodes
    const nodeGroup = container.append('g').attr('class', 'nodes');
    
    const nodeElements = nodeGroup
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .on('click', (event, d) => onNodeClick?.(d))
      .call(d3.drag<SVGGElement, AgentNode>()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded)
      );
    
    // Node circles
    nodeElements
      .append('circle')
      .attr('r', (d) => 30 + Math.log(d.span_count + 1) * 5)
      .attr('fill', (d) => {
        if (failedAgents.includes(d.id)) return '#ef4444';
        if (d.id === highlightedAgent) return '#3b82f6';
        return getColorForRole(d.role);
      })
      .attr('stroke', '#1e293b')
      .attr('stroke-width', 2);
    
    // Node labels
    nodeElements
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 4)
      .attr('fill', 'white')
      .attr('font-weight', 'bold')
      .attr('font-size', '12px')
      .text((d) => d.name.slice(0, 12));
    
    // Role subtitle
    nodeElements
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 50)
      .attr('fill', '#64748b')
      .attr('font-size', '10px')
      .text((d) => d.role);
    
    // Arrow marker definition
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 35)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .append('path')
      .attr('d', 'M 0,-5 L 10,0 L 0,5')
      .attr('fill', '#94a3b8');
    
    // Update positions on tick
    simulation.on('tick', () => {
      edgeElements.select('line')
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);
      
      edgeElements.select('text')
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);
      
      nodeElements.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });
    
    function dragStarted(event: d3.D3DragEvent<SVGGElement, AgentNode, AgentNode>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }
    
    function dragged(event: d3.D3DragEvent<SVGGElement, AgentNode, AgentNode>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }
    
    function dragEnded(event: d3.D3DragEvent<SVGGElement, AgentNode, AgentNode>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }
    
    return () => {
      simulation.stop();
    };
  }, [nodes, edges, dimensions, highlightedAgent, failedAgents]);
  
  return (
    <div className="agent-graph-container w-full h-full bg-slate-900 rounded-lg">
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
      />
    </div>
  );
};

function getColorForRole(role: string): string {
  const colors: Record<string, string> = {
    planner: '#8b5cf6',
    executor: '#10b981',
    reviewer: '#f59e0b',
    coder: '#3b82f6',
    researcher: '#ec4899',
    default: '#6b7280',
  };
  return colors[role.toLowerCase()] || colors.default;
}
```

### 3.3 Tasks

1. **Set up React project**
   - Vite + React + TypeScript
   - Tailwind CSS
   - React Query for data fetching

2. **Implement Trace List**
   - Paginated list with virtual scrolling
   - Filters: status, date range, agent count
   - Search by trace name/ID

3. **Implement Agent Graph**
   - D3.js force-directed layout
   - Node sizing by span count
   - Edge thickness by message count
   - Color coding for failures
   - Zoom and pan

4. **Implement Span Timeline**
   - Gantt-style visualization
   - Color by agent
   - Click to select span

5. **Implement Span Detail Panel**
   - JSON viewer for input/output
   - Error display
   - Token/cost metrics

6. **Implement Failure Panel**
   - List failure annotations
   - Filter by category
   - Click to highlight span/agent

### Deliverables
- [ ] Trace list with search and filters
- [ ] Interactive agent graph visualization
- [ ] Span timeline view
- [ ] Span detail panel
- [ ] Failure annotations display
- [ ] Responsive design

---

## Phase 4: Replay Engine (Weeks 9-11)

### Objectives
- Checkpoint creation and storage
- State restoration
- Re-execution from checkpoint
- Diff visualization

### 4.1 Checkpoint Manager

```python
# packages/replay/agenttrace_replay/checkpoint.py

import pickle
import hashlib
from datetime import datetime
from typing import Any, TypeVar, Generic
from dataclasses import dataclass
import asyncpg

T = TypeVar('T')

@dataclass
class Checkpoint(Generic[T]):
    checkpoint_id: str
    trace_id: str
    span_id: str
    agent_id: str
    name: str
    state: T
    timestamp: datetime
    state_hash: str
    
    @classmethod
    def create(
        cls,
        trace_id: str,
        span_id: str,
        agent_id: str,
        name: str,
        state: T,
    ) -> "Checkpoint[T]":
        state_bytes = pickle.dumps(state)
        state_hash = hashlib.sha256(state_bytes).hexdigest()[:16]
        
        return cls(
            checkpoint_id=f"{trace_id}:{span_id}:{state_hash}",
            trace_id=trace_id,
            span_id=span_id,
            agent_id=agent_id,
            name=name,
            state=state,
            timestamp=datetime.utcnow(),
            state_hash=state_hash,
        )

class CheckpointManager:
    """
    Manages checkpoints for replay debugging.
    
    Checkpoints capture agent state at specific points in execution,
    allowing developers to:
    - Replay from a specific point
    - Modify inputs and re-run
    - Compare outputs across replays
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def save(self, checkpoint: Checkpoint) -> str:
        """Save checkpoint to database."""
        state_bytes = pickle.dumps(checkpoint.state)
        
        await self.db.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, trace_id, span_id, agent_id,
                name, state, timestamp
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (checkpoint_id) DO NOTHING
            """,
            checkpoint.checkpoint_id,
            checkpoint.trace_id,
            checkpoint.span_id,
            checkpoint.agent_id,
            checkpoint.name,
            state_bytes,
            checkpoint.timestamp,
        )
        
        return checkpoint.checkpoint_id
    
    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        """Load checkpoint from database."""
        row = await self.db.fetchrow(
            """
            SELECT * FROM checkpoints WHERE checkpoint_id = $1
            """,
            checkpoint_id,
        )
        
        if not row:
            return None
        
        state = pickle.loads(row["state"])
        
        return Checkpoint(
            checkpoint_id=row["checkpoint_id"],
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            agent_id=row["agent_id"],
            name=row["name"],
            state=state,
            timestamp=row["timestamp"],
            state_hash=hashlib.sha256(row["state"]).hexdigest()[:16],
        )
    
    async def list_for_trace(self, trace_id: str) -> list[dict]:
        """List all checkpoints for a trace."""
        rows = await self.db.fetch(
            """
            SELECT 
                c.checkpoint_id, c.name, c.timestamp, c.span_id, c.agent_id,
                a.name as agent_name,
                s.name as span_name
            FROM checkpoints c
            JOIN agents a ON c.agent_id = a.agent_id
            JOIN spans s ON c.span_id = s.span_id
            WHERE c.trace_id = $1
            ORDER BY c.timestamp
            """,
            trace_id,
        )
        
        return [dict(row) for row in rows]
    
    async def auto_checkpoint_trace(self, trace_id: str):
        """
        Automatically create checkpoints for a trace.
        
        Creates checkpoints at:
        - Agent handoffs
        - Before tool calls
        - After LLM calls with significant state changes
        """
        spans = await self.db.fetch(
            """
            SELECT * FROM spans
            WHERE trace_id = $1 AND kind IN ('handoff', 'tool_call', 'llm_call')
            ORDER BY start_time
            """,
            trace_id,
        )
        
        for span in spans:
            # Build state from span input + prior context
            state = {
                "input": span["input"],
                "prior_output": await self._get_prior_output(trace_id, span["span_id"]),
                "agent_config": await self._get_agent_config(span["agent_id"]),
            }
            
            checkpoint = Checkpoint.create(
                trace_id=trace_id,
                span_id=span["span_id"],
                agent_id=span["agent_id"],
                name=f"auto:{span['kind']}:{span['name']}",
                state=state,
            )
            
            await self.save(checkpoint)
```

### 4.2 Replay Executor

```python
# packages/replay/agenttrace_replay/executor.py

from dataclasses import dataclass
from typing import Any, Callable
from datetime import datetime
import asyncio

from agenttrace_core.models import Span
from .checkpoint import Checkpoint, CheckpointManager

@dataclass
class ReplayResult:
    replay_id: str
    checkpoint_id: str
    original_output: Any
    replay_output: Any
    diff: dict
    success: bool
    error: str | None
    duration_ms: int

@dataclass
class ReplayConfig:
    # Modified inputs for this replay
    modified_input: dict | None = None
    
    # Override agent configuration
    agent_overrides: dict | None = None
    
    # Stop at specific span (for partial replay)
    stop_at_span: str | None = None
    
    # Timeout
    timeout_seconds: int = 300

class ReplayExecutor:
    """
    Executes replays from checkpoints.
    
    This is the most complex component because it needs to:
    1. Restore agent state from checkpoint
    2. Re-execute with potentially modified inputs
    3. Capture new outputs
    4. Compare against original
    """
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        agent_registry: dict[str, Callable],  # Framework-specific executors
    ):
        self.checkpoints = checkpoint_manager
        self.agent_registry = agent_registry
    
    async def replay(
        self,
        checkpoint_id: str,
        config: ReplayConfig | None = None,
    ) -> ReplayResult:
        """
        Replay execution from a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to replay from
            config: Optional configuration for modified replay
        
        Returns:
            ReplayResult with comparison to original
        """
        config = config or ReplayConfig()
        
        # Load checkpoint
        checkpoint = await self.checkpoints.load(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        # Get original span for comparison
        original_span = await self._get_original_span(checkpoint.span_id)
        
        # Prepare input (with modifications if any)
        replay_input = config.modified_input or checkpoint.state.get("input", {})
        
        # Get executor for this agent's framework
        agent_config = checkpoint.state.get("agent_config", {})
        framework = agent_config.get("framework", "generic")
        executor = self.agent_registry.get(framework)
        
        if not executor:
            raise ValueError(f"No executor registered for framework: {framework}")
        
        # Execute with timeout
        start_time = datetime.utcnow()
        try:
            replay_output = await asyncio.wait_for(
                executor(
                    input=replay_input,
                    state=checkpoint.state,
                    config=agent_config,
                    overrides=config.agent_overrides,
                ),
                timeout=config.timeout_seconds,
            )
            success = True
            error = None
        except asyncio.TimeoutError:
            replay_output = None
            success = False
            error = "Replay timed out"
        except Exception as e:
            replay_output = None
            success = False
            error = str(e)
        
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Compute diff
        diff = self._compute_diff(original_span.output, replay_output)
        
        # Generate replay ID and store result
        replay_id = f"replay:{checkpoint_id}:{start_time.timestamp()}"
        
        result = ReplayResult(
            replay_id=replay_id,
            checkpoint_id=checkpoint_id,
            original_output=original_span.output,
            replay_output=replay_output,
            diff=diff,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        
        # Store replay for history
        await self._store_replay(result)
        
        return result
    
    def _compute_diff(self, original: Any, replay: Any) -> dict:
        """Compute structured diff between original and replay outputs."""
        from deepdiff import DeepDiff
        
        diff = DeepDiff(original, replay, ignore_order=True)
        
        return {
            "has_changes": bool(diff),
            "added": diff.get("dictionary_item_added", []),
            "removed": diff.get("dictionary_item_removed", []),
            "changed": diff.get("values_changed", {}),
            "type_changes": diff.get("type_changes", {}),
        }
```

### 4.3 Framework-Specific Executors

```python
# packages/replay/agenttrace_replay/executors/langgraph.py

from typing import Any

async def langgraph_executor(
    input: dict,
    state: dict,
    config: dict,
    overrides: dict | None = None,
) -> Any:
    """
    Re-execute a LangGraph node.
    
    This requires reconstructing the graph state and invoking
    the specific node that was checkpointed.
    """
    from langgraph.graph import StateGraph
    
    # Reconstruct graph from config
    graph_config = config.get("graph_config", {})
    node_name = config.get("node_name")
    
    # Apply overrides
    if overrides:
        if "model" in overrides:
            graph_config["model"] = overrides["model"]
        if "temperature" in overrides:
            graph_config["temperature"] = overrides["temperature"]
    
    # This is a simplified example - real implementation would need
    # to handle graph reconstruction properly
    
    # For now, we'll assume we can invoke the node directly
    # In practice, you'd need to serialize/deserialize the graph
    
    # Invoke the node with restored state
    result = await invoke_node(
        node_name=node_name,
        input=input,
        state=state.get("prior_output", {}),
        config=graph_config,
    )
    
    return result
```

### 4.4 Tasks

1. **Implement CheckpointManager**
   - Save/load checkpoints
   - Auto-checkpoint logic
   - Checkpoint listing

2. **Implement ReplayExecutor**
   - Basic replay flow
   - Diff computation
   - Replay storage

3. **Implement framework executors**
   - LangGraph executor (priority)
   - Generic executor (fallback)

4. **Create Replay API**
   ```
   GET  /api/traces/{trace_id}/checkpoints
   POST /api/checkpoints/{checkpoint_id}/replay
   GET  /api/replays/{replay_id}
   GET  /api/replays/{replay_id}/diff
   ```

5. **Add Replay UI**
   - Checkpoint list in trace view
   - "Replay from here" button
   - Input modification form
   - Diff visualization

### Deliverables
- [ ] Checkpoint creation and storage
- [ ] Replay execution with diff
- [ ] LangGraph executor
- [ ] Replay API endpoints
- [ ] Replay UI in web interface

---

## Phase 5: SDK & Integrations (Weeks 12-14)

### Objectives
- Python SDK for manual instrumentation
- Auto-instrumentation for LangGraph
- Documentation and examples

### 5.1 Python SDK

```python
# packages/sdk/python/agenttrace/tracer.py

from contextlib import contextmanager
from typing import Any, Callable
from datetime import datetime
import functools
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

class AgentTracer:
    """
    Main entry point for AgentTrace instrumentation.
    
    Usage:
        tracer = AgentTracer(endpoint="http://localhost:4317")
        
        @tracer.agent("Planner", role="planner", model="claude-3-opus")
        async def plan(task: str) -> str:
            ...
        
        @tracer.tool("search")
        async def search(query: str) -> list[str]:
            ...
    """
    
    def __init__(
        self,
        endpoint: str = "http://localhost:4317",
        service_name: str = "agenttrace-app",
        framework: str = "custom",
    ):
        self.endpoint = endpoint
        self.service_name = service_name
        self.framework = framework
        
        # Set up OpenTelemetry
        self._setup_otel()
        
        self._tracer = trace.get_tracer(__name__)
        self._current_trace_id: str | None = None
    
    def _setup_otel(self):
        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    
    @contextmanager
    def trace(self, name: str, metadata: dict | None = None):
        """Start a new trace (top-level execution)."""
        with self._tracer.start_as_current_span(name) as span:
            self._current_trace_id = format(span.get_span_context().trace_id, '032x')
            
            span.set_attribute("agenttrace.framework", self.framework)
            if metadata:
                for k, v in metadata.items():
                    span.set_attribute(f"agenttrace.metadata.{k}", str(v))
            
            try:
                yield span
            finally:
                self._current_trace_id = None
    
    def agent(
        self,
        name: str,
        role: str = "unknown",
        model: str | None = None,
    ):
        """Decorator to mark a function as an agent."""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with self._tracer.start_as_current_span(f"agent:{name}") as span:
                    span.set_attribute("agent.name", name)
                    span.set_attribute("agent.role", role)
                    span.set_attribute("agent.framework", self.framework)
                    if model:
                        span.set_attribute("agent.model", model)
                    
                    # Capture input
                    span.set_attribute("agenttrace.input", _serialize(kwargs or args))
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("agenttrace.output", _serialize(result))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise
            
            return wrapper
        return decorator
    
    def tool(self, name: str):
        """Decorator to mark a function as a tool."""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with self._tracer.start_as_current_span(f"tool:{name}") as span:
                    span.set_attribute("tool.name", name)
                    span.set_attribute("agenttrace.kind", "tool_call")
                    span.set_attribute("agenttrace.input", _serialize(kwargs or args))
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("agenttrace.output", _serialize(result))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise
            
            return wrapper
        return decorator
    
    def message(
        self,
        from_agent: str,
        to_agent: str,
        content: Any,
        message_type: str = "request",
    ):
        """Record an inter-agent message."""
        span = trace.get_current_span()
        
        # Add as span event
        span.add_event(
            "agent_message",
            attributes={
                "message.from_agent": from_agent,
                "message.to_agent": to_agent,
                "message.type": message_type,
                "message.content": _serialize(content),
            }
        )
    
    def checkpoint(self, name: str, state: Any):
        """Create a checkpoint at current position."""
        span = trace.get_current_span()
        
        span.add_event(
            "checkpoint",
            attributes={
                "checkpoint.name": name,
                "checkpoint.state": _serialize(state),
                "checkpoint.restorable": True,
            }
        )
```

### 5.2 LangGraph Auto-Instrumentation

```python
# packages/sdk/python/agenttrace/integrations/langgraph.py

from typing import Any
from functools import wraps
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from opentelemetry import trace

def instrument_langgraph():
    """
    Auto-instrument LangGraph to emit AgentTrace-compatible spans.
    
    Call this once at application startup:
        from agenttrace.integrations.langgraph import instrument_langgraph
        instrument_langgraph()
    """
    _patch_state_graph()
    _patch_compiled_graph()

def _patch_state_graph():
    """Patch StateGraph to capture node definitions."""
    original_add_node = StateGraph.add_node
    
    @wraps(original_add_node)
    def patched_add_node(self, name: str, action: Any, *args, **kwargs):
        # Wrap the action to emit spans
        wrapped_action = _wrap_node_action(name, action)
        return original_add_node(self, name, wrapped_action, *args, **kwargs)
    
    StateGraph.add_node = patched_add_node

def _patch_compiled_graph():
    """Patch CompiledGraph.invoke to create trace spans."""
    original_invoke = CompiledGraph.invoke
    original_ainvoke = CompiledGraph.ainvoke
    
    @wraps(original_invoke)
    def patched_invoke(self, input: Any, config: dict | None = None, **kwargs):
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("langgraph.invoke") as span:
            span.set_attribute("agent.framework", "langgraph")
            span.set_attribute("agenttrace.input", _serialize(input))
            
            try:
                result = original_invoke(self, input, config, **kwargs)
                span.set_attribute("agenttrace.output", _serialize(result))
                return result
            except Exception as e:
                span.record_exception(e)
                raise
    
    @wraps(original_ainvoke)
    async def patched_ainvoke(self, input: Any, config: dict | None = None, **kwargs):
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("langgraph.ainvoke") as span:
            span.set_attribute("agent.framework", "langgraph")
            span.set_attribute("agenttrace.input", _serialize(input))
            
            try:
                result = await original_ainvoke(self, input, config, **kwargs)
                span.set_attribute("agenttrace.output", _serialize(result))
                return result
            except Exception as e:
                span.record_exception(e)
                raise
    
    CompiledGraph.invoke = patched_invoke
    CompiledGraph.ainvoke = patched_ainvoke

def _wrap_node_action(node_name: str, action: Any):
    """Wrap a node action to emit spans."""
    tracer = trace.get_tracer(__name__)
    
    if asyncio.iscoroutinefunction(action):
        @wraps(action)
        async def wrapped(*args, **kwargs):
            with tracer.start_as_current_span(f"langgraph.node:{node_name}") as span:
                span.set_attribute("langgraph.node", node_name)
                span.set_attribute("agent.name", node_name)
                span.set_attribute("agenttrace.kind", "agent_message")
                
                # Try to extract state from args
                if args:
                    span.set_attribute("agenttrace.input", _serialize(args[0]))
                
                result = await action(*args, **kwargs)
                
                span.set_attribute("agenttrace.output", _serialize(result))
                return result
        return wrapped
    else:
        @wraps(action)
        def wrapped(*args, **kwargs):
            with tracer.start_as_current_span(f"langgraph.node:{node_name}") as span:
                span.set_attribute("langgraph.node", node_name)
                span.set_attribute("agent.name", node_name)
                span.set_attribute("agenttrace.kind", "agent_message")
                
                if args:
                    span.set_attribute("agenttrace.input", _serialize(args[0]))
                
                result = action(*args, **kwargs)
                
                span.set_attribute("agenttrace.output", _serialize(result))
                return result
        return wrapped
```

### 5.3 Tasks

1. **Implement core SDK**
   - `AgentTracer` class
   - Decorators: `@agent`, `@tool`
   - `message()` and `checkpoint()` methods

2. **Implement LangGraph integration**
   - Auto-instrumentation
   - State capture

3. **Implement AutoGen integration**
   - Conversation tracing
   - Agent identification

4. **Write documentation**
   - Getting started guide
   - SDK reference
   - Integration guides

5. **Create examples**
   - LangGraph example app
   - AutoGen example app
   - Custom agent example

### Deliverables
- [ ] Python SDK published to PyPI
- [ ] LangGraph auto-instrumentation
- [ ] AutoGen auto-instrumentation
- [ ] Documentation site
- [ ] Example applications

---

## 7. Testing Strategy

### 7.1 Unit Tests

Each package has its own test suite:

```bash
# Run all tests
make test

# Run specific package tests
uv run pytest packages/core/tests
uv run pytest packages/ingestion/tests
uv run pytest packages/analysis/tests
```

### 7.2 Integration Tests

```python
# tests/integration/test_e2e.py

import pytest
from agenttrace import AgentTracer
from agenttrace.integrations.langgraph import instrument_langgraph

@pytest.fixture
def tracer():
    return AgentTracer(endpoint="http://localhost:4317")

@pytest.fixture
def sample_langgraph_app():
    """Create a simple LangGraph app for testing."""
    from langgraph.graph import StateGraph
    
    def planner(state):
        return {"plan": "test plan"}
    
    def executor(state):
        return {"result": "test result"}
    
    graph = StateGraph()
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_edge("planner", "executor")
    
    return graph.compile()

async def test_langgraph_trace_captured(tracer, sample_langgraph_app):
    """Verify that LangGraph execution produces traces."""
    instrument_langgraph()
    
    with tracer.trace("test-trace"):
        result = await sample_langgraph_app.ainvoke({"input": "test"})
    
    # Verify trace was stored
    # (would query the database here)
    assert result["result"] == "test result"

async def test_failure_classification(tracer):
    """Verify that failures are correctly classified."""
    # Create a trace with known failure pattern
    # Verify classifier identifies it correctly
    pass
```

### 7.3 Load Tests

```python
# tests/load/test_ingestion_throughput.py

import asyncio
from locust import HttpUser, task, between

class TraceIngestionUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def send_trace(self):
        # Generate sample OTLP payload
        payload = generate_otlp_payload(num_spans=50)
        
        self.client.post(
            "/v1/traces",
            data=payload,
            headers={"Content-Type": "application/x-protobuf"},
        )
```

---

## 8. Deployment

### 8.1 Docker Compose (Development/Small Scale)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: agenttrace
      POSTGRES_USER: agenttrace
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  ingestion:
    image: agenttrace/ingestion:latest
    environment:
      DATABASE_URL: postgresql://agenttrace:${POSTGRES_PASSWORD}@postgres:5432/agenttrace
    ports:
      - "4317:4317"
      - "4318:4318"
    depends_on:
      - postgres

  analysis:
    image: agenttrace/analysis:latest
    environment:
      DATABASE_URL: postgresql://agenttrace:${POSTGRES_PASSWORD}@postgres:5432/agenttrace
    depends_on:
      - postgres

  web:
    image: agenttrace/web:latest
    environment:
      API_URL: http://analysis:8000
    ports:
      - "3000:3000"
    depends_on:
      - analysis

volumes:
  pgdata:
```

### 8.2 Kubernetes (Production)

```yaml
# deploy/kubernetes/ingestion-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenttrace-ingestion
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenttrace-ingestion
  template:
    metadata:
      labels:
        app: agenttrace-ingestion
    spec:
      containers:
        - name: ingestion
          image: agenttrace/ingestion:latest
          ports:
            - containerPort: 4317
            - containerPort: 4318
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: agenttrace-secrets
                  key: database-url
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

---

## 9. Success Metrics

| Metric | Target (V1) |
|--------|-------------|
| Trace ingestion latency (p99) | < 100ms |
| Graph construction time | < 500ms for 100 agents |
| Failure classification accuracy | > 70% (vs. manual annotation) |
| Replay success rate | > 90% |
| UI load time | < 2s |

---

## 10. Future Considerations (V2+)

1. **LLM-as-Judge classifier** - Use Claude/GPT to classify ambiguous failures
2. **Real-time streaming** - WebSocket updates for live traces
3. **Collaborative annotations** - Team-based failure labeling
4. **Cost optimization suggestions** - Identify expensive agent patterns
5. **A/B testing for prompts** - Compare agent configurations
6. **TypeScript SDK** - For Node.js agent frameworks

---

## Appendix A: References

- [MAST: Multi-Agent System Failure Taxonomy](https://arxiv.org/abs/2503.13657)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Langfuse Architecture](https://langfuse.com/docs/architecture)

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Trace** | A complete execution from user input to final output |
| **Span** | A single operation within a trace (LLM call, tool use, etc.) |
| **Agent** | An LLM-powered entity with a specific role |
| **Checkpoint** | A saved state that can be restored for replay |
| **MAST** | Multi-Agent System Failure Taxonomy |
| **Handoff** | Transfer of control/context from one agent to another |
