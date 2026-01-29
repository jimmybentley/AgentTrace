"""Tests for core data models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from agenttrace_core.models import Agent, Span, Trace


def test_trace_creation():
    """Test that a Trace can be created with required fields."""
    trace = Trace(
        name="test_trace",
        start_time=datetime.utcnow(),
    )

    assert isinstance(trace.trace_id, UUID)
    assert trace.name == "test_trace"
    assert trace.status == "running"
    assert isinstance(trace.metadata, dict)
    assert trace.created_at is not None


def test_agent_creation():
    """Test that an Agent can be created with required fields."""
    trace_id = uuid4()
    agent = Agent(
        trace_id=trace_id,
        name="Planner",
        role="planner",
        model="claude-3-opus-20240229",
        framework="langgraph",
    )

    assert isinstance(agent.agent_id, UUID)
    assert agent.trace_id == trace_id
    assert agent.name == "Planner"
    assert agent.role == "planner"
    assert agent.model == "claude-3-opus-20240229"
    assert agent.framework == "langgraph"


def test_span_creation():
    """Test that a Span can be created with required fields."""
    trace_id = uuid4()
    agent_id = uuid4()
    span = Span(
        trace_id=trace_id,
        agent_id=agent_id,
        name="llm_call",
        kind="llm_call",
        start_time=datetime.utcnow(),
    )

    assert isinstance(span.span_id, UUID)
    assert span.trace_id == trace_id
    assert span.agent_id == agent_id
    assert span.name == "llm_call"
    assert span.kind == "llm_call"
    assert span.status == "ok"


def test_span_with_tokens_and_cost():
    """Test that a Span can store token counts and cost."""
    trace_id = uuid4()
    span = Span(
        trace_id=trace_id,
        name="llm_call",
        kind="llm_call",
        start_time=datetime.utcnow(),
        model="claude-3-opus-20240229",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.0045"),
    )

    assert span.model == "claude-3-opus-20240229"
    assert span.input_tokens == 100
    assert span.output_tokens == 50
    assert span.cost_usd == Decimal("0.0045")


def test_trace_serialization():
    """Test that Trace can be serialized to dict/JSON."""
    trace = Trace(
        name="test_trace",
        start_time=datetime.utcnow(),
        status="completed",
        total_tokens=150,
    )

    trace_dict = trace.model_dump()

    assert trace_dict["name"] == "test_trace"
    assert trace_dict["status"] == "completed"
    assert trace_dict["total_tokens"] == 150


def test_agent_with_config():
    """Test that Agent can store configuration."""
    trace_id = uuid4()
    agent = Agent(
        trace_id=trace_id,
        name="Coder",
        role="coder",
        config={
            "temperature": 0.7,
            "max_tokens": 2000,
            "tools": ["python_repl", "bash"],
        },
    )

    assert agent.config["temperature"] == 0.7
    assert agent.config["max_tokens"] == 2000
    assert "python_repl" in agent.config["tools"]
