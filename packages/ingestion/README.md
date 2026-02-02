# AgentTrace Ingestion Service

Production-ready OTLP ingestion service for receiving and normalizing multi-agent system traces.

## Overview

The ingestion service provides a FastAPI-based HTTP endpoint that accepts OpenTelemetry Protocol (OTLP) traces, normalizes them for different agent frameworks, and stores them in PostgreSQL with TimescaleDB for efficient time-series querying.

## Features

- **OTLP HTTP Endpoint** - Full OTLP/HTTP implementation (protobuf and JSON)
- **Framework Normalization** - Intelligent parsing for LangGraph, AutoGen, CrewAI, and generic agents
- **Batch Processing** - High-throughput ingestion with connection pooling
- **Agent Extraction** - Automatic detection and extraction of agent metadata
- **Message Detection** - Identifies inter-agent communication patterns
- **Health Checks** - Built-in health and readiness endpoints
- **Error Handling** - Graceful handling of malformed traces with detailed logging

## Installation

```bash
pip install agenttrace-ingestion
```

Or as part of the monorepo:

```bash
uv sync --package agenttrace-ingestion
```

## Quick Start

Start the ingestion service:

```bash
uvicorn agenttrace_ingestion.server:app --port 4318
```

The service will be available at:
- **OTLP endpoint**: `http://localhost:4318/v1/traces`
- **Health check**: `http://localhost:4318/health`
- **Metrics**: `http://localhost:4318/metrics`

## Sending Traces

### Using the AgentTrace SDK

```python
from agenttrace import AgentTracer

tracer = AgentTracer(endpoint="http://localhost:4318")

with tracer.trace("my-workflow"):
    # Your agent code
    pass
```

### Using OpenTelemetry SDK

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("agent-execution"):
    # Your agent code
    pass
```

### Using cURL

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

## Framework Normalization

The ingestion service automatically detects and normalizes traces from different frameworks:

### LangGraph

Detects:
- Graph node executions
- State transitions
- Edge traversals
- Tool calls

```python
# Attributes extracted:
# - agent.framework = "langgraph"
# - agent.name = node name
# - agent.role = inferred from node type
```

### AutoGen

Detects:
- Agent conversations
- Message exchanges
- Group chat coordination

```python
# Attributes extracted:
# - agent.framework = "autogen"
# - agent.name = agent name
# - agent.role = agent role
```

### CrewAI

Detects:
- Crew executions
- Task assignments
- Agent collaborations

```python
# Attributes extracted:
# - agent.framework = "crewai"
# - agent.name = agent name
# - agent.role = crew role
```

### Generic Agents

Falls back to generic normalization for custom frameworks:

```python
# Uses standard OpenTelemetry attributes:
# - service.name
# - span.kind
# - Custom attributes in span.attributes
```

## Configuration

Configure via environment variables:

```bash
# Database
DATABASE_URL=postgresql://agenttrace:password@localhost:5432/agenttrace

# Server
OTLP_HTTP_PORT=4318
WORKERS=4

# Performance
BATCH_SIZE=100
POOL_SIZE=20
POOL_MAX_OVERFLOW=10
```

Or via command line:

```bash
uvicorn agenttrace_ingestion.server:app \
  --host 0.0.0.0 \
  --port 4318 \
  --workers 4
```

## API Endpoints

### POST /v1/traces

OTLP trace ingestion endpoint.

**Request:**
- Content-Type: `application/json` or `application/x-protobuf`
- Body: OTLP ExportTraceServiceRequest

**Response:**
- 200 OK: `{"status": "success", "traces_received": 1}`
- 400 Bad Request: Invalid OTLP data
- 500 Internal Server Error: Database error

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### GET /metrics

Prometheus-style metrics endpoint.

**Metrics:**
- `agenttrace_traces_received_total` - Total traces received
- `agenttrace_spans_received_total` - Total spans received
- `agenttrace_ingestion_errors_total` - Total ingestion errors
- `agenttrace_ingestion_duration_seconds` - Ingestion duration histogram

## Architecture

```
┌─────────────────┐
│  OTLP Traces    │
│  (HTTP/JSON)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  FastAPI Server     │
│  - /v1/traces       │
│  - /health          │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Normalizers        │
│  - LangGraph        │
│  - AutoGen          │
│  - CrewAI           │
│  - Generic          │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Database Writer    │
│  - Batch insert     │
│  - Connection pool  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  PostgreSQL +       │
│  TimescaleDB        │
└─────────────────────┘
```

## Development

Run tests:

```bash
pytest packages/ingestion/tests -v
```

Run with hot reload:

```bash
make run-ingestion
# or
uvicorn agenttrace_ingestion.server:app --reload --port 4318
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install uv && uv sync --package agenttrace-ingestion

EXPOSE 4318
CMD ["uvicorn", "agenttrace_ingestion.server:app", "--host", "0.0.0.0", "--port", "4318"]
```

### Kubernetes

See [deploy/kubernetes/ingestion.yaml](../../deploy/kubernetes/ingestion.yaml) for example deployment.

### Performance Tuning

For high-throughput scenarios:

```bash
# Increase workers
uvicorn agenttrace_ingestion.server:app --workers 8

# Increase batch size
export BATCH_SIZE=500

# Increase connection pool
export POOL_SIZE=50
export POOL_MAX_OVERFLOW=20
```

## Monitoring

The ingestion service exposes metrics at `/metrics` in Prometheus format:

```bash
# Scrape configuration for Prometheus
scrape_configs:
  - job_name: 'agenttrace-ingestion'
    static_configs:
      - targets: ['localhost:4318']
```

## Troubleshooting

### Traces Not Being Stored

1. Check database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

2. Check ingestion logs:
   ```bash
   # Look for errors in uvicorn output
   ```

3. Verify OTLP format:
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   ```

### Performance Issues

1. Increase batch size and workers
2. Check database connection pool size
3. Monitor `/metrics` endpoint for bottlenecks

## License

MIT - see root LICENSE file for details
