# AgentTrace Replay Engine

The replay engine for AgentTrace enables "time-travel" debugging by allowing developers to replay agent execution from checkpoints.

## Features

- **Checkpoint Management**: Save agent state at key points during execution
- **State Restoration**: Load and reconstruct agent context from checkpoints
- **Re-execution**: Run from checkpoint with optional input modifications
- **Diff Visualization**: Compare original vs. replay outputs
- **Framework Support**: Extensible architecture for different agent frameworks

## Installation

```bash
pip install agenttrace-replay
```

## Quick Start

```python
import asyncpg
from agenttrace_replay import CheckpointManager, ReplayExecutor, ReplayConfig

# Initialize
db_pool = await asyncpg.create_pool("postgresql://...")
checkpoint_manager = CheckpointManager(db_pool)
replay_executor = ReplayExecutor(checkpoint_manager, db_pool)

# Create checkpoints for a trace
checkpoint_ids = await checkpoint_manager.auto_checkpoint_trace("trace-123")

# Execute a replay
result = await replay_executor.replay(checkpoint_ids[0])

# Execute replay with modified input
config = ReplayConfig(
    modified_input={"query": "new question"},
    dry_run=True  # Use mock executor (no LLM calls)
)
result = await replay_executor.replay(checkpoint_ids[0], config)

# Check the diff
print(result.diff["summary"])
if result.diff["has_changes"]:
    print("Changes detected:")
    for key, change in result.diff["changed"].items():
        print(f"  {key}: {change['old']} -> {change['new']}")
```

## API Endpoints

The replay package exposes REST API endpoints:

### Checkpoint Endpoints

- `GET /api/traces/{trace_id}/checkpoints` - List checkpoints for a trace
- `POST /api/traces/{trace_id}/checkpoints` - Create checkpoints (auto mode)
- `GET /api/checkpoints/{checkpoint_id}` - Get checkpoint details
- `DELETE /api/checkpoints/{checkpoint_id}` - Delete a checkpoint

### Replay Endpoints

- `POST /api/checkpoints/{checkpoint_id}/replay` - Execute a replay
- `GET /api/replays/{replay_id}` - Get replay result
- `GET /api/replays/{replay_id}/diff` - Get detailed diff
- `GET /api/traces/{trace_id}/replays` - List replays for a trace

### Example API Usage

```bash
# Create checkpoints
curl -X POST http://localhost:8000/api/traces/trace-123/checkpoints \
  -H "Content-Type: application/json" \
  -d '{"auto": true}'

# Execute replay with modified input
curl -X POST http://localhost:8000/api/checkpoints/chk-456/replay \
  -H "Content-Type: application/json" \
  -d '{
    "modified_input": {"query": "new question"},
    "dry_run": true
  }'
```

## Executors

The replay engine supports different frameworks through executors:

- **Mock Executor**: For testing without LLM calls
- **Generic Executor**: Fallback that returns original output
- **LangGraph Executor**: For LangGraph agents (simplified in V1)

### Custom Executors

You can register custom executors for your framework:

```python
from agenttrace_replay.executors import register_executor

async def my_executor(input, state, config, overrides=None):
    # Your re-execution logic here
    return {"output": "..."}

register_executor("my_framework", my_executor)
```

## Architecture

```
agenttrace_replay/
├── checkpoint.py          # Checkpoint, CheckpointManager
├── executor.py            # ReplayExecutor, ReplayConfig, ReplayResult
├── differ.py              # Diff computation
├── api.py                 # FastAPI router
└── executors/
    ├── base.py            # AgentExecutor protocol
    ├── mock.py            # Mock executor
    ├── generic.py         # Generic fallback executor
    └── langgraph.py       # LangGraph-specific executor
```

## Testing

Run tests with pytest:

```bash
pytest packages/replay/tests
```

## Development

The replay engine is part of AgentTrace Phase 4. See the [design document](../../agenttrace-design-doc.md#phase-4-replay-engine) for full details.

## License

MIT
