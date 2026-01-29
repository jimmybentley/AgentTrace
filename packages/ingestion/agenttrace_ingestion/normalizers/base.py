"""Base normalizer class for framework-specific normalization."""

from typing import Any

from agenttrace_core.models import NormalizedSpan


class BaseNormalizer:
    """
    Base class for framework-specific normalizers.

    Each normalizer extracts agent information and inter-agent messages
    from OTLP spans based on framework-specific semantic conventions.
    """

    FRAMEWORK: str = "unknown"

    def normalize(self, span: Any, resource_attrs: dict[str, Any]) -> NormalizedSpan:
        """
        Normalize an OTLP span to AgentTrace format.

        Args:
            span: OTLP span protobuf object
            resource_attrs: Resource-level attributes from OTLP

        Returns:
            NormalizedSpan with extracted agent and message information
        """
        raise NotImplementedError(
            f"Normalizer for framework '{self.FRAMEWORK}' must implement normalize()"
        )

    def _extract_attributes(self, attributes: Any) -> dict[str, Any]:
        """Extract attributes from OTLP format to dict."""
        result = {}
        if not attributes:
            return result

        for attr in attributes:
            key = attr.key
            value = attr.value

            # Extract value based on which field is set
            if value.HasField("string_value"):
                result[key] = value.string_value
            elif value.HasField("bool_value"):
                result[key] = value.bool_value
            elif value.HasField("int_value"):
                result[key] = value.int_value
            elif value.HasField("double_value"):
                result[key] = value.double_value
            elif value.HasField("array_value"):
                # Convert array to list
                result[key] = [self._extract_any_value(v) for v in value.array_value.values]
            elif value.HasField("kvlist_value"):
                # Convert kvlist to dict
                result[key] = self._extract_attributes(value.kvlist_value.values)

        return result

    def _extract_any_value(self, value: Any) -> Any:
        """Extract value from AnyValue protobuf."""
        if value.HasField("string_value"):
            return value.string_value
        elif value.HasField("bool_value"):
            return value.bool_value
        elif value.HasField("int_value"):
            return value.int_value
        elif value.HasField("double_value"):
            return value.double_value
        return None

    def _map_status(self, status: Any) -> str:
        """Map OTLP status to AgentTrace status."""
        if not status:
            return "ok"

        # OTLP status codes: OK = 1, ERROR = 2
        if status.code == 2:
            return "error"
        return "ok"

    def _ns_to_datetime(self, ns: int):
        """Convert nanoseconds timestamp to datetime."""
        from datetime import datetime, timezone

        return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
