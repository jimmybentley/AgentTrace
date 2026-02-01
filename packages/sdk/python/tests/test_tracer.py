"""Tests for AgentTracer class."""

import asyncio

import pytest

from agenttrace import AgentTracer


def test_tracer_initialization(test_config):
    """Test AgentTracer initialization."""
    tracer = AgentTracer(config=test_config)
    assert tracer.config.endpoint == "http://localhost:4318"
    assert tracer.config.service_name == "test-service"


def test_tracer_with_parameters():
    """Test AgentTracer with explicit parameters."""
    tracer = AgentTracer(endpoint="http://custom:4318", service_name="custom-service")
    assert tracer.config.endpoint == "http://custom:4318"
    assert tracer.config.service_name == "custom-service"


def test_tracer_disabled(disabled_config):
    """Test that tracer respects disabled configuration."""
    tracer = AgentTracer(config=disabled_config)

    # Decorators should return original functions when disabled
    @tracer.agent("TestAgent", role="test")
    def test_func():
        return "result"

    result = test_func()
    assert result == "result"


def test_agent_decorator_sync(test_config):
    """Test agent decorator with sync function."""
    tracer = AgentTracer(config=test_config)

    @tracer.agent("TestAgent", role="test", model="gpt-4")
    def plan(task: str) -> str:
        return f"Plan for: {task}"

    result = plan("test task")
    assert result == "Plan for: test task"


@pytest.mark.asyncio
async def test_agent_decorator_async(test_config):
    """Test agent decorator with async function."""
    tracer = AgentTracer(config=test_config)

    @tracer.agent("TestAgent", role="test", model="gpt-4")
    async def plan(task: str) -> str:
        await asyncio.sleep(0.01)
        return f"Plan for: {task}"

    result = await plan("test task")
    assert result == "Plan for: test task"


def test_tool_decorator_sync(test_config):
    """Test tool decorator with sync function."""
    tracer = AgentTracer(config=test_config)

    @tracer.tool("search")
    def search(query: str) -> list:
        return [f"Result for: {query}"]

    result = search("test")
    assert result == ["Result for: test"]


@pytest.mark.asyncio
async def test_tool_decorator_async(test_config):
    """Test tool decorator with async function."""
    tracer = AgentTracer(config=test_config)

    @tracer.tool("search")
    async def search(query: str) -> list:
        await asyncio.sleep(0.01)
        return [f"Result for: {query}"]

    result = await search("test")
    assert result == ["Result for: test"]


def test_trace_context_manager(test_config):
    """Test trace context manager."""
    tracer = AgentTracer(config=test_config)

    with tracer.trace("test-trace", metadata={"user_id": "123"}):
        # Code executes without error
        pass


def test_message_recording(test_config):
    """Test message recording."""
    tracer = AgentTracer(config=test_config)

    with tracer.trace("test-trace"):
        tracer.message("Agent1", "Agent2", {"data": "test"}, "handoff")
        # Should not raise an error


def test_checkpoint_recording(test_config):
    """Test checkpoint recording."""
    tracer = AgentTracer(config=test_config)

    with tracer.trace("test-trace"):
        tracer.checkpoint("test-checkpoint", {"state": "value"})
        # Should not raise an error


@pytest.mark.asyncio
async def test_error_handling(test_config):
    """Test error handling in decorated functions."""
    tracer = AgentTracer(config=test_config)

    @tracer.agent("ErrorAgent", role="test")
    async def failing_agent():
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        await failing_agent()
