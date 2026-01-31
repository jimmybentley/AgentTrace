"""Tests for MAST failure classification."""

from datetime import UTC, datetime, timedelta

from agenttrace_analysis.mast import (
    FAILURE_MODES,
    ClassificationResult,
    FailureCategory,
    RuleBasedClassifier,
)


def test_failure_modes_exist():
    """Test that all expected failure modes are defined."""
    expected_modes = [
        "ambiguous_goal",
        "conflicting_constraints",
        "impossible_task",
        "infinite_loop",
        "handoff_failure",
        "resource_contention",
        "message_format_error",
        "hallucination",
        "incomplete_output",
        "timeout",
    ]

    for mode in expected_modes:
        assert mode in FAILURE_MODES


def test_failure_mode_categories():
    """Test that failure modes have correct categories."""
    assert FAILURE_MODES["infinite_loop"].category == FailureCategory.COORDINATION
    assert FAILURE_MODES["handoff_failure"].category == FailureCategory.COORDINATION
    assert FAILURE_MODES["timeout"].category == FailureCategory.VERIFICATION
    assert FAILURE_MODES["ambiguous_goal"].category == FailureCategory.SPECIFICATION


def test_classification_result_creation():
    """Test creating a classification result."""
    result = ClassificationResult(
        failure_mode="infinite_loop",
        category=FailureCategory.COORDINATION,
        confidence=0.85,
        reasoning="Agent called 4 times with same input",
        span_id="span-123",
        agent_id="agent-1",
    )

    assert result.failure_mode == "infinite_loop"
    assert result.category == FailureCategory.COORDINATION
    assert result.confidence == 0.85
    assert result.span_id == "span-123"


def test_classification_result_to_dict():
    """Test serializing classification result."""
    result = ClassificationResult(
        failure_mode="timeout",
        category=FailureCategory.VERIFICATION,
        confidence=0.95,
        reasoning="Execution timed out",
    )

    data = result.to_dict()

    assert data["failure_mode"] == "timeout"
    assert data["category"] == "verification"
    assert data["confidence"] == 0.95


def test_classifier_infinite_loop_detection():
    """Test detecting infinite loops."""
    classifier = RuleBasedClassifier()

    # Create spans showing infinite loop pattern
    base_time = datetime.now(UTC)
    spans = [
        {
            "span_id": f"span-{i}",
            "agent_id": "agent-1",
            "input": {"query": "test"},
            "start_time": base_time + timedelta(seconds=i),
            "status": "ok",
        }
        for i in range(5)  # 5 identical calls
    ]

    trace = {"trace_id": "trace-1", "status": "failed"}
    agents = {"agent-1": {"name": "TestAgent"}}

    results = classifier.classify(trace, spans, agents)

    # Should detect infinite loop
    assert len(results) > 0
    infinite_loop_results = [r for r in results if r.failure_mode == "infinite_loop"]
    assert len(infinite_loop_results) > 0
    assert infinite_loop_results[0].agent_id == "agent-1"


def test_classifier_handoff_failure_detection():
    """Test detecting handoff failures."""
    classifier = RuleBasedClassifier()

    base_time = datetime.now(UTC)
    spans = [
        {
            "span_id": "span-1",
            "agent_id": "agent-1",
            "kind": "handoff",
            "attributes": {"message.to_agent": "agent-2"},
            "start_time": base_time,
            "status": "ok",
        },
        {
            "span_id": "span-2",
            "agent_id": "agent-2",
            "kind": "agent",
            "start_time": base_time + timedelta(seconds=1),
            "status": "error",
            "error_message": "Failed to process handoff",
        },
    ]

    trace = {"trace_id": "trace-1", "status": "failed"}
    agents = {
        "agent-1": {"name": "Agent1"},
        "agent-2": {"name": "Agent2"},
    }

    results = classifier.classify(trace, spans, agents)

    # Should detect handoff failure
    handoff_results = [r for r in results if r.failure_mode == "handoff_failure"]
    assert len(handoff_results) > 0
    assert handoff_results[0].agent_id == "agent-2"


