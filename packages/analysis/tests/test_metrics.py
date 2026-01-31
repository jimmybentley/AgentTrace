"""Tests for metrics aggregation."""


from agenttrace_analysis.metrics import TraceMetrics


def test_trace_metrics_creation():
    """Test creating trace metrics."""
    metrics = TraceMetrics(
        trace_id="trace-1",
        total_duration_ms=5000.0,
        total_tokens=1500,
        total_cost_usd=0.15,
        agent_count=3,
        span_count=10,
        error_count=2,
    )

    assert metrics.trace_id == "trace-1"
    assert metrics.total_duration_ms == 5000.0
    assert metrics.total_tokens == 1500
    assert metrics.total_cost_usd == 0.15
    assert metrics.agent_count == 3
    assert metrics.span_count == 10
    assert metrics.error_count == 2


def test_trace_metrics_defaults():
    """Test default values for trace metrics."""
    metrics = TraceMetrics(trace_id="trace-1")

    assert metrics.total_duration_ms == 0.0
    assert metrics.total_tokens == 0
    assert metrics.total_cost_usd == 0.0
    assert metrics.agent_count == 0
    assert metrics.span_count == 0
    assert metrics.error_count == 0
    assert metrics.tokens_by_agent == {}
    assert metrics.latency_by_agent == {}
    assert metrics.cost_by_agent == {}


def test_trace_metrics_to_dict():
    """Test serializing trace metrics to dictionary."""
    metrics = TraceMetrics(
        trace_id="trace-1",
        total_duration_ms=5000.0,
        total_tokens=1500,
        tokens_by_agent={"Agent1": 800, "Agent2": 700},
        latency_by_agent={"Agent1": 250.5, "Agent2": 180.3},
        cost_by_agent={"Agent1": 0.08, "Agent2": 0.07},
    )

    result = metrics.to_dict()

    assert result["trace_id"] == "trace-1"
    assert result["total_duration_ms"] == 5000.0
    assert result["total_tokens"] == 1500
    assert result["tokens_by_agent"]["Agent1"] == 800
    assert result["latency_by_agent"]["Agent2"] == 180.3
    assert result["cost_by_agent"]["Agent1"] == 0.08


def test_trace_metrics_per_agent_breakdowns():
    """Test per-agent breakdown fields."""
    metrics = TraceMetrics(trace_id="trace-1")

    # Add per-agent data
    metrics.tokens_by_agent["Agent1"] = 500
    metrics.tokens_by_agent["Agent2"] = 300
    metrics.latency_by_agent["Agent1"] = 150.0
    metrics.cost_by_agent["Agent1"] = 0.05

    assert len(metrics.tokens_by_agent) == 2
    assert metrics.tokens_by_agent["Agent1"] == 500
    assert metrics.latency_by_agent["Agent1"] == 150.0
    assert metrics.cost_by_agent["Agent1"] == 0.05


def test_trace_metrics_empty_breakdowns():
    """Test that empty per-agent breakdowns work correctly."""
    metrics = TraceMetrics(trace_id="trace-1")

    result = metrics.to_dict()

    assert result["tokens_by_agent"] == {}
    assert result["latency_by_agent"] == {}
    assert result["cost_by_agent"] == {}
