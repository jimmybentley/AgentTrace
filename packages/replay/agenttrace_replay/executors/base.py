"""Base protocol for agent executors.

This module defines the interface that all framework-specific executors
must implement.
"""

from typing import Any, Protocol


class AgentExecutor(Protocol):
    """Protocol for framework-specific agent executors.

    An executor is responsible for re-executing agent code from a
    checkpointed state. Different frameworks have different ways of
    representing and executing agent code, so we need framework-specific
    implementations.

    The executor receives:
    - input: The input to the agent (potentially modified from original)
    - state: The checkpointed state including prior context
    - config: Agent configuration (model, temperature, etc.)
    - overrides: Optional runtime overrides for config

    And returns:
    - The output from re-executing the agent
    """

    async def __call__(
        self,
        input: dict[str, Any],
        state: dict[str, Any],
        config: dict[str, Any],
        overrides: dict[str, Any] | None = None,
    ) -> Any:
        """Execute the agent from checkpointed state.

        Args:
            input: Input to the agent (may be modified from original)
            state: Checkpointed state containing:
                - input: Original input
                - output: Original output (for reference)
                - prior_output: Output from previous span in the trace
                - agent_config: Agent configuration
                - span_kind: Type of span (llm_call, tool_call, etc.)
                - span_name: Name of the span
            config: Agent configuration:
                - name: Agent name
                - role: Agent role
                - model: LLM model
                - framework: Framework name
                - config: Framework-specific config
            overrides: Optional overrides for config:
                - model: Override model
                - temperature: Override temperature
                - max_tokens: Override max tokens
                - etc.

        Returns:
            The output from re-executing the agent

        Raises:
            Exception: If re-execution fails
        """
        ...
