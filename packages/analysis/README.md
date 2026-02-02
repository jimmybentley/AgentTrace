# AgentTrace Analysis Engine

Graph construction, failure classification, and analysis API for multi-agent system traces.

## Overview

The analysis engine processes stored traces to build agent communication graphs, classify failures using the MAST taxonomy, and expose a REST API for querying trace data and metrics.

## Features

- **Agent Communication Graphs** - Constructs directed graphs showing agent interactions
- **MAST Taxonomy Classification** - Rule-based failure categorization
- **REST API** - 8+ endpoints for trace querying and analysis
- **Metrics Aggregation** - Trace statistics, agent performance, failure rates
- **Graph Algorithms** - Path finding, cycle detection, centrality analysis
- **Real-time Analysis** - On-demand graph and failure analysis

## Installation

```bash
pip install agenttrace-analysis
```

Or as part of the monorepo:

```bash
uv sync --package agenttrace-analysis
```

## Quick Start

The analysis engine is typically started as part of the main API server:

```bash
make run-api
# or
uvicorn agenttrace_ingestion.server:app --port 8000
```

The analysis API is available at `http://localhost:8000/api/`.

## API Endpoints

### Trace Management

#### GET /api/traces

List all traces with pagination and filtering.

**Query Parameters:**
- `offset` (int): Pagination offset (default: 0)
- `limit` (int): Number of traces to return (default: 50, max: 100)
- `status` (str): Filter by status (ok, error)
- `service_name` (str): Filter by service name
- `start_time_gte` (datetime): Filter by start time >= value
- `start_time_lte` (datetime): Filter by start time <= value

**Response:**
```json
{
  "traces": [
    {
      "trace_id": "trace-123",
      "name": "customer_support",
      "start_time": "2024-01-01T00:00:00Z",
      "end_time": "2024-01-01T00:00:10Z",
      "service_name": "support-bot",
      "status": "ok",
      "span_count": 15,
      "metadata": {"user_id": "user-456"}
    }
  ],
  "total": 100,
  "offset": 0,
  "limit": 50
}
```

#### GET /api/traces/{trace_id}

Get detailed information about a specific trace.

**Response:**
```json
{
  "trace_id": "trace-123",
  "name": "customer_support",
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-01T00:00:10Z",
  "service_name": "support-bot",
  "status": "ok",
  "span_count": 15,
  "spans": [...],
  "agents": [...],
  "metadata": {}
}
```

#### GET /api/traces/{trace_id}/spans

Get all spans for a trace with parent-child relationships.

**Response:**
```json
{
  "trace_id": "trace-123",
  "spans": [
    {
      "span_id": "span-456",
      "parent_span_id": null,
      "name": "planner_agent",
      "start_time": "2024-01-01T00:00:00Z",
      "end_time": "2024-01-01T00:00:05Z",
      "attributes": {...},
      "events": [],
      "status": "ok"
    }
  ]
}
```

### Agent Graph Analysis

#### GET /api/traces/{trace_id}/graph

Get the agent communication graph for a trace.

**Response:**
```json
{
  "trace_id": "trace-123",
  "nodes": [
    {
      "agent_id": "agent-1",
      "name": "Planner",
      "role": "planner",
      "framework": "langgraph",
      "execution_count": 3,
      "total_duration_ms": 5000
    }
  ],
  "edges": [
    {
      "from_agent": "Planner",
      "to_agent": "Executor",
      "message_count": 2,
      "message_types": ["handoff", "request"]
    }
  ]
}
```

#### GET /api/traces/{trace_id}/graph/paths

Find paths between agents in the communication graph.

**Query Parameters:**
- `from_agent` (str): Source agent name
- `to_agent` (str): Destination agent name

**Response:**
```json
{
  "paths": [
    ["Planner", "Executor", "Verifier"],
    ["Planner", "Validator", "Verifier"]
  ]
}
```

### Failure Analysis

#### GET /api/traces/{trace_id}/failures

Get all failure annotations for a trace.

**Query Parameters:**
- `category` (str): Filter by MAST category
- `severity` (str): Filter by severity (low, medium, high, critical)

