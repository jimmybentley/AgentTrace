# agenttrace-core

Core data models and utilities for AgentTrace.

## Installation

```bash
pip install agenttrace-core
```

## Usage

```python
from agenttrace_core.models import Trace, Span, Agent

# Create a trace
trace = Trace(name="my_trace", start_time=datetime.utcnow())
```
