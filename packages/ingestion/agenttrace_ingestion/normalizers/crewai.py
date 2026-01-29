"""CrewAI-specific normalizer."""

from typing import Any

from agenttrace_core.models import AgentInfo, NormalizedSpan

from .base import BaseNormalizer


class CrewAINormalizer(BaseNormalizer):
    """
    Normalize CrewAI traces to AgentTrace format.

    CrewAI uses:
    - Crew and agent hierarchies
    - Task assignments to agents
    - Sequential and hierarchical execution patterns
    """

    FRAMEWORK = "crewai"

    def normalize(self, span: Any, resource_attrs: dict[str, Any]) -> NormalizedSpan:
        """Normalize a CrewAI OTLP span."""
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
        agent_name = attrs.get("crewai.agent.name") or attrs.get("agent.name")
        if agent_name:
            agent_info = AgentInfo(
                name=agent_name,
                role=attrs.get("crewai.agent.role") or attrs.get("agent.role"),
                model=attrs.get("llm.model") or attrs.get("gen_ai.request.model"),
                framework=self.FRAMEWORK,
                config={
                    "crew": attrs.get("crewai.crew.name"),
                    "task": attrs.get("crewai.task.name"),
                },
            )

        # Determine span kind
        kind = "agent_message"
        if "task" in span.name.lower():
            kind = "agent_message"
        elif "llm" in span.name.lower() or attrs.get("gen_ai.operation.name"):
            kind = "llm_call"
        elif "tool" in span.name.lower():
            kind = "tool_call"

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
            input_tokens=attrs.get("gen_ai.usage.input_tokens"),
            output_tokens=attrs.get("gen_ai.usage.output_tokens"),
            attributes=attrs,
        )
