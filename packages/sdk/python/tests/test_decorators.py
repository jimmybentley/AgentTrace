"""Tests for standalone decorators."""

import asyncio

import pytest

from agenttrace.decorators import agent, tool, trace


def test_trace_decorator():
    """Test standalone trace decorator."""
    with trace("test-trace", metadata={"test": "value"}):
        # Should execute without error
        pass


def test_agent_decorator_sync():
    """Test standalone agent decorator with sync function."""

    @agent(name="TestAgent", role="test")
    def test_agent(input_data: str) -> str:
        return f"Processed: {input_data}"

    result = test_agent("test")
    assert result == "Processed: test"


@pytest.mark.asyncio
async def test_agent_decorator_async():
    """Test standalone agent decorator with async function."""

    @agent(name="TestAgent", role="test")
    async def test_agent(input_data: str) -> str:
        await asyncio.sleep(0.01)
        return f"Processed: {input_data}"

    result = await test_agent("test")
    assert result == "Processed: test"


def test_tool_decorator_sync():
    """Test standalone tool decorator with sync function."""

    @tool(name="calculator")
    def calculate(expression: str) -> float:
        return eval(expression)

    result = calculate("2 + 2")
    assert result == 4.0


@pytest.mark.asyncio
async def test_tool_decorator_async():
    """Test standalone tool decorator with async function."""

    @tool(name="async_calculator")
    async def calculate(expression: str) -> float:
        await asyncio.sleep(0.01)
        return eval(expression)

    result = await calculate("3 + 3")
    assert result == 6.0


@pytest.mark.asyncio
async def test_nested_decorators():
    """Test nesting trace and agent decorators."""

    @agent(name="NestedAgent", role="test")
    async def nested_func(value: str) -> str:
        return f"Result: {value}"

    with trace("nested-test"):
        result = await nested_func("test")
        assert result == "Result: test"
