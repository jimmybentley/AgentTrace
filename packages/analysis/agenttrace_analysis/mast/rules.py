"""Rule-based failure classification using MAST taxonomy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .taxonomy import FailureCategory


@dataclass
class ClassificationResult:
    """Result of failure classification for a span or trace."""

    failure_mode: str
    category: FailureCategory
    confidence: float  # 0.0 - 1.0
    reasoning: str

    # Optional: specific span or agent that failed
    span_id: str | None = None
    agent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "failure_mode": self.failure_mode,
            "category": self.category.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "span_id": self.span_id,
            "agent_id": self.agent_id,
        }


class RuleBasedClassifier:
    """Rule-based classifier for detecting failure patterns in traces."""

    def __init__(self):
        """Initialize classifier."""
        self.rules = [
            self._check_infinite_loop,
            self._check_handoff_failure,
            self._check_resource_contention,
            self._check_format_error,
            self._check_timeout_pattern,
        ]

    def classify(
        self,
        trace: dict[str, Any],
        spans: list[dict[str, Any]],
        agents: dict[str, dict[str, Any]],
    ) -> list[ClassificationResult]:
        """
        Classify failures in a trace.

        Args:
            trace: Trace metadata (trace_id, status, etc.)
            spans: List of span dictionaries
            agents: Dictionary mapping agent_id to agent metadata

        Returns:
            List of classification results (may be empty if no failures detected)
        """
        results = []

        # Run all detection rules
        for rule in self.rules:
            rule_results = rule(trace, spans, agents)
            results.extend(rule_results)

        return results

    def _check_infinite_loop(
        self,
        trace: dict[str, Any],
        spans: list[dict[str, Any]],
        agents: dict[str, dict[str, Any]],
    ) -> list[ClassificationResult]:
        """
        Detect infinite loops: same agent called >3x with similar inputs.

        Pattern: Multiple consecutive spans from same agent with similar input content.
        """
        results = []

        # Group spans by agent
        agent_spans: dict[str, list[dict]] = {}
        for span in spans:
            agent_id = span.get("agent_id")
            if agent_id:
                if agent_id not in agent_spans:
                    agent_spans[agent_id] = []
                agent_spans[agent_id].append(span)

        # Check each agent for repeated calls with similar inputs
        for agent_id, agent_span_list in agent_spans.items():
            # Sort by start time
            sorted_spans = sorted(
                agent_span_list, key=lambda s: s.get("start_time") or datetime.min
            )

            # Look for sequences of similar inputs
            for i in range(len(sorted_spans) - 3):
                window = sorted_spans[i : i + 4]

                # Check if inputs are similar (simple heuristic: same keys and similar values)
                inputs = [self._normalize_input(s.get("input")) for s in window]

                if self._are_inputs_similar(inputs):
                    # Found potential infinite loop
                    agent_name = agents.get(agent_id, {}).get("name", agent_id)
                    results.append(
                        ClassificationResult(
                            failure_mode="infinite_loop",
                            category=FailureCategory.COORDINATION,
                            confidence=0.85,
                            reasoning=f"Agent '{agent_name}' executed 4+ times with similar inputs, indicating potential infinite loop",
                            span_id=window[-1].get("span_id"),
                            agent_id=agent_id,
                        )
                    )
                    break  # Only report once per agent

        return results

    def _check_handoff_failure(
        self,
        trace: dict[str, Any],
        spans: list[dict[str, Any]],
        agents: dict[str, dict[str, Any]],
    ) -> list[ClassificationResult]:
        """
        Detect handoff failures: agent errors immediately after receiving handoff.

        Pattern: Message from agent A to agent B, followed by error in agent B's next span.
        """
        results = []

        # Sort spans by start time
        sorted_spans = sorted(spans, key=lambda s: s.get("start_time") or datetime.min)

        # Look for handoff patterns (kind="handoff" or message in attributes)
        for i in range(len(sorted_spans) - 1):
            current = sorted_spans[i]
            next_span = sorted_spans[i + 1]

            # Check if current span is a handoff
            is_handoff = current.get("kind") == "handoff"
            attributes = current.get("attributes") or {}
            to_agent = attributes.get("message.to_agent")

            if is_handoff or to_agent:
                # Check if next span is from the receiving agent and has error
                next_agent = next_span.get("agent_id")
                next_status = next_span.get("status")

                if next_agent == to_agent and next_status == "error":
                    agent_name = agents.get(next_agent, {}).get("name", next_agent)
                    results.append(
                        ClassificationResult(
                            failure_mode="handoff_failure",
                            category=FailureCategory.COORDINATION,
                            confidence=0.9,
                            reasoning=f"Agent '{agent_name}' failed immediately after receiving handoff",
                            span_id=next_span.get("span_id"),
                            agent_id=next_agent,
                        )
                    )

        return results

    def _check_resource_contention(
        self,
        trace: dict[str, Any],
        spans: list[dict[str, Any]],
        agents: dict[str, dict[str, Any]],
    ) -> list[ClassificationResult]:
        """
        Detect resource contention: multiple agents calling same tool simultaneously.

        Pattern: Overlapping time windows for tool_call spans with same tool name.
        """
        results = []

        # Find all tool call spans
        tool_calls = [
            span
            for span in spans
            if span.get("kind") == "tool_call" or span.get("name", "").startswith("tool.")
        ]

        # Group by tool name
        tool_groups: dict[str, list[dict]] = {}
        for span in tool_calls:
            tool_name = span.get("name", "")
            if tool_name:
                if tool_name not in tool_groups:
                    tool_groups[tool_name] = []
                tool_groups[tool_name].append(span)

        # Check for temporal overlap within each tool group
        for tool_name, tool_span_list in tool_groups.items():
            if len(tool_span_list) < 2:
                continue

            # Check each pair for overlap
            for i in range(len(tool_span_list)):
                for j in range(i + 1, len(tool_span_list)):
                    span1 = tool_span_list[i]
                    span2 = tool_span_list[j]

                    if self._spans_overlap(span1, span2):
                        agent1_id = span1.get("agent_id")
                        agent2_id = span2.get("agent_id")

                        # Different agents accessing same resource
                        if agent1_id != agent2_id:
                            agent1_name = agents.get(agent1_id, {}).get("name", agent1_id)
                            agent2_name = agents.get(agent2_id, {}).get("name", agent2_id)

                            results.append(
                                ClassificationResult(
                                    failure_mode="resource_contention",
                                    category=FailureCategory.COORDINATION,
                                    confidence=0.75,
                                    reasoning=f"Agents '{agent1_name}' and '{agent2_name}' simultaneously accessed tool '{tool_name}'",
                                    span_id=span2.get("span_id"),
                                    agent_id=agent2_id,
                                )
                            )

        return results

    def _check_format_error(
        self,
        trace: dict[str, Any],
        spans: list[dict[str, Any]],
        agents: dict[str, dict[str, Any]],
    ) -> list[ClassificationResult]:
        """
        Detect message format errors: error messages containing format-related keywords.

        Pattern: Error status with message containing "json", "parse", "schema", "format", "validation".
        """
        results = []

        format_keywords = [
            "json",
            "parse",
            "schema",
            "format",
            "validation",
            "serialize",
            "deserialize",
        ]

        for span in spans:
            if span.get("status") != "error":
                continue

            # Check error message
            error_msg = span.get("error_message", "").lower()
            output = span.get("output") or {}
            if isinstance(output, dict):
                output_str = json.dumps(output).lower()
            else:
                output_str = str(output).lower()

            # Look for format-related keywords
            found_keywords = []
            for keyword in format_keywords:
                if keyword in error_msg or keyword in output_str:
                    found_keywords.append(keyword)

            if found_keywords:
                agent_id = span.get("agent_id")
                agent_name = agents.get(agent_id, {}).get("name", agent_id or "unknown")

                results.append(
                    ClassificationResult(
                        failure_mode="message_format_error",
                        category=FailureCategory.COORDINATION,
                        confidence=0.8,
                        reasoning=f"Agent '{agent_name}' encountered format error (keywords: {', '.join(found_keywords)})",
                        span_id=span.get("span_id"),
                        agent_id=agent_id,
                    )
                )

        return results

    def _check_timeout_pattern(
        self,
        trace: dict[str, Any],
        spans: list[dict[str, Any]],
        agents: dict[str, dict[str, Any]],
    ) -> list[ClassificationResult]:
        """
        Detect timeout failures: spans with status="timeout".

        Pattern: Status field explicitly set to timeout.
        """
        results = []

        for span in spans:
            if span.get("status") == "timeout":
                agent_id = span.get("agent_id")
                agent_name = agents.get(agent_id, {}).get("name", agent_id or "unknown")

                # Calculate span duration
                start = span.get("start_time")
                end = span.get("end_time")
                duration_ms = 0.0
                if start and end:
                    duration_ms = (end - start).total_seconds() * 1000

                results.append(
                    ClassificationResult(
                        failure_mode="timeout",
                        category=FailureCategory.VERIFICATION,
                        confidence=0.95,
                        reasoning=f"Agent '{agent_name}' execution timed out after {duration_ms:.0f}ms",
                        span_id=span.get("span_id"),
                        agent_id=agent_id,
                    )
                )

        return results

    # Helper methods

    def _normalize_input(self, input_data: Any) -> str:
        """Normalize input for comparison."""
        if input_data is None:
            return ""
        if isinstance(input_data, dict):
            return json.dumps(input_data, sort_keys=True)
        return str(input_data)

    def _are_inputs_similar(self, inputs: list[str], threshold: float = 0.9) -> bool:
        """Check if inputs are similar (simple string comparison)."""
        if not inputs or len(inputs) < 2:
            return False

        # Simple heuristic: check if all inputs are identical or very similar
        first = inputs[0]
        similar_count = sum(1 for inp in inputs if inp == first)

        return similar_count >= len(inputs) * threshold

    def _spans_overlap(self, span1: dict, span2: dict) -> bool:
        """Check if two spans have overlapping time windows."""
        start1 = span1.get("start_time")
        end1 = span1.get("end_time")
        start2 = span2.get("start_time")
        end2 = span2.get("end_time")

        if not all([start1, end1, start2, end2]):
            return False

        # Spans overlap if one starts before the other ends
        return start1 < end2 and start2 < end1
