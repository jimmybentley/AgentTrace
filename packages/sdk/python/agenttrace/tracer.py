"""Core tracer implementation for AgentTrace SDK."""

import asyncio
import functools
import inspect
import logging
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agenttrace._otel import get_tracer, setup_opentelemetry
from agenttrace._serialize import serialize
from agenttrace.config import AgentTraceConfig, get_config

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class AgentTracer:
    """Main entry point for AgentTrace instrumentation.

    The AgentTracer provides decorators and context managers for instrumenting
    multi-agent applications with minimal code changes.

    Example:
        >>> tracer = AgentTracer(endpoint="http://localhost:4318")
        >>>
        >>> @tracer.agent("Planner", role="planner", model="claude-3-opus")
        >>> async def plan(task: str) -> str:
        ...     return "plan"
        >>>
        >>> @tracer.tool("search")
        >>> async def search(query: str) -> list[str]:
        ...     return ["result"]
        >>>
        >>> async def main():
        ...     with tracer.trace("research-task"):
        ...         plan_result = await plan("Research AI trends")
        ...         tracer.message("Planner", "Researcher", plan_result, "handoff")
        ...         results = await search("AI trends")
    """

    def __init__(
        self,
        endpoint: str | None = None,
        service_name: str | None = None,
        framework: str = "custom",
        config: AgentTraceConfig | None = None,
    ):
        """Initialize the AgentTrace tracer.

        Args:
            endpoint: OTLP HTTP endpoint (default: http://localhost:4318)
            service_name: Name of this service/application
            framework: Framework identifier (custom, langgraph, autogen, crewai)
            config: Optional configuration object (overrides other parameters)
        """
        if config is None:
            config = get_config()
            if endpoint is not None:
                config.endpoint = endpoint
            if service_name is not None:
                config.service_name = service_name

        self.config = config
        self.framework = framework

        # Set up OpenTelemetry
        setup_opentelemetry(self.config)

        # Get tracer
        self._tracer = get_tracer(__name__)
        self._current_trace_id: str | None = None

    @contextmanager
    def trace(self, name: str, metadata: dict | None = None):
        """Start a new trace (top-level execution).

        Args:
            name: Name of the trace
            metadata: Optional metadata to attach to the trace

        Yields:
            The active span

        Example:
            >>> with tracer.trace("research-task", metadata={"user_id": "123"}):
            ...     result = await my_agent("input")
        """
        if not self.config.enabled:
            yield None
            return

        with self._tracer.start_as_current_span(name) as span:
            self._current_trace_id = format(span.get_span_context().trace_id, "032x")

            # Set framework attribute
            span.set_attribute("agenttrace.framework", self.framework)

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
            finally:
                self._current_trace_id = None

    def agent(
        self,
        name: str,
        role: str = "unknown",
        model: str | None = None,
    ) -> Callable[[F], F]:
        """Decorator to mark a function as an agent.

        Args:
            name: Name of the agent
            role: Role of the agent (e.g., "planner", "executor")
            model: LLM model used by the agent (e.g., "claude-3-opus")

        Returns:
            Decorated function

        Example:
            >>> @tracer.agent("Planner", role="planner", model="gpt-4")
            >>> async def plan(task: str) -> str:
            ...     return "plan"
        """

        def decorator(func: F) -> F:
            if not self.config.enabled:
                return func

            # Support both sync and async functions
            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    with self._tracer.start_as_current_span(f"agent:{name}") as span:
                        # Set agent attributes
                        span.set_attribute("agent.name", name)
                        span.set_attribute("agent.role", role)
                        span.set_attribute("agent.framework", self.framework)
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
                    with self._tracer.start_as_current_span(f"agent:{name}") as span:
                        # Set agent attributes
                        span.set_attribute("agent.name", name)
                        span.set_attribute("agent.role", role)
                        span.set_attribute("agent.framework", self.framework)
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

    def tool(self, name: str) -> Callable[[F], F]:
        """Decorator to mark a function as a tool.

        Args:
            name: Name of the tool

        Returns:
            Decorated function

        Example:
            >>> @tracer.tool("search")
            >>> async def search(query: str) -> list[str]:
            ...     return ["result"]
        """

        def decorator(func: F) -> F:
            if not self.config.enabled:
                return func

            # Support both sync and async functions
            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    with self._tracer.start_as_current_span(f"tool:{name}") as span:
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
                    with self._tracer.start_as_current_span(f"tool:{name}") as span:
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

    def message(
        self,
        from_agent: str,
        to_agent: str,
        content: Any,
        message_type: str = "request",
    ) -> None:
        """Record an inter-agent message.

        Args:
            from_agent: Name of the sending agent
            to_agent: Name of the receiving agent
            content: Message content
            message_type: Type of message (request, response, broadcast, handoff)

        Example:
            >>> tracer.message("Planner", "Executor", plan_result, "handoff")
        """
        if not self.config.enabled:
            return

        span = trace.get_current_span()

        # Add as span event
        span.add_event(
            "agent_message",
            attributes={
                "message.from_agent": from_agent,
                "message.to_agent": to_agent,
                "message.type": message_type,
                "message.content": serialize(content),
            },
        )

    def checkpoint(self, name: str, state: Any) -> None:
        """Create a checkpoint at current position.

        Args:
            name: Name of the checkpoint
            state: State to save

        Example:
            >>> tracer.checkpoint("after_planning", {"plan": plan_result})
        """
        if not self.config.enabled:
            return

        span = trace.get_current_span()

        # Calculate state size
        state_json = serialize(state)
        state_size = len(state_json.encode("utf-8"))

        span.add_event(
            "checkpoint",
            attributes={
                "checkpoint.name": name,
                "checkpoint.state": state_json,
                "checkpoint.state_size_bytes": state_size,
                "checkpoint.restorable": True,
            },
        )
