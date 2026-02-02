# AgentTrace Python SDK Guide

Complete guide to using the AgentTrace Python SDK for instrumenting multi-agent applications.

## Overview

The AgentTrace SDK provides both manual and automatic instrumentation for multi-agent LLM systems. It's built on OpenTelemetry and exports traces via OTLP to the AgentTrace backend.

## Installation

### Basic Installation

```bash
pip install agenttrace
```

### With Framework Support

```bash
# LangGraph
pip install agenttrace[langgraph]

# AutoGen
pip install agenttrace[autogen]

# CrewAI
pip install agenttrace[crewai]

# All frameworks
pip install agenttrace[all]
```

## Quick Start

### Auto-Instrumentation (Recommended)

The easiest way to get started:

```python
import agenttrace

# Instrument BEFORE importing your framework
agenttrace.instrument(["langgraph"])

# Now use LangGraph as normal
from langgraph.graph import StateGraph

graph = StateGraph(dict)
# Traces are captured automatically
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
    return f"Plan for: {task}"

async def main():
    with tracer.trace("my-workflow"):
        result = await plan("Research AI trends")
```

## Configuration

### Environment Variables

```bash
# Required
AGENTTRACE_ENDPOINT=http://localhost:4318

# Optional
AGENTTRACE_SERVICE_NAME=my-app
AGENTTRACE_ENABLED=true
AGENTTRACE_DEBUG=false
```

### Programmatic Configuration

```python
import agenttrace

agenttrace.configure(
    endpoint="http://localhost:4318",
    service_name="my-app",
    enabled=True,
    debug=False,
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

#### Constructor

```python
AgentTracer(
    endpoint: str = "http://localhost:4318",
    service_name: str = "agenttrace-app",
    framework: str = "custom",
)
```

**Parameters:**
- `endpoint` - OTLP ingestion endpoint URL
- `service_name` - Name of your application
- `framework` - Framework identifier (custom, langgraph, autogen, crewai)

#### trace()

Context manager for creating a top-level trace.

```python
with tracer.trace(name: str, metadata: dict | None = None):
    # Your code here
    pass
```

**Parameters:**
- `name` - Trace name (e.g., "customer_support_workflow")
- `metadata` - Optional metadata dictionary (e.g., {"user_id": "123"})

**Example:**
```python
with tracer.trace("order_processing", metadata={"order_id": "456"}):
    result = process_order()
```

#### agent()

Decorator for marking a function as an agent.

```python
@tracer.agent(
    name: str,
    role: str = "unknown",
    model: str | None = None
)
def my_agent(input: str) -> str:
    pass
```

**Parameters:**
- `name` - Agent name (e.g., "Planner", "Executor")
- `role` - Agent role (e.g., "planner", "executor", "validator")
- `model` - LLM model name (e.g., "gpt-4", "claude-3-sonnet")

**Example:**
```python
@tracer.agent("Planner", role="planner", model="gpt-4")
async def plan_workflow(task: str) -> dict:
    # Planning logic
    return {"steps": [...]}
```

#### tool()

Decorator for marking a function as a tool.

```python
@tracer.tool(name: str)
def my_tool(input: str) -> str:
    pass
```

**Parameters:**
- `name` - Tool name (e.g., "search", "calculator", "database_query")

**Example:**
```python
@tracer.tool("web_search")
def search(query: str) -> list[str]:
    # Search implementation
    return ["result1", "result2"]
```

#### message()

Record an inter-agent message.

```python
tracer.message(
    from_agent: str,
    to_agent: str,
    content: Any,
    message_type: str = "request"
)
```

**Parameters:**
- `from_agent` - Source agent name
- `to_agent` - Destination agent name
- `content` - Message content (will be serialized to JSON)
- `message_type` - Message type (request, response, handoff, broadcast)

**Example:**
```python
tracer.message(
    "Planner",
    "Executor",
    {"task": "execute_plan", "plan": [...]},
    "handoff"
)
```

#### checkpoint()

Create a checkpoint for replay debugging.

```python
tracer.checkpoint(name: str, state: Any)
```

**Parameters:**
- `name` - Checkpoint name (e.g., "after_planning")
- `state` - State to save (will be serialized to JSON)

**Example:**
```python
plan = await planner.run(task)
tracer.checkpoint("after_planning", {"plan": plan, "task": task})
```

### Standalone Decorators

Import from `agenttrace.decorators` for simpler usage without creating a tracer:

```python
from agenttrace.decorators import agent, tool, trace

