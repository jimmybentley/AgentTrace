# Getting Started with AgentTrace

This guide will help you set up and start using AgentTrace for debugging and observability of your multi-agent LLM systems.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose** - For running the full stack
- **Python 3.11+** - For local development
- **Node.js 18+** - For web UI development
- **Git** - For cloning the repository

Optional:
- **uv** - Python package manager (recommended for development)
- **PostgreSQL client** - For database inspection

## Quick Start (Docker Compose)

The fastest way to get AgentTrace running is with Docker Compose:

### 1. Clone the Repository

```bash
git clone https://github.com/jimmybentley/AgentTrace.git
cd AgentTrace
```

### 2. Start the Full Stack

```bash
docker compose up -d
```

This starts all services:
- PostgreSQL with TimescaleDB (port 5432)
- Ingestion service (port 4318)
- Analysis API (port 8000)
- Web UI (port 3000)

### 3. Verify Services

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:4318/health

# Open web UI
open http://localhost:3000
```

### 4. Send Your First Trace

Install the Python SDK:

```bash
pip install agenttrace
```

Create a simple instrumented agent:

```python
# example.py
from agenttrace import AgentTracer

tracer = AgentTracer(endpoint="http://localhost:4318")

@tracer.agent("SimpleAgent", role="assistant")
def process_request(query: str) -> str:
    return f"Processed: {query}"

if __name__ == "__main__":
    with tracer.trace("simple-workflow", metadata={"user": "demo"}):
        result = process_request("Hello AgentTrace!")
        print(result)
```

Run it:

```bash
python example.py
```

### 5. View Your Trace

1. Open http://localhost:3000
2. You should see your trace in the list
3. Click on it to view the agent graph and timeline

## Local Development Setup

For development with hot reloading and debugging:

### 1. Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all project dependencies
make install
```

### 2. Start the Database

```bash
# Start PostgreSQL with TimescaleDB
make docker-up

# Run database migrations
make migrate
```

### 3. Start Services

Open three terminal windows:

**Terminal 1: API Server**
```bash
make run-api
# Runs on http://localhost:8000
```

**Terminal 2: Web UI**
```bash
make run-web
# Runs on http://localhost:5173
```

**Terminal 3: Run your instrumented application**
```bash
python your_agent_app.py
```

### 4. Verify Installation

```bash
# Run all tests
make test

# Run integration tests
make test-integration

# Verify imports
make verify
```

## Instrumenting Your Application

### Option 1: Auto-Instrumentation (Recommended)

For LangGraph, AutoGen, or CrewAI applications:

```python
import agenttrace

# Instrument before importing your framework
agenttrace.instrument(["langgraph"])

# Now use your framework normally
from langgraph.graph import StateGraph

# All traces are automatically captured
```

### Option 2: Manual Instrumentation

For custom agents or more control:

```python
from agenttrace import AgentTracer

tracer = AgentTracer(
    endpoint="http://localhost:4318",
    service_name="my-agent-app",
)

@tracer.agent("Planner", role="planner", model="gpt-4")
async def plan_task(task: str) -> dict:
    # Your planning logic
    return {"plan": "..."}

@tracer.tool("search")
async def search(query: str) -> list:
    # Your search logic
    return ["result1", "result2"]

async def main():
    with tracer.trace("research-workflow"):
        plan = await plan_task("Research AI trends")
        results = await search("AI trends 2025")
```

### Option 3: Standalone Decorators

Simplest approach without creating a tracer instance:

```python
from agenttrace.decorators import agent, tool, trace

@agent(name="MyAgent", role="assistant")
def my_agent(input: str) -> str:
    return f"Processed: {input}"

with trace("my-workflow"):
    result = my_agent("Hello")
```

## Configuration

### Environment Variables

Create a `.env` file in your project:

```bash
# AgentTrace Backend
AGENTTRACE_ENDPOINT=http://localhost:4318
AGENTTRACE_SERVICE_NAME=my-app
AGENTTRACE_ENABLED=true

# Database (for local development)
DATABASE_URL=postgresql://agenttrace:dev_password@localhost:5432/agenttrace
```

### Programmatic Configuration

```python
import agenttrace

agenttrace.configure(
    endpoint="http://localhost:4318",
    service_name="my-app",
)
```

## Understanding the UI

### Trace List View

The main view shows all traces with:
- Trace name and ID
- Start time and duration
- Status (success/error)
- Number of spans
- Service name

**Filters:**
- Status (ok/error)
- Service name
- Time range

### Trace Detail View

Click on a trace to see:

**1. Agent Communication Graph**
- Force-directed D3.js graph
- Nodes = agents
- Edges = messages between agents
- Click nodes/edges for details

**2. Span Timeline**
- Gantt-style timeline
- Shows execution order and duration
- Parent-child relationships visible
- Click spans for detailed attributes

**3. Failure Analysis Panel**
- MAST taxonomy classifications
- Severity levels
- Failure descriptions
- Filter by category

**4. Replay Controls**
- Create checkpoints
- Execute replays with modified inputs
- View diff between original and replay

## Common Workflows

### Debugging a Failed Multi-Agent Task

1. **Find the failing trace** - Filter by status=error in the UI
2. **View the agent graph** - Identify which agents communicated
3. **Check the timeline** - See which spans failed and when
4. **Review failure annotations** - Understand the failure category (reasoning, communication, etc.)
5. **Create a checkpoint** - Save state before the failure
6. **Replay with modifications** - Test fixes without re-running the full workflow

### Analyzing Agent Performance

1. **View metrics dashboard** - See overall statistics
2. **Check agent execution counts** - Identify bottlenecks
3. **Review span durations** - Find slow agents
4. **Analyze communication patterns** - Optimize agent coordination

### Monitoring Production Systems

1. **Set up continuous ingestion** - Point your app to AgentTrace
2. **Monitor failure rates** - Track error trends over time
3. **Review failure categories** - Identify systematic issues
4. **Set up alerts** - Get notified of critical failures (future feature)

## Next Steps

- **[Architecture Overview](architecture.md)** - Understand how AgentTrace works
- **[API Reference](api-reference.md)** - Explore REST API endpoints
- **[SDK Guide](sdk-guide.md)** - Deep dive into Python SDK features
- **[Deployment Guide](deployment.md)** - Deploy to production
- **[Examples](../packages/sdk/python/examples/)** - Working code examples

## Troubleshooting

### Traces Not Appearing

**Check endpoint configuration:**
```python
from agenttrace.config import get_config
print(get_config())
```

**Verify backend is running:**
```bash
curl http://localhost:4318/health
```

**Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Connection Errors

**Check database is running:**
```bash
docker ps | grep postgres
```

**Verify connection:**
```bash
psql postgresql://agenttrace:dev_password@localhost:5432/agenttrace -c "SELECT 1"
```

**Check migrations:**
```bash
make migrate
```

### Web UI Not Loading

**Check API is running:**
```bash
curl http://localhost:8000/api/traces
```

**Check browser console** for errors

**Verify environment variables:**
```bash
# In web/.env
VITE_API_URL=http://localhost:8000
```

## Getting Help

- **Documentation**: Check docs/ folder for detailed guides
- **Examples**: See packages/sdk/python/examples/ for working code
- **Issues**: Report bugs at https://github.com/jimmybentley/AgentTrace/issues
- **Discussions**: Ask questions in GitHub Discussions

## Summary

You've learned how to:
- ✅ Start AgentTrace with Docker Compose
- ✅ Set up local development environment
- ✅ Instrument your agent application
- ✅ Send traces and view them in the UI
- ✅ Configure AgentTrace for your needs

Next, explore the [Architecture Overview](architecture.md) to understand how AgentTrace works under the hood.