**Response:**
```json
{
  "trace_id": "trace-123",
  "failures": [
    {
      "annotation_id": "ann-789",
      "span_id": "span-456",
      "category": "reasoning",
      "subcategory": "planning_error",
      "severity": "high",
      "description": "Agent failed to consider edge case",
      "detected_at": "2024-01-01T00:00:05Z"
    }
  ],
  "failure_count": 1
}
```

#### POST /api/traces/{trace_id}/analyze

Trigger failure analysis on a trace.

**Response:**
```json
{
  "trace_id": "trace-123",
  "failures_detected": 2,
  "categories": {
    "reasoning": 1,
    "communication": 1
  }
}
```

### Metrics

#### GET /api/metrics

Get aggregated metrics across all traces.

**Query Parameters:**
- `start_time` (datetime): Start of time range
- `end_time` (datetime): End of time range

**Response:**
```json
{
  "total_traces": 1000,
  "total_spans": 15000,
  "avg_trace_duration_ms": 5000,
  "success_rate": 0.95,
  "failure_rate": 0.05,
  "top_agents": [
    {"name": "Planner", "execution_count": 500},
    {"name": "Executor", "execution_count": 450}
  ],
  "failure_categories": {
    "reasoning": 30,
    "communication": 20
  }
}
```

## Agent Graph Construction

The analysis engine builds directed graphs from agent messages:

```python
from agenttrace_analysis import AgentGraph

# Create graph from trace
graph = AgentGraph.from_trace("trace-123", db_connection)

# Get nodes (agents)
nodes = graph.nodes
# [{"name": "Planner", "role": "planner", ...}]

# Get edges (messages)
edges = graph.edges
# [{"from": "Planner", "to": "Executor", "count": 2}]

# Find paths
paths = graph.find_paths("Planner", "Verifier")

# Detect cycles
cycles = graph.detect_cycles()

# Calculate centrality
centrality = graph.calculate_centrality()
```

## MAST Taxonomy Classification

The analysis engine uses rule-based classification to categorize failures:

```python
from agenttrace_analysis import RuleBasedClassifier

classifier = RuleBasedClassifier()

# Classify a span
annotation = classifier.classify_span(span)
# FailureAnnotation(
#   category="reasoning",
#   subcategory="planning_error",
#   severity="high",
#   ...
# )
```

### MAST Categories

- **Communication** - Agent coordination failures
  - `handoff_failure` - Failed agent handoffs
  - `message_loss` - Lost inter-agent messages
  - `protocol_violation` - Protocol mismatches

- **Reasoning** - Logic and planning errors
  - `planning_error` - Flawed plans
  - `goal_drift` - Task objective deviation
  - `invalid_conclusion` - Incorrect reasoning

- **Tool Use** - External tool failures
  - `tool_error` - Tool execution errors
  - `invalid_input` - Malformed tool inputs
  - `timeout` - Tool call timeouts

- **State Management** - State handling issues
  - `state_corruption` - Invalid state
  - `state_loss` - Lost state data
  - `checkpoint_failure` - Failed checkpoints

## Development

Run tests:

```bash
pytest packages/analysis/tests -v
```

Run with hot reload:

```bash
make run-api
```

## Usage Examples

### Get Trace Graph

```bash
curl http://localhost:8000/api/traces/trace-123/graph
```

### Filter Traces by Status

```bash
curl "http://localhost:8000/api/traces?status=error&limit=10"
```

### Analyze Failures

```bash
curl -X POST http://localhost:8000/api/traces/trace-123/analyze
```

### Get Metrics

```bash
curl "http://localhost:8000/api/metrics?start_time=2024-01-01T00:00:00Z"
```

## Architecture

```
┌──────────────────┐
│   REST API       │
│   (FastAPI)      │
└────────┬─────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌──────────────────┐  ┌──────────────────┐
│  Graph Builder   │  │  Classifier      │
│  - Agent Graph   │  │  - MAST Rules    │
│  - Paths         │  │  - Annotations   │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         ▼                     ▼
┌─────────────────────────────────┐
│      PostgreSQL Database         │
│      - Traces, Spans            │
│      - Agents, Messages         │
│      - Failure Annotations      │
└─────────────────────────────────┘
```

## License

MIT - see root LICENSE file for details
