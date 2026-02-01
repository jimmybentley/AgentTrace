# AgentTrace Python SDK

Instrument your multi-agent LLM applications for debugging and observability.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Manual Instrumentation** - Decorators for agents and tools
- **Auto-Instrumentation** - Automatic tracing for LangGraph, AutoGen, and CrewAI
- **OpenTelemetry-Based** - Standard OTLP export to any compatible backend
- **Async Support** - Works with both sync and async functions
- **Minimal Overhead** - Designed for production use
- **Type Safe** - Full type hints for better IDE support

## Installation

### Basic Installation

```bash
pip install agenttrace
```

### With Framework Support

```bash
# LangGraph support
pip install agenttrace[langgraph]

# AutoGen support
pip install agenttrace[autogen]

# CrewAI support
pip install agenttrace[crewai]

# All frameworks
pip install agenttrace[all]
```

## Quick Start

### Auto-Instrumentation (Recommended)

The easiest way to get started is with auto-instrumentation:

```python
import agenttrace

# Instrument LangGraph automatically
agenttrace.instrument(["langgraph"])

# Now use LangGraph as normal - traces are sent automatically
from langgraph.graph import StateGraph

graph = StateGraph(dict)
# ... your LangGraph code
```

### Manual Instrumentation

For custom agents or more control:

```python
from agenttrace import AgentTracer

tracer = AgentTracer(
    endpoint="http://localhost:4318",
    service_name="my-agent-app",
)

@tracer.agent("Planner", role="planner", model="gpt-4")
async def plan(task: str) -> str:
    # Your planning logic
    return f"Plan for: {task}"

@tracer.tool("search")
async def search(query: str) -> list[str]:
    # Your search logic
    return ["result1", "result2"]

async def main():
    with tracer.trace("research-task", metadata={"user_id": "123"}):
        plan = await plan("Research AI trends")
        results = await search("AI trends 2025")
```

### Standalone Decorators

For simpler use cases without creating a tracer instance:

```python
from agenttrace.decorators import agent, tool, trace

@agent(name="MyAgent", role="assistant")
async def my_agent(input: str) -> str:
    return f"Processed: {input}"

@tool(name="calculator")
def calculate(expression: str) -> float:
    return eval(expression)

async def main():
    with trace("my-workflow"):
        result = await my_agent("Hello")
        calc_result = calculate("2 + 2")
```

## Configuration

### Environment Variables

```bash
export AGENTTRACE_ENDPOINT=http://localhost:4318
export AGENTTRACE_SERVICE_NAME=my-app
export AGENTTRACE_ENABLED=true
```

### Programmatic Configuration

```python
import agenttrace

agenttrace.configure(
    endpoint="http://localhost:4318",
    service_name="my-app",
)
```

### Per-Instance Configuration

```python
from agenttrace import AgentTracer

tracer = AgentTracer(
    endpoint="http://localhost:4318",
    service_name="my-app",
    framework="custom",
)
```

## API Reference

### AgentTracer

Main class for manual instrumentation.

#### Methods

##### `trace(name: str, metadata: dict | None = None)`

Context manager for creating a top-level trace.

```python
with tracer.trace("my-task", metadata={"user_id": "123"}):
    # Your code here
    pass
```

##### `agent(name: str, role: str = "unknown", model: str | None = None)`

Decorator for marking a function as an agent.

```python
@tracer.agent("Planner", role="planner", model="gpt-4")
async def plan(task: str) -> str:
    return "plan"
```

##### `tool(name: str)`

Decorator for marking a function as a tool.

```python
@tracer.tool("search")
async def search(query: str) -> list[str]:
    return ["result"]
```

##### `message(from_agent: str, to_agent: str, content: Any, message_type: str = "request")`

Record an inter-agent message.

```python
tracer.message("Agent1", "Agent2", {"data": "value"}, "handoff")
```

##### `checkpoint(name: str, state: Any)`

Create a checkpoint for replay debugging.

