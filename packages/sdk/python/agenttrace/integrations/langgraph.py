"""LangGraph auto-instrumentation for AgentTrace.

This module patches LangGraph to automatically emit AgentTrace-compatible spans
without requiring manual instrumentation.

Usage:
    >>> from agenttrace.integrations.langgraph import instrument_langgraph
    >>> instrument_langgraph()
    >>>
    >>> # Now all LangGraph graph executions will emit traces
    >>> from langgraph.graph import StateGraph
    >>> # ... your LangGraph code
"""

import asyncio
import functools
import logging
from typing import Any

from opentelemetry.trace import Status, StatusCode

from agenttrace._otel import get_tracer, setup_opentelemetry
from agenttrace._serialize import serialize
from agenttrace.config import get_config

logger = logging.getLogger(__name__)

_instrumented = False


def instrument_langgraph() -> None:
    """Auto-instrument LangGraph to emit AgentTrace-compatible spans.

    Call this once at application startup. After calling, all LangGraph
    graph executions will automatically emit traces to the configured
    AgentTrace endpoint.

    Example:
        >>> from agenttrace.integrations.langgraph import instrument_langgraph
        >>> instrument_langgraph()
        >>>
        >>> # Now use LangGraph as normal
        >>> from langgraph.graph import StateGraph
        >>> graph = StateGraph(dict)
        >>> # ... define nodes and edges
        >>> app = graph.compile()
        >>> result = app.invoke({"input": "test"})
    """
    global _instrumented

    if _instrumented:
        logger.debug("LangGraph already instrumented")
        return

    config = get_config()
    if not config.enabled:
        logger.info("AgentTrace disabled, skipping LangGraph instrumentation")
        return

    # Set up OpenTelemetry
    setup_opentelemetry(config)

    try:
        # Import LangGraph components
        from langgraph.graph import StateGraph
        from langgraph.pregel import Pregel

        # Patch StateGraph.add_node
        _patch_add_node(StateGraph)

        # Patch Pregel (CompiledGraph) invoke methods
        _patch_pregel(Pregel)

        _instrumented = True
        logger.info("LangGraph instrumented successfully")

    except ImportError as e:
        logger.warning(f"Failed to instrument LangGraph: {e}. Is langgraph installed?")
    except Exception as e:
        logger.error(f"Error instrumenting LangGraph: {e}")


def _patch_add_node(state_graph_class: Any) -> None:
    """Patch StateGraph.add_node to wrap node actions.

    Args:
        state_graph_class: The StateGraph class to patch
    """
    original_add_node = state_graph_class.add_node

    @functools.wraps(original_add_node)
    def patched_add_node(self, node: str, action: Any = None, **kwargs):
        """Patched add_node that wraps the action."""
        if action is not None:
            # Wrap the action to emit spans
            wrapped_action = _wrap_node_action(node, action)
            return original_add_node(self, node, wrapped_action, **kwargs)
        return original_add_node(self, node, action, **kwargs)

    state_graph_class.add_node = patched_add_node


def _patch_pregel(pregel_class: Any) -> None:
    """Patch Pregel (CompiledGraph) invoke methods.

    Args:
        pregel_class: The Pregel class to patch
    """
    # Patch invoke
    if hasattr(pregel_class, "invoke"):
        original_invoke = pregel_class.invoke

        @functools.wraps(original_invoke)
        def patched_invoke(self, input: Any, config: dict | None = None, **kwargs):
            """Patched invoke that creates parent trace span."""
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span("langgraph.invoke") as span:
                span.set_attribute("agenttrace.framework", "langgraph")
                span.set_attribute("agenttrace.kind", "graph_execution")
                span.set_attribute("agenttrace.input", serialize(input))

                try:
                    result = original_invoke(self, input, config, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        pregel_class.invoke = patched_invoke

    # Patch ainvoke (async)
    if hasattr(pregel_class, "ainvoke"):
        original_ainvoke = pregel_class.ainvoke

        @functools.wraps(original_ainvoke)
        async def patched_ainvoke(self, input: Any, config: dict | None = None, **kwargs):
            """Patched ainvoke that creates parent trace span."""
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span("langgraph.ainvoke") as span:
                span.set_attribute("agenttrace.framework", "langgraph")
                span.set_attribute("agenttrace.kind", "graph_execution")
                span.set_attribute("agenttrace.input", serialize(input))

                try:
                    result = await original_ainvoke(self, input, config, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        pregel_class.ainvoke = patched_ainvoke


def _wrap_node_action(node_name: str, action: Any) -> Any:
    """Wrap a node action to emit spans.

    Args:
        node_name: Name of the node
        action: The action function to wrap

    Returns:
        Wrapped action function
    """
    tracer = get_tracer(__name__)

    if asyncio.iscoroutinefunction(action):

        @functools.wraps(action)
        async def async_wrapped(*args, **kwargs):
            with tracer.start_as_current_span(f"langgraph.node:{node_name}") as span:
                span.set_attribute("langgraph.node", node_name)
                span.set_attribute("agent.name", node_name)
                span.set_attribute("agent.framework", "langgraph")
                span.set_attribute("agenttrace.kind", "agent_call")

                # Try to extract state from args (first arg is usually state)
                if args:
                    span.set_attribute("agenttrace.input", serialize(args[0]))

                try:
                    result = await action(*args, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return async_wrapped

    else:

        @functools.wraps(action)
        def sync_wrapped(*args, **kwargs):
            with tracer.start_as_current_span(f"langgraph.node:{node_name}") as span:
                span.set_attribute("langgraph.node", node_name)
                span.set_attribute("agent.name", node_name)
                span.set_attribute("agent.framework", "langgraph")
                span.set_attribute("agenttrace.kind", "agent_call")

                # Try to extract state from args
                if args:
                    span.set_attribute("agenttrace.input", serialize(args[0]))

                try:
                    result = action(*args, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return sync_wrapped


def is_instrumented() -> bool:
    """Check if LangGraph has been instrumented.

    Returns:
        True if instrumented, False otherwise
    """
    return _instrumented
