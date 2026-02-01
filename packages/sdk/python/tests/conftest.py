"""Shared pytest fixtures for AgentTrace SDK tests."""

import pytest

from agenttrace.config import AgentTraceConfig


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return AgentTraceConfig(
        endpoint="http://localhost:4318",
        service_name="test-service",
        enabled=True,
    )


@pytest.fixture
def disabled_config():
    """Create a configuration with tracing disabled."""
    return AgentTraceConfig(
        endpoint="http://localhost:4318",
        service_name="test-service",
        enabled=False,
    )


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state between tests."""
    # Reset config
    import agenttrace.config

    agenttrace.config._config = None

    # Reset OTEL initialization state
    import agenttrace._otel

    agenttrace._otel._initialized = False

    # Reset instrumentation states
    try:
        import agenttrace.integrations.langgraph

        agenttrace.integrations.langgraph._instrumented = False
    except ImportError:
        pass

    try:
        import agenttrace.integrations.autogen

        agenttrace.integrations.autogen._instrumented = False
    except ImportError:
        pass

    try:
        import agenttrace.integrations.crewai

        agenttrace.integrations.crewai._instrumented = False
    except ImportError:
        pass

    yield
