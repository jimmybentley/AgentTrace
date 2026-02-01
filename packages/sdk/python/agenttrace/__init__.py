"""AgentTrace Python SDK - Instrumentation for multi-agent LLM systems.

This SDK provides tools for instrumenting multi-agent applications with
OpenTelemetry-compatible tracing, enabling debugging and observability
via the AgentTrace platform.
"""

from agenttrace.config import configure
from agenttrace.decorators import agent as agent_decorator
from agenttrace.decorators import tool as tool_decorator
from agenttrace.decorators import trace as trace_decorator
from agenttrace.integrations import instrument_frameworks
from agenttrace.tracer import AgentTracer

__version__ = "0.1.0"


def instrument(frameworks: list[str] | None = None) -> None:
    """Auto-instrument specified frameworks.

    This is a convenience function that instruments one or more agent
    frameworks to automatically emit traces to AgentTrace.

    Args:
        frameworks: List of frameworks to instrument.
                   If None, instruments all available frameworks.
                   Options: "langgraph", "autogen", "crewai"

    Example:
        >>> import agenttrace
        >>> agenttrace.instrument(["langgraph"])
        >>>
        >>> # Now use LangGraph as normal - traces are sent automatically
        >>> from langgraph.graph import StateGraph
        >>> # ... your code

    Note:
        This function should be called once at application startup,
        before creating any agent instances.
    """
    instrument_frameworks(frameworks)


# Public API
__all__ = [
    # Main classes
    "AgentTracer",
    # Decorators (can be used standalone or via AgentTracer)
    "agent_decorator",
    "tool_decorator",
    "trace_decorator",
    # Configuration
    "configure",
    # Auto-instrumentation
    "instrument",
    # Version
    "__version__",
]
