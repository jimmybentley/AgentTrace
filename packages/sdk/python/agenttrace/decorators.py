"""Standalone decorators for AgentTrace instrumentation.

These decorators work without instantiating an AgentTracer object.
They use a global tracer instance configured via environment variables.
"""

import asyncio
import functools
import logging
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agenttrace._otel import get_tracer, setup_opentelemetry
from agenttrace._serialize import serialize
from agenttrace.config import get_config

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Global tracer instance
_global_tracer = None


def _get_global_tracer():
    """Get or create global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        config = get_config()
        setup_opentelemetry(config)
        _global_tracer = get_tracer(__name__)
    return _global_tracer


@contextmanager
def trace(name: str, metadata: dict | None = None):
    """Start a new trace (top-level execution).

    This is a standalone version of AgentTracer.trace() that uses
    global configuration from environment variables.

    Args:
        name: Name of the trace
        metadata: Optional metadata to attach to the trace

    Yields:
        The active span

    Example:
        >>> from agenttrace.decorators import trace
        >>> with trace("my-task"):
        ...     result = my_function()
    """
    config = get_config()
    if not config.enabled:
        yield None
        return

    tracer = _get_global_tracer()

    with tracer.start_as_current_span(name) as span:
        # Set metadata attributes
        if metadata:
            for key, value in metadata.items():
                span.set_attribute(f"agenttrace.metadata.{key}", str(value))

        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def agent(
    name: str,
    role: str = "unknown",
    model: str | None = None,
) -> Callable[[F], F]:
    """Decorator to mark a function as an agent.

    Args:
        name: Name of the agent
        role: Role of the agent
        model: LLM model used by the agent

    Returns:
        Decorated function

    Example:
        >>> from agenttrace.decorators import agent
        >>> @agent(name="Planner", role="planner")
        >>> async def plan(task: str) -> str:
        ...     return "plan"
    """

    def decorator(func: F) -> F:
        config = get_config()
        if not config.enabled:
            return func

        tracer = _get_global_tracer()

        # Support both sync and async functions
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(f"agent:{name}") as span:
                    # Set agent attributes
                    span.set_attribute("agent.name", name)
                    span.set_attribute("agent.role", role)
                    span.set_attribute("agenttrace.kind", "agent_call")

                    if model:
                        span.set_attribute("agent.model", model)

                    # Capture input
                    input_data = {"args": args, "kwargs": kwargs}
                    span.set_attribute("agenttrace.input", serialize(input_data))

                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("agenttrace.output", serialize(result))
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(f"agent:{name}") as span:
                    # Set agent attributes
                    span.set_attribute("agent.name", name)
                    span.set_attribute("agent.role", role)
                    span.set_attribute("agenttrace.kind", "agent_call")

                    if model:
                        span.set_attribute("agent.model", model)

                    # Capture input
                    input_data = {"args": args, "kwargs": kwargs}
                    span.set_attribute("agenttrace.input", serialize(input_data))

                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("agenttrace.output", serialize(result))
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return sync_wrapper  # type: ignore

    return decorator


def tool(name: str) -> Callable[[F], F]:
    """Decorator to mark a function as a tool.

    Args:
        name: Name of the tool

    Returns:
        Decorated function

    Example:
        >>> from agenttrace.decorators import tool
        >>> @tool(name="search")
        >>> async def search(query: str) -> list[str]:
        ...     return ["result"]
    """

    def decorator(func: F) -> F:
        config = get_config()
        if not config.enabled:
            return func

        tracer = _get_global_tracer()

        # Support both sync and async functions
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(f"tool:{name}") as span:
                    span.set_attribute("tool.name", name)
                    span.set_attribute("agenttrace.kind", "tool_call")

                    # Capture input
                    input_data = {"args": args, "kwargs": kwargs}
                    span.set_attribute("agenttrace.input", serialize(input_data))

                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("agenttrace.output", serialize(result))
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(f"tool:{name}") as span:
                    span.set_attribute("tool.name", name)
                    span.set_attribute("agenttrace.kind", "tool_call")

                    # Capture input
                    input_data = {"args": args, "kwargs": kwargs}
                    span.set_attribute("agenttrace.input", serialize(input_data))

                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("agenttrace.output", serialize(result))
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return sync_wrapper  # type: ignore

    return decorator
