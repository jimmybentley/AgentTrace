"""OTLP protocol parsing helpers."""

import json
from typing import Any

from google.protobuf.json_format import Parse
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)


def parse_otlp_request(body: bytes, content_type: str) -> ExportTraceServiceRequest:
    """
    Parse OTLP request from bytes.

    Args:
        body: Request body bytes
        content_type: Content-Type header value

    Returns:
        Parsed ExportTraceServiceRequest

    Raises:
        ValueError: If content type is unsupported or parsing fails
    """
    request = ExportTraceServiceRequest()

    if "protobuf" in content_type.lower():
        # Parse protobuf binary format
        try:
            request.ParseFromString(body)
        except Exception as e:
            raise ValueError(f"Failed to parse protobuf: {e}") from e

    elif "json" in content_type.lower():
        # Parse JSON format
        try:
            json_data = json.loads(body)
            Parse(json.dumps(json_data), request)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {e}") from e

    else:
        raise ValueError(f"Unsupported content type: {content_type}")

    return request


def extract_resource_attributes(resource: Any) -> dict[str, Any]:
    """
    Extract resource-level attributes from OTLP resource.

    Args:
        resource: OTLP Resource protobuf object

    Returns:
        Dictionary of resource attributes
    """
    result = {}

    if not resource or not hasattr(resource, "attributes"):
        return result

    for attr in resource.attributes:
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

    return result


def determine_framework(resource_attrs: dict[str, Any]) -> str:
    """
    Determine framework from resource attributes.

    Args:
        resource_attrs: Resource-level attributes

    Returns:
        Framework name (langgraph, autogen, crewai, or generic)
    """
    # Check for explicit framework attribute
    framework = resource_attrs.get("agent.framework", "").lower()
    if framework:
        return framework

    # Check service name for framework hints
    service_name = resource_attrs.get("service.name", "").lower()
    if "langgraph" in service_name:
        return "langgraph"
    if "autogen" in service_name:
        return "autogen"
    if "crewai" in service_name or "crew" in service_name:
        return "crewai"

    # Default to generic
    return "generic"
