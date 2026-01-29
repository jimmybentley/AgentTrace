"""Generic fallback normalizer for unknown frameworks."""

from typing import Any

from agenttrace_core.models import AgentInfo, NormalizedSpan

from .base import BaseNormalizer


class GenericNormalizer(BaseNormalizer):
    """
    Generic fallback normalizer for unknown frameworks.

    Attempts to extract agent information from common OTEL semantic conventions.
    """

    FRAMEWORK = "generic"

    def normalize(self, span: Any, resource_attrs: dict[str, Any]) -> NormalizedSpan:
        """Normalize a generic OTLP span."""
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

        # Try to extract agent information from common attributes
        agent_info = None
        agent_name = (
            attrs.get("agent.name")
            or attrs.get("agent.id")
            or resource_attrs.get("service.name")
        )

        if agent_name:
            agent_info = AgentInfo(
                name=agent_name,
                role=attrs.get("agent.role"),
                model=attrs.get("llm.model") or attrs.get("gen_ai.request.model"),
                framework=resource_attrs.get("agent.framework", self.FRAMEWORK),
            )

        # Determine span kind from name and attributes
        kind = self._infer_kind(span.name, attrs)

        return NormalizedSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=span.name,
            kind=kind,
            start_time=self._ns_to_datetime(span.start_time_unix_nano),
            end_time=(
                self._ns_to_datetime(span.end_time_unix_nano)
                if span.end_time_unix_nano
                else None
            ),
            status=self._map_status(span.status),
            agent=agent_info,
            model=attrs.get("llm.model") or attrs.get("gen_ai.request.model"),
            input_tokens=attrs.get("llm.token_count.prompt")
            or attrs.get("gen_ai.usage.input_tokens"),
            output_tokens=attrs.get("llm.token_count.completion")
            or attrs.get("gen_ai.usage.output_tokens"),
            attributes=attrs,
        )

    def _infer_kind(self, name: str, attrs: dict[str, Any]) -> str:
        """Infer span kind from name and attributes."""
        name_lower = name.lower()

        # Check for LLM calls
        if (
            "llm" in name_lower
            or "chat" in name_lower
            or "completion" in name_lower
            or attrs.get("gen_ai.operation.name")
        ):
            return "llm_call"

        # Check for tool calls
        if "tool" in name_lower or "function" in name_lower:
            return "tool_call"

        # Default to agent_message
        return "agent_message"