@agent(name="MyAgent", role="assistant")
def my_agent(input: str) -> str:
    return f"Processed: {input}"

@tool(name="calculator")
def calculate(expr: str) -> float:
    return eval(expr)

with trace("workflow"):
    result = my_agent("Hello")
    calc = calculate("2+2")
```

These use global configuration from environment variables.

### Auto-Instrumentation

#### instrument()

Auto-instrument specified frameworks.

```python
agenttrace.instrument(frameworks: list[str] | None = None)
```

**Parameters:**
- `frameworks` - List of framework names to instrument, or None for all available

**Supported Frameworks:**
- `"langgraph"` - LangGraph state machines
- `"autogen"` - Microsoft AutoGen agents
- `"crewai"` - CrewAI agent orchestration

**Example:**
```python
# Instrument specific frameworks
agenttrace.instrument(["langgraph", "autogen"])

# Instrument all available
agenttrace.instrument()
```

**Important:** Call `instrument()` BEFORE importing the frameworks you want to instrument.

## Framework-Specific Guides

### LangGraph

```python
import agenttrace
agenttrace.instrument(["langgraph"])

from langgraph.graph import StateGraph

def planner(state: dict) -> dict:
    # Your planner logic
    return {"plan": "..."}

def executor(state: dict) -> dict:
    # Your executor logic
    return {"result": "..."}

# Build graph
graph = StateGraph(dict)
graph.add_node("planner", planner)
graph.add_node("executor", executor)
graph.add_edge("planner", "executor")
graph.set_entry_point("planner")
graph.set_finish_point("executor")

app = graph.compile()

# Run - traces captured automatically
result = app.invoke({"input": "task"})
```

**What's Captured:**
- Each node execution as a span
- Node names as agent names
- State transitions
- Input/output for each node
- Execution order and timing

### AutoGen

```python
import agenttrace
agenttrace.instrument(["autogen"])

from autogen import ConversableAgent

# Create agents
assistant = ConversableAgent(
    "assistant",
    system_message="You are a helpful assistant.",
    llm_config={"model": "gpt-4"}
)

user_proxy = ConversableAgent(
    "user_proxy",
    human_input_mode="NEVER",
)

# Run conversation - traces captured automatically
user_proxy.initiate_chat(
    assistant,
    message="Tell me a joke"
)
```

**What's Captured:**
- Each agent message as a span
- Agent names and roles
- Message content
- Conversation flow
- Turn-by-turn timing

### CrewAI

```python
import agenttrace
agenttrace.instrument(["crewai"])

from crewai import Crew, Agent, Task

# Define agents
researcher = Agent(
    role="Researcher",
    goal="Research AI trends",
    backstory="Expert researcher"
)

# Define tasks
research_task = Task(
    description="Research latest AI trends",
    agent=researcher
)

# Create crew
crew = Crew(
    agents=[researcher],
    tasks=[research_task]
)

# Run - traces captured automatically
result = crew.kickoff()
```

**What's Captured:**
- Crew execution as top-level trace
- Each task as a span
- Agent assignments
- Task dependencies
- Execution timeline

## Advanced Usage

### Custom Attributes

Add custom attributes to spans:

```python
from agenttrace import get_current_span

@tracer.agent("Planner")
def plan(task: str) -> dict:
    span = get_current_span()
    span.set_attribute("task.priority", "high")
    span.set_attribute("task.category", "research")

    # Your logic
    return {"plan": "..."}
```

### Events

Add events to spans for important moments:

```python
from agenttrace import get_current_span

@tracer.agent("Executor")
def execute(plan: dict) -> dict:
    span = get_current_span()

    span.add_event("execution_started", {"plan_steps": len(plan["steps"])})

    for step in plan["steps"]:
        result = execute_step(step)
        span.add_event("step_completed", {"step": step, "result": result})

    span.add_event("execution_finished")

    return {"result": "..."}
