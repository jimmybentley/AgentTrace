"""Tests for framework integrations."""

import importlib.util

import pytest

from agenttrace.integrations import get_available_integrations, instrument_frameworks


def test_get_available_integrations():
    """Test getting list of available integrations."""
    available = get_available_integrations()
    assert isinstance(available, list)
    # At minimum, the function should return a list (may be empty if no frameworks installed)


def test_instrument_unknown_framework():
    """Test that instrumenting unknown framework raises error."""
    with pytest.raises(ValueError, match="Unknown framework"):
        instrument_frameworks(["unknown_framework"])


def test_instrument_unavailable_framework():
    """Test that instrumenting unavailable framework raises error."""
    # Try to instrument a framework that's likely not installed in test environment
    with pytest.raises(ValueError):
        instrument_frameworks(["crewai"])  # Assuming CrewAI is not installed in test env


def test_instrument_frameworks_none():
    """Test instrumenting all available frameworks."""
    # Should not raise an error
    instrument_frameworks(None)


# LangGraph-specific tests (only run if LangGraph is installed)
LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph") is not None


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
def test_instrument_langgraph():
    """Test LangGraph instrumentation."""
    from agenttrace.integrations.langgraph import instrument_langgraph, is_instrumented

    # Should not be instrumented initially
    assert not is_instrumented()

    # Instrument
    instrument_langgraph()

    # Should now be instrumented
    assert is_instrumented()

    # Instrumenting again should be idempotent
    instrument_langgraph()
    assert is_instrumented()
