# AgentTrace SDK Examples

This directory contains examples demonstrating different ways to use the AgentTrace Python SDK.

## Examples

### 1. Manual Instrumentation (`manual_example.py`)

Shows how to use the `AgentTracer` class to manually instrument a multi-agent application.

```bash
python manual_example.py
```

**Features demonstrated:**
- Creating an `AgentTracer` instance
- `@tracer.agent()` decorator for agent functions
- `@tracer.tool()` decorator for tool functions
- `tracer.trace()` context manager
- `tracer.message()` for inter-agent communication
- `tracer.checkpoint()` for creating checkpoints

### 2. LangGraph Auto-Instrumentation (`langgraph_example.py`)

Shows how to auto-instrument a LangGraph application.

```bash
pip install agenttrace[langgraph]
python langgraph_example.py
```

**Features demonstrated:**
- Auto-instrumentation with `agenttrace.instrument(["langgraph"])`
- Automatic trace capture from LangGraph workflows
- No manual decorator usage required

### 3. Standalone Decorators (`decorator_example.py`)

Shows how to use standalone decorators without creating an `AgentTracer` instance.

```bash
export AGENTTRACE_ENDPOINT=http://localhost:4318
export AGENTTRACE_SERVICE_NAME=my-app
python decorator_example.py
```

**Features demonstrated:**
- Standalone `@agent()` and `@tool()` decorators
- Standalone `trace()` context manager
- Configuration via environment variables

## Prerequisites

1. **Start the AgentTrace backend:**

```bash
# From the repository root
make run-api
```

This starts:
- OTLP ingestion service on port 4318
- PostgreSQL database
- Web UI on port 5173

2. **Install the SDK:**

```bash
# Basic installation
pip install -e packages/sdk/python

# With framework support
pip install -e packages/sdk/python[langgraph]
pip install -e packages/sdk/python[all]  # All frameworks
```

## Configuration

The SDK can be configured via:

1. **Environment variables:**
   - `AGENTTRACE_ENDPOINT` - OTLP endpoint (default: http://localhost:4318)
   - `AGENTTRACE_SERVICE_NAME` - Service name (default: agenttrace-app)
   - `AGENTTRACE_ENABLED` - Enable/disable tracing (default: true)

2. **Programmatically:**

```python
import agenttrace

agenttrace.configure(
    endpoint="http://localhost:4318",
    service_name="my-app"
)
```

3. **Via AgentTracer constructor:**

```python
from agenttrace import AgentTracer

tracer = AgentTracer(
    endpoint="http://localhost:4318",
    service_name="my-app"
)
```

## Viewing Traces

After running an example, view the traces in the web UI:

1. Open http://localhost:5173 in your browser
2. You should see your traces listed
3. Click on a trace to view:
   - Agent communication graph
   - Span timeline
   - Input/output for each agent
   - Checkpoints (if created)

## Troubleshooting

**Traces not appearing?**

1. Check that the OTLP ingestion service is running:
   ```bash
   curl http://localhost:4318/health
   ```

2. Check the SDK configuration:
   ```python
   from agenttrace.config import get_config
   print(get_config())
   ```

3. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

**Import errors?**

Make sure you've installed the SDK with the appropriate extras:
```bash
pip install -e packages/sdk/python[langgraph,autogen,crewai]
```
