"""Tests for custom exceptions."""

import pytest

from agenttrace_core.exceptions import (
    AgentTraceError,
    CheckpointError,
    TraceNotFoundError,
)


def test_trace_not_found_error():
    """Test TraceNotFoundError with trace_id."""
    trace_id = "550e8400-e29b-41d4-a716-446655440000"
    error = TraceNotFoundError(trace_id)

    assert error.trace_id == trace_id
    assert "Trace not found" in str(error)
    assert trace_id in str(error)


def test_checkpoint_error():
    """Test CheckpointError can be raised."""
    with pytest.raises(CheckpointError):
        raise CheckpointError("Failed to create checkpoint")


def test_base_exception():
    """Test that all custom exceptions inherit from AgentTraceError."""
    assert issubclass(TraceNotFoundError, AgentTraceError)
    assert issubclass(CheckpointError, AgentTraceError)
