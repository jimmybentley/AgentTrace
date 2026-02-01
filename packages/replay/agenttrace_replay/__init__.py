"""AgentTrace Replay - Checkpoint management and replay debugging.

This package provides the replay engine for AgentTrace, enabling developers to:
- Create checkpoints at key points during agent execution
- Restore agent state from checkpoints
- Re-execute agents with optional modifications
- Compare original vs. replay outputs
"""

__version__ = "0.1.0"

from .checkpoint import Checkpoint, CheckpointManager
from .differ import compute_diff, format_diff_for_display
from .executor import ReplayConfig, ReplayExecutor, ReplayResult
from .executors import get_executor, register_executor

__all__ = [
    "Checkpoint",
    "CheckpointManager",
    "ReplayConfig",
    "ReplayExecutor",
    "ReplayResult",
    "compute_diff",
    "format_diff_for_display",
    "get_executor",
    "register_executor",
]
