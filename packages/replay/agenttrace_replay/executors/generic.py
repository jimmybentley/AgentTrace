"""Generic fallback executor.

This executor is used when no framework-specific executor is available.
It doesn't actually re-execute the agent; instead, it returns the original
output from the checkpoint.

This is useful for:
- "What-if" analysis without actual re-execution
- Frameworks that don't yet have a specific executor
- Cases where re-execution isn't possible but we still want to analyze the replay flow
"""

from typing import Any


async def generic_executor(
    input: dict[str, Any],
    state: dict[str, Any],
    config: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> Any:
    """Generic executor that returns the original output.

    This executor doesn't perform actual re-execution. Instead, it:
    1. Returns the original output from the checkpoint state
    2. If input was modified, it annotates that the output may not reflect changes
    3. Optionally applies simple transformations if overrides are present

    Args:
        input: Input to the agent (potentially modified)
        state: Checkpointed state containing original output
        config: Agent configuration
        overrides: Optional overrides

    Returns:
        The original output, possibly with annotations
    """
    original_output = state.get("output", {})
    original_input = state.get("input", {})

    # Check if input was modified
    input_modified = input != original_input

    # If input wasn't modified and no overrides, just return original output
    if not input_modified and not overrides:
        return original_output

    # Otherwise, return output with annotations
    result = {
        "output": original_output,
        "note": "Generic executor: returned original output without re-execution",
    }

    if input_modified:
        result["warning"] = (
            "Input was modified but agent was not re-executed. Output may not reflect changes."
        )
        result["input_changes"] = {
            "original": original_input,
            "modified": input,
        }

    if overrides:
        result["overrides_ignored"] = overrides
        result["warning"] = (
            result.get("warning", "")
            + " Overrides were specified but not applied (no re-execution)."
        )

    return result
