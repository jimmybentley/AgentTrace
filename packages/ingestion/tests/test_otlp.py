"""Tests for OTLP parsing helpers."""

import json
from unittest.mock import Mock

import pytest

from agenttrace_ingestion.otlp import (
    determine_framework,
    extract_resource_attributes,
    parse_otlp_request,
)


class TestExtractResourceAttributes:
    """Tests for extract_resource_attributes."""

    def test_extract_string_attribute(self):
        """Test extracting string attribute."""
        resource = Mock()
        attr = Mock()
        attr.key = "service.name"
        attr.value = Mock()
        attr.value.HasField = lambda x: x == "string_value"
        attr.value.string_value = "MyService"
        resource.attributes = [attr]

        result = extract_resource_attributes(resource)

        assert result["service.name"] == "MyService"

    def test_extract_int_attribute(self):
        """Test extracting integer attribute."""
        resource = Mock()
        attr = Mock()
        attr.key = "service.instance.id"
        attr.value = Mock()
        attr.value.HasField = lambda x: x == "int_value"
        attr.value.int_value = 42
        resource.attributes = [attr]

        result = extract_resource_attributes(resource)

        assert result["service.instance.id"] == 42

    def test_extract_bool_attribute(self):
        """Test extracting boolean attribute."""
        resource = Mock()
        attr = Mock()
        attr.key = "agent.enabled"
        attr.value = Mock()
        attr.value.HasField = lambda x: x == "bool_value"
        attr.value.bool_value = True
        resource.attributes = [attr]

        result = extract_resource_attributes(resource)

        assert result["agent.enabled"] is True

    def test_extract_multiple_attributes(self):
        """Test extracting multiple attributes."""
        resource = Mock()
        attrs = []

        # String attribute
        attr1 = Mock()
        attr1.key = "service.name"
        attr1.value = Mock()
        attr1.value.HasField = lambda x: x == "string_value"
        attr1.value.string_value = "TestService"
        attrs.append(attr1)

        # Int attribute
        attr2 = Mock()
        attr2.key = "version"
        attr2.value = Mock()
        attr2.value.HasField = lambda x: x == "int_value"
        attr2.value.int_value = 1
        attrs.append(attr2)

        resource.attributes = attrs

        result = extract_resource_attributes(resource)

        assert len(result) == 2
        assert result["service.name"] == "TestService"
        assert result["version"] == 1

    def test_extract_no_attributes(self):
        """Test extracting from resource with no attributes."""
        resource = Mock()
        resource.attributes = []

        result = extract_resource_attributes(resource)

        assert result == {}

    def test_extract_none_resource(self):
        """Test extracting from None resource."""
        result = extract_resource_attributes(None)

        assert result == {}


class TestDetermineFramework:
    """Tests for determine_framework."""

    def test_explicit_framework_attribute(self):
        """Test explicit framework attribute."""
        attrs = {"agent.framework": "langgraph"}

        result = determine_framework(attrs)

        assert result == "langgraph"

    def test_framework_from_service_name_langgraph(self):
        """Test framework detection from service name (LangGraph)."""
        attrs = {"service.name": "my-langgraph-app"}

        result = determine_framework(attrs)

        assert result == "langgraph"

    def test_framework_from_service_name_autogen(self):
        """Test framework detection from service name (AutoGen)."""
        attrs = {"service.name": "autogen-agents"}

        result = determine_framework(attrs)

        assert result == "autogen"

    def test_framework_from_service_name_crewai(self):
        """Test framework detection from service name (CrewAI)."""
        attrs = {"service.name": "my-crew-app"}

        result = determine_framework(attrs)

        assert result == "crewai"

    def test_default_to_generic(self):
        """Test default to generic framework."""
        attrs = {"service.name": "unknown-service"}

        result = determine_framework(attrs)

        assert result == "generic"

    def test_empty_attributes(self):
        """Test with empty attributes."""
        result = determine_framework({})

        assert result == "generic"

    def test_case_insensitive_detection(self):
        """Test case-insensitive framework detection."""
        attrs = {"service.name": "MyLangGraphApp"}

        result = determine_framework(attrs)

        assert result == "langgraph"


class TestParseOTLPRequest:
    """Tests for parse_otlp_request."""

    def test_parse_json_request(self):
        """Test parsing JSON OTLP request."""
        # Simple JSON request
        json_data = {"resourceSpans": []}
        body = json.dumps(json_data).encode()

        result = parse_otlp_request(body, "application/json")

        assert result is not None
        assert len(result.resource_spans) == 0

    def test_unsupported_content_type(self):
        """Test unsupported content type raises ValueError."""
        body = b"some data"

        with pytest.raises(ValueError, match="Unsupported content type"):
            parse_otlp_request(body, "text/plain")

    def test_invalid_json_raises_error(self):
        """Test invalid JSON raises ValueError."""
        body = b"not valid json"

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            parse_otlp_request(body, "application/json")

    def test_content_type_case_insensitive(self):
        """Test content type matching is case-insensitive."""
        json_data = {"resourceSpans": []}
        body = json.dumps(json_data).encode()

        # Should work with uppercase
        result = parse_otlp_request(body, "APPLICATION/JSON")

        assert result is not None
