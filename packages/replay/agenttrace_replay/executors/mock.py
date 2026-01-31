"""Mock executor for testing and dry runs.

This executor doesn't actually call any LLMs or execute real code.
Instead, it returns a predictable mock output based on the input.

Useful for:
- Testing the replay flow without LLM costs
- Dry runs to validate checkpoint restoration
- Unit testing replay logic
"""

from typing import Any


async def mock_executor(
    input: dict[str, Any],
    state: dict[str, Any],
    config: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> Any:
    """Mock executor that returns a predictable output.

    The mock executor constructs a response that echoes the input
    and includes markers indicating this is a mock execution.

    Args:
        input: Input to the agent
        state: Checkpointed state
        config: Agent configuration
        overrides: Optional overrides

    Returns:
        Mock output dictionary
    """
    agent_name = config.get("name", "unknown")
    span_kind = state.get("span_kind", "unknown")

    # Build mock response
    response = {
        "mock": True,
        "agent": agent_name,
        "span_kind": span_kind,
        "input_echo": input,
        "message": f"Mock execution of {agent_name} ({span_kind})",
    }

    # Include override information if present
    if overrides:
        response["overrides_applied"] = overrides

    # For different span kinds, tailor the response
    if span_kind == "llm_call":
        response["content"] = f"Mock LLM response to: {input.get('query', input.get('prompt', 'unknown'))}"
        response["model"] = overrides.get("model") if overrides else config.get("model", "mock-model")
        response["tokens"] = {"input": 10, "output": 20}

    elif span_kind == "tool_call":
        response["tool_result"] = f"Mock tool result for: {input}"
        response["success"] = True

    elif span_kind == "handoff":
        response["handoff_to"] = state.get("agent_config", {}).get("name", "next-agent")
        response["context"] = input

    else:
        response["output"] = f"Mock output for {span_kind}"

    return response
