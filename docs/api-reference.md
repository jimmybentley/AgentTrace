# AgentTrace API Reference

Complete REST API documentation for AgentTrace services.

## Base URLs

- **Ingestion Service**: `http://localhost:4318`
- **Analysis API**: `http://localhost:8000/api`

## Authentication

Currently, AgentTrace does not require authentication. This will be added in a future release.

## Ingestion API

### POST /v1/traces

Ingest OTLP traces.

**Endpoint:** `POST /v1/traces`

**Content-Type:**
- `application/json` - OTLP JSON format
- `application/x-protobuf` - OTLP protobuf format

**Request Body (JSON):**
```json
{
  "resourceSpans": [
    {
      "resource": {
        "attributes": [
          {"key": "service.name", "value": {"stringValue": "my-service"}},
          {"key": "agent.framework", "value": {"stringValue": "langgraph"}}
        ]
      },
      "scopeSpans": [
        {
          "spans": [
            {
              "traceId": "0102030405060708090a0b0c0d0e0f10",
              "spanId": "0102030405060708",
              "name": "agent_execution",
              "startTimeUnixNano": "1640000000000000000",
              "endTimeUnixNano": "1640000001000000000",
              "attributes": [
                {"key": "agent.name", "value": {"stringValue": "Planner"}}
              ],
              "status": {"code": 1}
            }
          ]
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "traces_received": 1,
  "spans_received": 1
}
```

**Status Codes:**
- `200 OK` - Trace ingested successfully
- `400 Bad Request` - Invalid OTLP format
- `500 Internal Server Error` - Database error

**cURL Example:**
```bash
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d @trace.json
```

### GET /health

Check ingestion service health.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service or database is down

### GET /metrics

Get Prometheus-style metrics.

**Endpoint:** `GET /metrics`

**Response:**
```text
# HELP agenttrace_traces_received_total Total traces received
# TYPE agenttrace_traces_received_total counter
agenttrace_traces_received_total 1234

# HELP agenttrace_spans_received_total Total spans received
# TYPE agenttrace_spans_received_total counter
agenttrace_spans_received_total 15678

# HELP agenttrace_ingestion_errors_total Total ingestion errors
# TYPE agenttrace_ingestion_errors_total counter
agenttrace_ingestion_errors_total 5

# HELP agenttrace_ingestion_duration_seconds Ingestion duration
# TYPE agenttrace_ingestion_duration_seconds histogram
agenttrace_ingestion_duration_seconds_bucket{le="0.1"} 1000
agenttrace_ingestion_duration_seconds_bucket{le="0.5"} 1200
agenttrace_ingestion_duration_seconds_bucket{le="1.0"} 1230
agenttrace_ingestion_duration_seconds_count 1234
agenttrace_ingestion_duration_seconds_sum 123.45
```

## Analysis API

### Trace Endpoints

#### GET /api/traces

List traces with pagination and filtering.

**Endpoint:** `GET /api/traces`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset` | int | 0 | Pagination offset |
| `limit` | int | 50 | Number of traces (max: 100) |
| `status` | str | - | Filter by status (ok, error) |
| `service_name` | str | - | Filter by service name |
| `start_time_gte` | datetime | - | Start time >= value (ISO 8601) |
| `start_time_lte` | datetime | - | Start time <= value (ISO 8601) |

**Response:**
```json
{
  "traces": [
    {
      "trace_id": "trace-123",
      "name": "customer_support",
      "start_time": "2026-01-01T00:00:00Z",
      "end_time": "2026-01-01T00:00:10Z",
      "duration_ms": 10000,
      "service_name": "support-bot",
      "status": "ok",
      "span_count": 15,
      "agent_count": 3,
      "metadata": {"user_id": "user-456"}
    }
  ],
  "total": 100,
  "offset": 0,
  "limit": 50
}
```

**cURL Example:**
```bash
# Get all traces
curl http://localhost:8000/api/traces

# Get error traces only
curl "http://localhost:8000/api/traces?status=error"

# Get traces from specific service
curl "http://localhost:8000/api/traces?service_name=support-bot&limit=10"

