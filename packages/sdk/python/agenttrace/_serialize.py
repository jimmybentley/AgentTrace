"""Serialization utilities for capturing inputs and outputs."""

import json
from typing import Any


def serialize(obj: Any, max_length: int = 10000) -> str:
    """Serialize an object to a JSON string for span attributes.

    Args:
        obj: Object to serialize
        max_length: Maximum length of serialized string

    Returns:
        JSON string representation of the object
    """
    try:
        # Try direct JSON serialization
        result = json.dumps(obj, default=_default_serializer)
    except (TypeError, ValueError):
        # Fallback to string representation
        result = str(obj)

    # Truncate if too long
    if len(result) > max_length:
        result = result[:max_length] + "... (truncated)"

    return result


def _default_serializer(obj: Any) -> Any:
    """Default serializer for non-JSON-serializable objects.

    Args:
        obj: Object to serialize

    Returns:
        Serializable representation
    """
    # Handle common types
    if hasattr(obj, "__dict__"):
        return {
            "__type__": obj.__class__.__name__,
            **{k: v for k, v in obj.__dict__.items() if not k.startswith("_")},
        }

    if hasattr(obj, "dict") and callable(obj.dict):
        # Pydantic models
        return obj.dict()

    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        # Pydantic v2 models
        return obj.model_dump()

    # Fallback to string
    return str(obj)


def truncate_string(s: str, max_length: int = 1000) -> str:
    """Truncate a string to a maximum length.

    Args:
        s: String to truncate
        max_length: Maximum length

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[:max_length] + "... (truncated)"
