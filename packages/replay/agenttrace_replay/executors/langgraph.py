"""LangGraph-specific executor.

This executor knows how to re-execute LangGraph nodes from checkpointed state.
It handles LangGraph's state management and graph structure.

Note: This is a simplified implementation for V1. Full LangGraph support would
require deeper integration with LangGraph's checkpoint system.
"""

from typing import Any


async def langgraph_executor(
    input: dict[str, Any],
    state: dict[str, Any],
    config: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> Any:
    """Execute a LangGraph node from checkpointed state.

    This executor attempts to reconstruct and re-execute a LangGraph node.
    For V1, this is simplified and may not work for all LangGraph patterns.

    Args:
        input: Input to the agent (potentially modified)
        state: Checkpointed state containing:
            - input: Original input
            - output: Original output
            - prior_output: Output from previous span
            - agent_config: Agent configuration
            - span_kind: Type of span
            - span_name: Name of the span
        config: Agent configuration:
            - name: Agent name
            - model: LLM model
            - framework: Should be "langgraph"
            - config: Framework-specific config
        overrides: Optional overrides (model, temperature, etc.)

    Returns:
        Output from re-executing the node

    Raises:
        ImportError: If LangGraph is not installed
        ValueError: If graph configuration is invalid
    """
    try:
        import langgraph  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "LangGraph is not installed. Install with: pip install langgraph"
        ) from e

    # For V1, we'll use a simplified approach:
    # Instead of trying to reconstruct the entire graph, we'll focus on
    # re-executing just the node that was checkpointed.

    span_name = state.get("span_name", "")

    # Extract the node name from the span name
    # LangGraph spans are typically named like "langgraph.node:NodeName"
    node_name = span_name.split(":")[-1] if ":" in span_name else span_name

    # Get LangGraph-specific config
    graph_config = config.get("config", {}).get("graph_config", {})

    # Build the state dict for LangGraph
    # LangGraph nodes typically receive the full state dict
    lg_state = {
        **input,  # Modified input
        **state.get("prior_output", {}),  # Context from previous nodes
    }

    # Apply overrides to config
    if overrides:
        if "model" in overrides:
            graph_config["model"] = overrides["model"]
        if "temperature" in overrides:
            graph_config["temperature"] = overrides.get("temperature")

    # For V1, we'll return a simplified result that indicates we would re-execute
    # In V2, we would actually invoke the node here
    #
    # To actually re-execute, we would need:
    # 1. The graph definition (stored in checkpoint or retrievable)
    # 2. The node function/callable
    # 3. Proper state reconstruction
    #
    # Example of what V2 might look like:
    # if graph_definition := state.get("graph_definition"):
    #     graph = reconstruct_graph(graph_definition)
    #     result = await graph.nodes[node_name](lg_state, config=graph_config)
    #     return result

    # For now, return a note that this is a simplified implementation
    return {
        "note": "LangGraph executor V1: Simplified implementation",
        "node_name": node_name,
        "framework": "langgraph",
        "state": lg_state,
        "config_applied": graph_config,
        "original_output": state.get("output"),
        "message": (
            f"Would re-execute LangGraph node '{node_name}' with state: {lg_state}. "
            "Full re-execution requires V2 implementation with graph reconstruction."
        ),
    }


# Helper function for V2 implementation
def _reconstruct_graph(graph_definition: dict) -> Any:
    """Reconstruct a LangGraph graph from its definition.

    This would be implemented in V2 to support full graph reconstruction.
    """
    raise NotImplementedError("Graph reconstruction not yet implemented")