# Get traces in time range
curl "http://localhost:8000/api/traces?start_time_gte=2026-01-01T00:00:00Z&start_time_lte=2026-01-31T23:59:59Z"
```

#### GET /api/traces/{trace_id}

Get detailed trace information.

**Endpoint:** `GET /api/traces/{trace_id}`

**Path Parameters:**
- `trace_id` (str): Trace ID

**Response:**
```json
{
  "trace_id": "trace-123",
  "name": "customer_support",
  "start_time": "2026-01-01T00:00:00Z",
  "end_time": "2026-01-01T00:00:10Z",
  "duration_ms": 10000,
  "service_name": "support-bot",
  "status": "ok",
  "metadata": {"user_id": "user-456"},
  "spans": [...],
  "agents": [...]
}
```

**Status Codes:**
- `200 OK` - Trace found
- `404 Not Found` - Trace not found

**cURL Example:**
```bash
curl http://localhost:8000/api/traces/trace-123
```

#### GET /api/traces/{trace_id}/spans

Get all spans for a trace.

**Endpoint:** `GET /api/traces/{trace_id}/spans`

**Response:**
```json
{
  "trace_id": "trace-123",
  "span_count": 15,
  "spans": [
    {
      "span_id": "span-456",
      "parent_span_id": null,
      "name": "planner_agent",
      "start_time": "2026-01-01T00:00:00Z",
      "end_time": "2026-01-01T00:00:05Z",
      "duration_ms": 5000,
      "attributes": {
        "agent.name": "Planner",
        "agent.role": "planner",
        "agent.model": "gpt-4",
        "input": "Plan a customer support workflow",
        "output": "Step 1: Analyze query..."
      },
      "events": [],
      "status": "ok",
      "children": ["span-789", "span-012"]
    }
  ]
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/traces/trace-123/spans
```

#### DELETE /api/traces/{trace_id}

Delete a trace and all associated data.

**Endpoint:** `DELETE /api/traces/{trace_id}`

**Response:**
```json
{
  "status": "deleted",
  "trace_id": "trace-123",
  "spans_deleted": 15,
  "messages_deleted": 8
}
```

**Status Codes:**
- `200 OK` - Trace deleted
- `404 Not Found` - Trace not found

**cURL Example:**
```bash
curl -X DELETE http://localhost:8000/api/traces/trace-123
```

### Graph Endpoints

#### GET /api/traces/{trace_id}/graph

Get agent communication graph.

**Endpoint:** `GET /api/traces/{trace_id}/graph`

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
      "model": "gpt-4",
      "execution_count": 3,
      "total_duration_ms": 5000,
      "avg_duration_ms": 1666,
      "error_count": 0
    },
    {
      "agent_id": "agent-2",
      "name": "Executor",
      "role": "executor",
      "framework": "langgraph",
      "execution_count": 5,
      "total_duration_ms": 8000,
      "avg_duration_ms": 1600,
      "error_count": 1
    }
  ],
  "edges": [
    {
      "from_agent": "Planner",
      "to_agent": "Executor",
      "message_count": 2,
      "message_types": ["handoff", "request"],
      "total_messages": 2
    }
  ],
  "metrics": {
    "node_count": 2,
    "edge_count": 1,
    "avg_messages_per_agent": 1.0,
    "max_depth": 3
  }
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/traces/trace-123/graph
```

#### GET /api/traces/{trace_id}/graph/paths

Find paths between agents.

**Endpoint:** `GET /api/traces/{trace_id}/graph/paths`

**Query Parameters:**
- `from_agent` (str, required): Source agent name
- `to_agent` (str, required): Destination agent name

**Response:**
```json
{
  "trace_id": "trace-123",
  "from_agent": "Planner",
  "to_agent": "Verifier",
  "paths": [
    ["Planner", "Executor", "Verifier"],
    ["Planner", "Validator", "Verifier"]
  ],
  "shortest_path": ["Planner", "Executor", "Verifier"],
  "path_count": 2
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/traces/trace-123/graph/paths?from_agent=Planner&to_agent=Verifier"
```

### Failure Analysis Endpoints

#### GET /api/traces/{trace_id}/failures

Get failure annotations for a trace.

**Endpoint:** `GET /api/traces/{trace_id}/failures`

**Query Parameters:**
- `category` (str): Filter by MAST category
- `severity` (str): Filter by severity (low, medium, high, critical)

**Response:**
```json
{
  "trace_id": "trace-123",
  "failure_count": 2,
  "failures": [
    {
      "annotation_id": "ann-789",
      "span_id": "span-456",
      "category": "reasoning",
      "subcategory": "planning_error",
      "severity": "high",
      "description": "Agent failed to consider edge case in customer query",
      "detected_at": "2026-01-01T00:00:05Z",
      "span_name": "planner_agent",
      "error_message": "Invalid plan generated"
    },
    {
      "annotation_id": "ann-790",
      "span_id": "span-457",
      "category": "communication",
      "subcategory": "handoff_failure",
      "severity": "medium",
      "description": "Failed to hand off task to Executor agent",
      "detected_at": "2026-01-01T00:00:08Z",
      "span_name": "coordinator",
      "error_message": "Agent not available"
    }
  ]
}
```

**cURL Example:**
```bash
# Get all failures
curl http://localhost:8000/api/traces/trace-123/failures

# Get reasoning failures only
curl "http://localhost:8000/api/traces/trace-123/failures?category=reasoning"

# Get high severity failures
curl "http://localhost:8000/api/traces/trace-123/failures?severity=high"
```

#### POST /api/traces/{trace_id}/analyze

Trigger failure analysis on a trace.

**Endpoint:** `POST /api/traces/{trace_id}/analyze`

**Request Body (optional):**
```json
{
  "force": true,
  "rules": ["reasoning", "communication"]
}
```

**Response:**
```json
{
  "trace_id": "trace-123",
  "status": "analyzed",
  "failures_detected": 2,
  "categories": {
    "reasoning": 1,
    "communication": 1,
    "tool_use": 0,
    "state_management": 0
  },
  "analysis_duration_ms": 150
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/traces/trace-123/analyze
```

### Checkpoint Endpoints

#### GET /api/traces/{trace_id}/checkpoints

List checkpoints for a trace.

**Endpoint:** `GET /api/traces/{trace_id}/checkpoints`

**Response:**
```json
{
  "trace_id": "trace-123",
  "checkpoint_count": 3,
  "checkpoints": [
    {
      "checkpoint_id": "chk-1",
      "span_id": "span-456",
      "name": "after_planning",
      "created_at": "2026-01-01T00:00:05Z",
      "state_size_bytes": 1024,
      "can_replay": true
    }
  ]
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/traces/trace-123/checkpoints
```

#### POST /api/traces/{trace_id}/checkpoints

Create checkpoints for a trace.

**Endpoint:** `POST /api/traces/{trace_id}/checkpoints`

**Request Body:**
```json
{
  "auto": true,
  "span_ids": ["span-456", "span-789"]
}
```

**Response:**
```json
{
  "trace_id": "trace-123",
  "checkpoints_created": 3,
  "checkpoint_ids": ["chk-1", "chk-2", "chk-3"]
}
```

**cURL Example:**
```bash
# Auto-create checkpoints at key points
curl -X POST http://localhost:8000/api/traces/trace-123/checkpoints \
  -H "Content-Type: application/json" \
  -d '{"auto": true}'

# Create checkpoints at specific spans
curl -X POST http://localhost:8000/api/traces/trace-123/checkpoints \
  -H "Content-Type: application/json" \
  -d '{"span_ids": ["span-456"]}'
```

#### GET /api/checkpoints/{checkpoint_id}

Get checkpoint details.

**Endpoint:** `GET /api/checkpoints/{checkpoint_id}`

**Response:**
```json
{
  "checkpoint_id": "chk-1",
  "trace_id": "trace-123",
  "span_id": "span-456",
  "name": "after_planning",
  "created_at": "2026-01-01T00:00:05Z",
  "state": {
    "agent_name": "Planner",
    "input": "Plan workflow",
    "output": "Step 1: ...",
    "context": {...}
  },
  "configuration": {
    "temperature": 0.7,
    "model": "gpt-4"
  }
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/checkpoints/chk-1
```

#### DELETE /api/checkpoints/{checkpoint_id}

Delete a checkpoint.

**Endpoint:** `DELETE /api/checkpoints/{checkpoint_id}`

**Response:**
```json
{
  "status": "deleted",
  "checkpoint_id": "chk-1"
}
```

**cURL Example:**
```bash
curl -X DELETE http://localhost:8000/api/checkpoints/chk-1
```

### Replay Endpoints

#### POST /api/checkpoints/{checkpoint_id}/replay

Execute a replay from a checkpoint.

**Endpoint:** `POST /api/checkpoints/{checkpoint_id}/replay`

**Request Body:**
```json
{
  "modified_input": {
    "query": "Modified customer query"
  },
  "dry_run": true,
  "timeout_seconds": 30
}
```

**Response:**
```json
{
  "replay_id": "replay-1",
  "checkpoint_id": "chk-1",
  "status": "completed",
  "started_at": "2026-01-01T00:10:00Z",
  "completed_at": "2026-01-01T00:10:05Z",
  "duration_ms": 5000,
  "output": {
    "result": "Modified result based on new input"
  },
  "diff": {
    "has_changes": true,
    "summary": "Output changed due to modified input",
    "changed": {
      "result": {
        "old": "Original result",
        "new": "Modified result based on new input"
      }
    }
  }
}
```

**cURL Example:**
```bash
# Dry run replay (uses mock executor)
curl -X POST http://localhost:8000/api/checkpoints/chk-1/replay \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Real replay with modified input
curl -X POST http://localhost:8000/api/checkpoints/chk-1/replay \
  -H "Content-Type: application/json" \
  -d '{
    "modified_input": {"query": "New query"},
    "dry_run": false
  }'
```

#### GET /api/replays/{replay_id}

Get replay result.

**Endpoint:** `GET /api/replays/{replay_id}`

**Response:**
```json
{
  "replay_id": "replay-1",
  "checkpoint_id": "chk-1",
  "trace_id": "trace-123",
  "status": "completed",
  "started_at": "2026-01-01T00:10:00Z",
  "completed_at": "2026-01-01T00:10:05Z",
  "duration_ms": 5000,
  "output": {...},
  "error": null
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/replays/replay-1
```

#### GET /api/replays/{replay_id}/diff

Get detailed diff for a replay.

**Endpoint:** `GET /api/replays/{replay_id}/diff`

**Response:**
```json
{
  "replay_id": "replay-1",
  "has_changes": true,
  "summary": "2 fields changed",
  "added": {
    "new_field": "new value"
  },
  "removed": {
    "old_field": "old value"
  },
  "changed": {
    "result": {
      "old": "Original result",
      "new": "Modified result"
    }
  },
  "unchanged": ["field1", "field2"]
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/replays/replay-1/diff
```

#### GET /api/traces/{trace_id}/replays

List all replays for a trace.

**Endpoint:** `GET /api/traces/{trace_id}/replays`

**Response:**
```json
{
  "trace_id": "trace-123",
  "replay_count": 2,
  "replays": [
    {
      "replay_id": "replay-1",
      "checkpoint_id": "chk-1",
      "status": "completed",
      "started_at": "2026-01-01T00:10:00Z",
      "duration_ms": 5000,
      "has_changes": true
    }
  ]
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/traces/trace-123/replays
```

### Metrics Endpoints

#### GET /api/metrics

Get aggregated metrics.

**Endpoint:** `GET /api/metrics`

**Query Parameters:**
- `start_time` (datetime): Start of time range (ISO 8601)
- `end_time` (datetime): End of time range (ISO 8601)

**Response:**
```json
{
  "time_range": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-01-31T23:59:59Z"
  },
  "total_traces": 1000,
  "total_spans": 15000,
  "total_agents": 50,
  "avg_trace_duration_ms": 5000,
  "median_trace_duration_ms": 4000,
  "p95_trace_duration_ms": 10000,
  "success_rate": 0.95,
  "error_rate": 0.05,
  "top_agents": [
    {
      "name": "Planner",
      "execution_count": 500,
      "avg_duration_ms": 1500,
      "error_rate": 0.02
    }
  ],
  "failure_categories": {
    "reasoning": 30,
    "communication": 20,
    "tool_use": 10,
    "state_management": 5
  },
  "traces_over_time": [
    {"date": "2026-01-01", "count": 50},
    {"date": "2026-01-02", "count": 55}
  ]
}
```

**cURL Example:**
```bash
# Get all-time metrics
curl http://localhost:8000/api/metrics

# Get metrics for time range
curl "http://localhost:8000/api/metrics?start_time=2026-01-01T00:00:00Z&end_time=2026-01-31T23:59:59Z"
```

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "error": {
    "code": "TRACE_NOT_FOUND",
    "message": "Trace with ID 'trace-123' not found",
    "details": {}
  }
}
```

**Common Error Codes:**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TRACE_NOT_FOUND` | 404 | Trace ID does not exist |
| `INVALID_PARAMETER` | 400 | Invalid query parameter or request body |
| `DATABASE_ERROR` | 500 | Internal database error |
| `TIMEOUT` | 504 | Request timeout |

## Rate Limiting

Currently, there is no rate limiting. This will be added in a future release.

## Pagination

List endpoints support offset-based pagination:

- `offset` - Number of items to skip (default: 0)
- `limit` - Number of items to return (default: 50, max: 100)

Response includes pagination metadata:

```json
{
  "data": [...],
  "total": 1000,
  "offset": 0,
  "limit": 50,
  "has_more": true
}
```

## Filtering

Most list endpoints support filtering via query parameters:

- Exact match: `?status=error`
- Range: `?start_time_gte=2026-01-01&start_time_lte=2026-01-31`
- Multiple values: `?category=reasoning,communication` (future)

## Sorting

Sorting is not currently supported but will be added in a future release.

## Related Documentation

- [Getting Started Guide](getting-started.md) - Setup and usage
- [Architecture Overview](architecture.md) - System design
- [SDK Guide](sdk-guide.md) - Python SDK reference