def test_classifier_resource_contention_detection():
    """Test detecting resource contention."""
    classifier = RuleBasedClassifier()

    base_time = datetime.now(UTC)
    spans = [
        {
            "span_id": "span-1",
            "agent_id": "agent-1",
            "kind": "tool_call",
            "name": "tool.database_query",
            "start_time": base_time,
            "end_time": base_time + timedelta(seconds=5),
            "status": "ok",
        },
        {
            "span_id": "span-2",
            "agent_id": "agent-2",
            "kind": "tool_call",
            "name": "tool.database_query",
            "start_time": base_time + timedelta(seconds=2),  # Overlaps!
            "end_time": base_time + timedelta(seconds=7),
            "status": "ok",
        },
    ]

    trace = {"trace_id": "trace-1", "status": "completed"}
    agents = {
        "agent-1": {"name": "Agent1"},
        "agent-2": {"name": "Agent2"},
    }

    results = classifier.classify(trace, spans, agents)

    # Should detect resource contention
    contention_results = [r for r in results if r.failure_mode == "resource_contention"]
    assert len(contention_results) > 0


def test_classifier_format_error_detection():
    """Test detecting message format errors."""
    classifier = RuleBasedClassifier()

    spans = [
        {
            "span_id": "span-1",
            "agent_id": "agent-1",
            "status": "error",
            "error_message": "JSON parse error: unexpected token",
            "start_time": datetime.now(UTC),
        }
    ]

    trace = {"trace_id": "trace-1", "status": "failed"}
    agents = {"agent-1": {"name": "Agent1"}}

    results = classifier.classify(trace, spans, agents)

    # Should detect format error
    format_results = [r for r in results if r.failure_mode == "message_format_error"]
    assert len(format_results) > 0
    assert "json" in format_results[0].reasoning.lower()


def test_classifier_timeout_detection():
    """Test detecting timeout failures."""
    classifier = RuleBasedClassifier()

    base_time = datetime.now(UTC)
    spans = [
        {
            "span_id": "span-1",
            "agent_id": "agent-1",
            "status": "timeout",
            "start_time": base_time,
            "end_time": base_time + timedelta(seconds=30),
        }
    ]

    trace = {"trace_id": "trace-1", "status": "failed"}
    agents = {"agent-1": {"name": "Agent1"}}

    results = classifier.classify(trace, spans, agents)

    # Should detect timeout
    timeout_results = [r for r in results if r.failure_mode == "timeout"]
    assert len(timeout_results) > 0
    assert timeout_results[0].confidence == 0.95


def test_classifier_no_failures():
    """Test that classifier returns empty list when no failures detected."""
    classifier = RuleBasedClassifier()

    spans = [
        {
            "span_id": "span-1",
            "agent_id": "agent-1",
            "status": "ok",
            "input": {"query": "test1"},
            "start_time": datetime.now(UTC),
        },
        {
            "span_id": "span-2",
            "agent_id": "agent-2",
            "status": "ok",
            "input": {"query": "test2"},
            "start_time": datetime.now(UTC) + timedelta(seconds=1),
        },
    ]

    trace = {"trace_id": "trace-1", "status": "completed"}
    agents = {
        "agent-1": {"name": "Agent1"},
        "agent-2": {"name": "Agent2"},
    }

    results = classifier.classify(trace, spans, agents)

    # Should not detect any failures
    assert len(results) == 0


def test_classifier_multiple_failures():
    """Test detecting multiple different failure types in one trace."""
    classifier = RuleBasedClassifier()

    base_time = datetime.now(UTC)
    spans = [
        # Timeout
        {
            "span_id": "span-1",
            "agent_id": "agent-1",
            "status": "timeout",
            "start_time": base_time,
            "end_time": base_time + timedelta(seconds=30),
        },
        # Format error
        {
            "span_id": "span-2",
            "agent_id": "agent-2",
            "status": "error",
            "error_message": "Schema validation failed",
            "start_time": base_time + timedelta(seconds=1),
        },
    ]

    trace = {"trace_id": "trace-1", "status": "failed"}
    agents = {
        "agent-1": {"name": "Agent1"},
        "agent-2": {"name": "Agent2"},
    }

    results = classifier.classify(trace, spans, agents)

    # Should detect both failures
    assert len(results) >= 2
    failure_modes = {r.failure_mode for r in results}
    assert "timeout" in failure_modes
    assert "message_format_error" in failure_modes
