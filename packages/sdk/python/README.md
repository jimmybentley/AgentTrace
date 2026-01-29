# agenttrace

Python SDK for AgentTrace instrumentation.

## Installation

```bash
pip install agenttrace
```

## Usage

```python
from agenttrace import AgentTracer

tracer = AgentTracer(endpoint="http://localhost:4317")

@tracer.agent("Planner", role="planner")
async def plan(task: str):
    # Your agent logic here
    pass
```
