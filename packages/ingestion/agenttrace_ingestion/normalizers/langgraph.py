"""LangGraph-specific normalizer."""

import json
from typing import Any

from agenttrace_core.models import AgentInfo, MessageInfo, NormalizedSpan

from .base import BaseNormalizer


class LangGraphNormalizer(BaseNormalizer):
    """
    Normalize LangGraph traces to AgentTrace format.

    LangGraph uses:
    - "langgraph.node" for agent names
    - "langgraph.step" for execution order
    - Parent-child relationships for subgraph calls
    - Edges represent handoffs between nodes
    """

    FRAMEWORK = "langgraph"

    def normalize(self, span: Any, resource_attrs: dict[str, Any]) -> NormalizedSpan:
        """Normalize a LangGraph OTLP span."""
        attrs = self._extract_attributes(span.attributes)

        # Extract basic span information
        span_id = span.span_id.hex() if hasattr(span.span_id, "hex") else str(span.span_id)
        trace_id = span.trace_id.hex() if hasattr(span.trace_id, "hex") else str(span.trace_id)
        parent_span_id = None
        if span.parent_span_id and span.parent_span_id != b"\x00" * 8:
            parent_span_id = (
                span.parent_span_id.hex()
                if hasattr(span.parent_span_id, "hex")
                else str(span.parent_span_id)
            )

        # Extract agent information
        agent_info = None
        if "langgraph.node" in attrs:
            agent_info = AgentInfo(
                name=attrs["langgraph.node"],
                role=attrs.get("langgraph.node_type", "unknown"),
                model=attrs.get("llm.model") or attrs.get("gen_ai.request.model"),
                framework=self.FRAMEWORK,
                config={
                    "step": attrs.get("langgraph.step"),
                    "thread_id": attrs.get("langgraph.thread_id"),
                },
            )

        # Extract inter-agent messages
        messages = []
        if span.name == "langgraph.edge" or "langgraph.edge" in span.name.lower():
            # This is a handoff between nodes
            messages.append(
                MessageInfo(
                    from_agent=attrs.get("langgraph.source_node"),
                    to_agent=attrs.get("langgraph.target_node"),
                    message_type="handoff",
                    content=self._safe_parse_json(attrs.get("langgraph.state", {})),
                    timestamp=self._ns_to_datetime(span.start_time_unix_nano),
                )
            )

        # Determine span kind
        kind = self._determine_kind(span, attrs)

        # Extract LLM-specific fields
        model = attrs.get("llm.model") or attrs.get("gen_ai.request.model")
        input_tokens = attrs.get("llm.token_count.prompt") or attrs.get("gen_ai.usage.input_tokens")
        output_tokens = attrs.get("llm.token_count.completion") or attrs.get(
            "gen_ai.usage.output_tokens"
        )

        # Calculate cost if we have token information and model
        cost_usd = self._estimate_cost(model, input_tokens, output_tokens)

        # Extract input/output content
        input_content = self._extract_input(attrs)
        output_content = self._extract_output(attrs)
        error_content = self._extract_error(span)

        return NormalizedSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=span.name,
            kind=kind,
            start_time=self._ns_to_datetime(span.start_time_unix_nano),
            end_time=(
                self._ns_to_datetime(span.end_time_unix_nano) if span.end_time_unix_nano else None
            ),
            status=self._map_status(span.status),
            agent=agent_info,
            messages=messages,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            input=input_content,
            output=output_content,
            error=error_content,
            attributes=attrs,
        )

    def _determine_kind(self, span: Any, attrs: dict[str, Any]) -> str:
        """Determine the span kind from name and attributes."""
        name_lower = span.name.lower()

        # Check for LLM calls
        if (
            "llm" in name_lower
            or "chat" in name_lower
            or attrs.get("gen_ai.operation.name") == "chat"
        ):
            return "llm_call"

        # Check for tool calls
        if "tool" in name_lower or attrs.get("langgraph.node_type") == "tool":
            return "tool_call"

        # Check for edges/handoffs
        if "edge" in name_lower or "handoff" in name_lower:
            return "handoff"

        # Check for checkpoints
        if "checkpoint" in name_lower or attrs.get("langgraph.checkpoint_id"):
            return "checkpoint"

        # Default to agent_message for node executions
        if "langgraph.node" in attrs:
            return "agent_message"

        return "agent_message"

    def _safe_parse_json(self, value: Any) -> dict[str, Any]:
        """Safely parse JSON string or return dict."""
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {"raw": value}
        return {}

    def _extract_input(self, attrs: dict[str, Any]) -> dict[str, Any] | None:
        """Extract input content from attributes."""
        input_data = {}

        # Try various LLM input attributes
        if "llm.prompts" in attrs:
            input_data["prompts"] = self._safe_parse_json(attrs["llm.prompts"])
        if "gen_ai.prompt" in attrs:
            input_data["prompt"] = attrs["gen_ai.prompt"]
        if "langgraph.input" in attrs:
            input_data["input"] = self._safe_parse_json(attrs["langgraph.input"])

        return input_data if input_data else None

    def _extract_output(self, attrs: dict[str, Any]) -> dict[str, Any] | None:
        """Extract output content from attributes."""
        output_data = {}

        # Try various LLM output attributes
        if "llm.completions" in attrs:
            output_data["completions"] = self._safe_parse_json(attrs["llm.completions"])
        if "gen_ai.completion" in attrs:
            output_data["completion"] = attrs["gen_ai.completion"]
        if "langgraph.output" in attrs:
            output_data["output"] = self._safe_parse_json(attrs["langgraph.output"])

        return output_data if output_data else None

    def _extract_error(self, span: Any) -> dict[str, Any] | None:
        """Extract error information from span."""
        if not span.status or span.status.code != 2:  # Not an error
            return None

        error_data = {"message": span.status.message if span.status.message else "Unknown error"}

        # Look for exception events
        for event in span.events:
            if event.name == "exception":
                attrs = self._extract_attributes(event.attributes)
                error_data.update(
                    {
                        "type": attrs.get("exception.type"),
                        "message": attrs.get("exception.message"),
                        "stacktrace": attrs.get("exception.stacktrace"),
                    }
                )
                break

        return error_data

    def _estimate_cost(
        self, model: str | None, input_tokens: int | None, output_tokens: int | None
    ) -> float | None:
        """Estimate cost based on model and token counts."""
        if not model or not input_tokens or not output_tokens:
            return None

        # Simplified cost estimation (actual costs vary)
        # This should be made configurable in production
        cost_per_1k = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        }

        # Find matching model
        model_lower = model.lower()
        for model_key, prices in cost_per_1k.items():
            if model_key in model_lower:
                input_cost = (input_tokens / 1000) * prices["input"]
                output_cost = (output_tokens / 1000) * prices["output"]
                return round(input_cost + output_cost, 6)

        return None
