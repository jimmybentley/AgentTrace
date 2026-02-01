"""Framework-specific executors for replay.

This package contains executors that know how to re-execute agent code
from checkpointed state for different frameworks.
"""

from .base import AgentExecutor
from .generic import generic_executor
from .mock import mock_executor

__all__ = ["AgentExecutor", "generic_executor", "mock_executor"]

# Executor registry - maps framework names to executor functions
EXECUTOR_REGISTRY: dict[str, AgentExecutor] = {
    "generic": generic_executor,
    "mock": mock_executor,
}

# Try to import optional framework executors
try:
    from .langgraph import langgraph_executor

    EXECUTOR_REGISTRY["langgraph"] = langgraph_executor
except ImportError:
    pass  # LangGraph not installed


def get_executor(framework: str) -> AgentExecutor:
    """Get an executor for a specific framework.

    Args:
        framework: Framework name (e.g., "langgraph", "autogen", "generic")

    Returns:
        Executor function for that framework

    Raises:
        ValueError: If no executor is registered for the framework
    """
    executor = EXECUTOR_REGISTRY.get(framework)
    if not executor:
        # Fall back to generic executor
        return EXECUTOR_REGISTRY["generic"]
    return executor


def register_executor(framework: str, executor: AgentExecutor):
    """Register a custom executor for a framework.

    Args:
        framework: Framework name
        executor: Executor function
    """
    EXECUTOR_REGISTRY[framework] = executor