```python
tracer.checkpoint("after_planning", {"plan": plan_result})
```

### Standalone Decorators

Import from `agenttrace.decorators`:

- `trace(name: str, metadata: dict | None = None)` - Context manager
- `agent(name: str, role: str = "unknown", model: str | None = None)` - Agent decorator
- `tool(name: str)` - Tool decorator

These use global configuration from environment variables.

### Auto-Instrumentation

#### `agenttrace.instrument(frameworks: list[str] | None = None)`

Auto-instrument specified frameworks.

```python
import agenttrace

# Instrument specific frameworks
agenttrace.instrument(["langgraph", "autogen"])

# Or instrument all available frameworks
agenttrace.instrument()
```

**Supported frameworks:**
- `langgraph` - LangGraph state machines
- `autogen` - Microsoft AutoGen agents
- `crewai` - CrewAI agent orchestration

## Framework-Specific Guides

### LangGraph

```python
import agenttrace

# Call this BEFORE importing LangGraph
agenttrace.instrument(["langgraph"])

from langgraph.graph import StateGraph

# Your LangGraph code works as normal
graph = StateGraph(dict)
graph.add_node("planner", planner_func)
graph.add_node("executor", executor_func)
# ...
app = graph.compile()
result = app.invoke({"input": "task"})
```

### AutoGen

```python
import agenttrace

agenttrace.instrument(["autogen"])

from autogen import ConversableAgent

# Your AutoGen code works as normal
agent = ConversableAgent("assistant")
# ...
```

### CrewAI

```python
import agenttrace

agenttrace.instrument(["crewai"])

from crewai import Crew, Agent, Task

# Your CrewAI code works as normal
crew = Crew(agents=[...], tasks=[...])
result = crew.kickoff()
```

## Examples

See the `examples/` directory for complete working examples:

- `manual_example.py` - Manual instrumentation with AgentTracer
- `langgraph_example.py` - Auto-instrumentation for LangGraph
- `decorator_example.py` - Using standalone decorators

## Testing

Run the test suite:

```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=agenttrace --cov-report=html
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourorg/agenttrace.git
cd agenttrace

# Install in development mode
pip install -e packages/sdk/python[dev]

# Run tests
pytest packages/sdk/python/tests
```

### Code Style

This project uses:
- **Ruff** for linting and formatting
- **Type hints** for all public APIs
- **Docstrings** in Google style

```bash
# Format code
ruff format packages/sdk/python

# Lint code
ruff check packages/sdk/python
```

## Architecture

The SDK is built on OpenTelemetry and exports traces via OTLP HTTP:

```
Your Application
       │
       ├─ AgentTracer / Decorators
       │  └─ Capture spans, attributes
       │
       ├─ OpenTelemetry SDK
       │  └─ Process and batch spans
       │
       └─ OTLP HTTP Exporter
          └─ Send to AgentTrace (localhost:4318)
                     ↓
              AgentTrace Backend
                     ↓
              PostgreSQL Storage
                     ↓
              Web UI (localhost:5173)
```

## Troubleshooting

### Traces Not Appearing

1. **Check endpoint is correct:**
   ```python
   from agenttrace.config import get_config
   print(get_config())
   ```

2. **Verify backend is running:**
   ```bash
   curl http://localhost:4318/health
   ```

3. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Import Errors

Make sure you've installed the SDK with the required extras:

```bash
pip install agenttrace[langgraph]  # For LangGraph
pip install agenttrace[all]        # For all frameworks
```

### Performance Concerns

The SDK is designed for minimal overhead:
- Batched span export (default batch size: 512)
- Async processing
- Configurable sampling (future feature)

To disable tracing in production:

```bash
export AGENTTRACE_ENABLED=false
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation:** https://docs.agenttrace.dev
- **Issues:** https://github.com/yourorg/agenttrace/issues
- **Discussions:** https://github.com/yourorg/agenttrace/discussions