```

### Error Handling

Errors are automatically captured, but you can add context:

```python
@tracer.agent("Validator")
def validate(data: dict) -> bool:
    try:
        # Validation logic
        return True
    except ValidationError as e:
        span = get_current_span()
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.set_attribute("error.type", "validation")
        span.set_attribute("error.details", e.details)
        raise
```

### Async Support

The SDK fully supports async functions:

```python
@tracer.agent("AsyncPlanner")
async def async_plan(task: str) -> dict:
    # Async planning logic
    await asyncio.sleep(1)
    return {"plan": "..."}

async def main():
    with tracer.trace("async_workflow"):
        plan = await async_plan("task")
```

### Context Propagation

The SDK automatically propagates context in async code:

```python
async def workflow():
    with tracer.trace("main_workflow"):
        # Context automatically propagates to child tasks
        results = await asyncio.gather(
            agent1.run(),
            agent2.run(),
            agent3.run()
        )
```

## Best Practices

### 1. Use Descriptive Names

```python
# Good
@tracer.agent("CustomerSupportPlanner", role="planner")
def plan_support(query: str) -> dict:
    pass

# Less helpful
@tracer.agent("Agent1", role="unknown")
def func1(x: str) -> dict:
    pass
```

### 2. Add Relevant Metadata

```python
with tracer.trace("order_processing", metadata={
    "user_id": user.id,
    "order_id": order.id,
    "priority": order.priority,
    "source": "api"
}):
    process_order(order)
```

### 3. Use Checkpoints at Key Points

```python
@tracer.agent("Planner")
def plan(task: str) -> dict:
    plan = generate_plan(task)

    # Checkpoint after planning
    tracer.checkpoint("after_planning", {
        "plan": plan,
        "task": task,
        "timestamp": datetime.now()
    })

    return plan
```

### 4. Record Inter-Agent Messages

```python
def coordinator(task: str):
    # Assign task to agent
    tracer.message(
        "Coordinator",
        "Executor",
        {"task": task, "priority": "high"},
        "handoff"
    )

    result = executor.run(task)

    # Get result back
    tracer.message(
        "Executor",
        "Coordinator",
        {"result": result, "status": "completed"},
        "response"
    )
```

### 5. Disable in Production (if needed)

```python
# Disable tracing in production
agenttrace.configure(
    enabled=os.getenv("ENV") != "production"
)
```

## Performance Considerations

### Batching

The SDK batches spans before sending:

```python
# Default batch size: 512 spans
# Adjust if needed:
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    schedule_delay_millis=5000,
    max_export_batch_size=512
)
```

### Sampling

For high-volume applications, use sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
tracer = AgentTracer(
    endpoint="http://localhost:4318",
    sampler=TraceIdRatioBased(0.1)
)
```

### Overhead

The SDK is designed for minimal overhead:
- Async span export (non-blocking)
- Efficient serialization
- Batched network requests
- Typical overhead: <1ms per span

## Troubleshooting

### Traces Not Appearing

**1. Check configuration:**
```python
from agenttrace.config import get_config
print(get_config())
```

**2. Verify endpoint:**
```bash
curl http://localhost:4318/health
```

**3. Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Import Errors

Make sure you've installed the correct extras:

```bash
pip install agenttrace[langgraph]  # For LangGraph
```

### Auto-Instrumentation Not Working

Ensure you call `instrument()` BEFORE importing frameworks:

```python
# Correct order
import agenttrace
agenttrace.instrument(["langgraph"])
from langgraph.graph import StateGraph  # Import AFTER instrument

# Wrong order (won't work)
from langgraph.graph import StateGraph
import agenttrace
agenttrace.instrument(["langgraph"])  # Too late!
```

## Examples

See [packages/sdk/python/examples/](../packages/sdk/python/examples/) for complete examples:

- `manual_example.py` - Manual instrumentation
- `langgraph_example.py` - LangGraph auto-instrumentation
- `decorator_example.py` - Standalone decorators

## Related Documentation

- [Getting Started Guide](getting-started.md) - Setup instructions
- [API Reference](api-reference.md) - REST API documentation
- [Architecture Overview](architecture.md) - System design

For the complete SDK reference, see [packages/sdk/python/README.md](../packages/sdk/python/README.md).
