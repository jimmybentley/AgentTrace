"""Tests for framework-specific normalizers."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from agenttrace_ingestion.normalizers import (
    AutoGenNormalizer,
    CrewAINormalizer,
    GenericNormalizer,
    LangGraphNormalizer,
    get_normalizer,
)


@pytest.fixture
def mock_span():
    """Create a mock OTLP span."""
    span = Mock()
    span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    span.trace_id = b"\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20"
    span.parent_span_id = b"\x00\x00\x00\x00\x00\x00\x00\x00"
    span.name = "test_span"
    span.start_time_unix_nano = int(
        datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC).timestamp() * 1_000_000_000
    )
    span.end_time_unix_nano = int(
        datetime(2026, 1, 29, 12, 0, 1, tzinfo=UTC).timestamp() * 1_000_000_000
    )
    span.status = Mock(code=1, message="")
    span.attributes = []
    span.events = []
    return span


def create_attribute(key: str, value):
    """Helper to create mock OTLP attribute."""
    attr = Mock()
    attr.key = key
    attr.value = Mock()

    if isinstance(value, str):
        attr.value.HasField = lambda x: x == "string_value"
        attr.value.string_value = value
    elif isinstance(value, bool):
        attr.value.HasField = lambda x: x == "bool_value"
        attr.value.bool_value = value
    elif isinstance(value, int):
        attr.value.HasField = lambda x: x == "int_value"
        attr.value.int_value = value
    elif isinstance(value, float):
        attr.value.HasField = lambda x: x == "double_value"
        attr.value.double_value = value

    return attr


class TestLangGraphNormalizer:
    """Tests for LangGraphNormalizer."""

    def test_normalize_basic_span(self, mock_span):
        """Test basic span normalization."""
        mock_span.attributes = [
            create_attribute("langgraph.node", "Planner"),
            create_attribute("langgraph.step", 1),
        ]

        normalizer = LangGraphNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.span_id == "0102030405060708"
        assert result.name == "test_span"
        assert result.agent is not None
        assert result.agent.name == "Planner"
        assert result.agent.framework == "langgraph"

    def test_normalize_llm_call(self, mock_span):
        """Test LLM call span normalization."""
        mock_span.name = "llm_call"
        mock_span.attributes = [
            create_attribute("langgraph.node", "Coder"),
            create_attribute("gen_ai.request.model", "claude-3-opus-20240229"),
            create_attribute("gen_ai.usage.input_tokens", 100),
            create_attribute("gen_ai.usage.output_tokens", 50),
        ]

        normalizer = LangGraphNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.kind == "llm_call"
        assert result.model == "claude-3-opus-20240229"
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.cost_usd is not None  # Cost should be estimated

    def test_normalize_handoff(self, mock_span):
        """Test handoff/edge span normalization."""
        mock_span.name = "langgraph.edge"
        mock_span.attributes = [
            create_attribute("langgraph.source_node", "Planner"),
            create_attribute("langgraph.target_node", "Coder"),
        ]

        normalizer = LangGraphNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.kind == "handoff"
        assert len(result.messages) == 1
        assert result.messages[0].from_agent == "Planner"
        assert result.messages[0].to_agent == "Coder"
        assert result.messages[0].message_type == "handoff"


class TestAutoGenNormalizer:
    """Tests for AutoGenNormalizer."""

    def test_normalize_basic_span(self, mock_span):
        """Test basic AutoGen span normalization."""
        mock_span.attributes = [
            create_attribute("autogen.agent.name", "AssistantAgent"),
            create_attribute("autogen.agent.role", "assistant"),
        ]

        normalizer = AutoGenNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.agent is not None
        assert result.agent.name == "AssistantAgent"
        assert result.agent.role == "assistant"
        assert result.agent.framework == "autogen"

    def test_normalize_message(self, mock_span):
        """Test message extraction."""
        mock_span.attributes = [
            create_attribute("autogen.agent.name", "UserProxy"),
            create_attribute("autogen.message.sender", "UserProxy"),
            create_attribute("autogen.message.recipient", "AssistantAgent"),
            create_attribute("autogen.message.type", "request"),
        ]

        normalizer = AutoGenNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert len(result.messages) == 1
        assert result.messages[0].from_agent == "UserProxy"
        assert result.messages[0].to_agent == "AssistantAgent"
        assert result.messages[0].message_type == "request"


class TestCrewAINormalizer:
    """Tests for CrewAINormalizer."""

    def test_normalize_basic_span(self, mock_span):
        """Test basic CrewAI span normalization."""
        mock_span.attributes = [
            create_attribute("crewai.agent.name", "Researcher"),
            create_attribute("crewai.agent.role", "researcher"),
            create_attribute("crewai.crew.name", "ResearchCrew"),
            create_attribute("crewai.task.name", "gather_info"),
        ]

        normalizer = CrewAINormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.agent is not None
        assert result.agent.name == "Researcher"
        assert result.agent.role == "researcher"
        assert result.agent.framework == "crewai"
        assert result.agent.config["crew"] == "ResearchCrew"
        assert result.agent.config["task"] == "gather_info"


class TestGenericNormalizer:
    """Tests for GenericNormalizer."""

    def test_normalize_with_generic_attributes(self, mock_span):
        """Test generic normalization with standard OTEL attributes."""
        mock_span.attributes = [
            create_attribute("agent.name", "GenericAgent"),
            create_attribute("agent.role", "worker"),
        ]

        normalizer = GenericNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.agent is not None
        assert result.agent.name == "GenericAgent"
        assert result.agent.role == "worker"
        assert result.agent.framework == "generic"

    def test_normalize_fallback_to_resource(self, mock_span):
        """Test fallback to resource attributes."""
        resource_attrs = {"service.name": "MyService"}

        normalizer = GenericNormalizer()
        result = normalizer.normalize(mock_span, resource_attrs)

        assert result.agent is not None
        assert result.agent.name == "MyService"

    def test_infer_llm_call_kind(self, mock_span):
        """Test kind inference for LLM calls."""
        mock_span.name = "chat_completion"
        mock_span.attributes = [
            create_attribute("gen_ai.request.model", "gpt-4"),
        ]

        normalizer = GenericNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.kind == "llm_call"

    def test_infer_tool_call_kind(self, mock_span):
        """Test kind inference for tool calls."""
        mock_span.name = "execute_tool"

        normalizer = GenericNormalizer()
        result = normalizer.normalize(mock_span, {})

        assert result.kind == "tool_call"


class TestNormalizerFactory:
    """Tests for get_normalizer factory."""

    def test_get_langgraph_normalizer(self):
        """Test getting LangGraph normalizer."""
        normalizer = get_normalizer("langgraph")
        assert isinstance(normalizer, LangGraphNormalizer)

    def test_get_autogen_normalizer(self):
        """Test getting AutoGen normalizer."""
        normalizer = get_normalizer("autogen")
        assert isinstance(normalizer, AutoGenNormalizer)

    def test_get_crewai_normalizer(self):
        """Test getting CrewAI normalizer."""
        normalizer = get_normalizer("crewai")
        assert isinstance(normalizer, CrewAINormalizer)

    def test_get_generic_normalizer_fallback(self):
        """Test fallback to generic normalizer."""
        normalizer = get_normalizer("unknown_framework")
        assert isinstance(normalizer, GenericNormalizer)

    def test_get_normalizer_case_insensitive(self):
        """Test case-insensitive framework matching."""
        normalizer = get_normalizer("LangGraph")
        assert isinstance(normalizer, LangGraphNormalizer)
