"""Tests for analysis API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from agenttrace_analysis import api


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    pool = MagicMock()
    conn = AsyncMock()

    # Set up the async context manager for acquire()
    acquire_context = AsyncMock()
    acquire_context.__aenter__.return_value = conn
    acquire_context.__aexit__.return_value = None
    pool.acquire.return_value = acquire_context

    return pool, conn


@pytest.fixture
def client(mock_db_pool):
    """Create test client with mock database."""
    pool, _ = mock_db_pool
    api.set_db_pool(pool)

    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(api.router)

    return TestClient(app)


def test_list_traces_empty(client, mock_db_pool):
    """Test listing traces when database is empty."""
    pool, conn = mock_db_pool
    conn.fetchval.return_value = 0  # Total count
    conn.fetch.return_value = []  # Empty results

    response = client.get("/api/traces")

    assert response.status_code == 200
    data = response.json()
    assert data["traces"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_list_traces_with_results(client, mock_db_pool):
    """Test listing traces with results."""
    pool, conn = mock_db_pool
    conn.fetchval.return_value = 2  # Total count

    # Mock trace results
    mock_traces = [
        {
            "trace_id": "trace-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "status": "completed",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC),
            "metadata": {"key": "value"},
        },
        {
            "trace_id": "trace-2",
            "session_id": "session-2",
            "user_id": "user-2",
            "status": "failed",
            "start_time": datetime.now(UTC),
            "end_time": None,
            "metadata": {},
        },
    ]
    conn.fetch.return_value = mock_traces

    response = client.get("/api/traces?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["traces"]) == 2
    assert data["total"] == 2
    assert data["limit"] == 10


def test_list_traces_with_status_filter(client, mock_db_pool):
    """Test listing traces filtered by status."""
    pool, conn = mock_db_pool
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [
        {
            "trace_id": "trace-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "status": "failed",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC),
            "metadata": {},
        }
    ]

    response = client.get("/api/traces?status=failed")

    assert response.status_code == 200
    data = response.json()
    assert len(data["traces"]) == 1
    assert data["traces"][0]["status"] == "failed"


def test_get_trace_not_found(client, mock_db_pool):
    """Test getting a trace that doesn't exist."""
    pool, conn = mock_db_pool
    conn.fetchrow.return_value = None

    response = client.get("/api/traces/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_trace_success(client, mock_db_pool):
    """Test getting a trace successfully."""
    pool, conn = mock_db_pool

    # Mock trace data
    conn.fetchrow.side_effect = [
        {
            "trace_id": "trace-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "status": "completed",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC),
            "metadata": {},
        },
        {"span_count": 10, "agent_count": 3},
    ]

    response = client.get("/api/traces/trace-1")

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-1"
    assert data["span_count"] == 10
    assert data["agent_count"] == 3


def test_get_trace_graph_not_found(client, mock_db_pool):
    """Test getting graph for nonexistent trace."""
    pool, conn = mock_db_pool
    conn.fetchval.return_value = False  # Trace doesn't exist

    response = client.get("/api/traces/nonexistent/graph")

    assert response.status_code == 404


def test_get_trace_failures(client, mock_db_pool):
    """Test getting failure annotations for a trace."""
    pool, conn = mock_db_pool

    # Mock trace existence check
    conn.fetchval.return_value = True

    # Mock annotations
    mock_annotations = [
        {
            "annotation_id": 1,
            "span_id": "span-1",
            "agent_id": "agent-1",
            "failure_mode": "timeout",
            "category": "verification",
            "confidence": 0.95,
            "reasoning": "Timeout occurred",
            "created_at": datetime.now(UTC),
        }
    ]
    conn.fetch.return_value = mock_annotations

    response = client.get("/api/traces/trace-1/failures")

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-1"
    assert data["count"] == 1
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["failure_mode"] == "timeout"


def test_get_trace_metrics_not_found(client, mock_db_pool):
    """Test getting metrics for nonexistent trace."""
    pool, conn = mock_db_pool
    conn.fetchval.return_value = False  # Trace doesn't exist

    response = client.get("/api/traces/nonexistent/metrics")

    assert response.status_code == 404


def test_list_trace_spans(client, mock_db_pool):
    """Test listing spans for a trace."""
    pool, conn = mock_db_pool

    # Mock trace existence and spans
    conn.fetchval.side_effect = [True, 5]  # exists, total count
    mock_spans = [
        {
            "span_id": "span-1",
            "parent_span_id": None,
            "agent_id": "agent-1",
            "name": "agent_execution",
            "kind": "agent",
            "status": "ok",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC),
            "input": {},
            "output": {},
            "error_message": None,
            "attributes": {},
            "input_tokens": 100,
            "output_tokens": 50,
            "cost_usd": 0.01,
        }
    ]
    conn.fetch.return_value = mock_spans

    response = client.get("/api/traces/trace-1/spans")

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-1"
    assert data["total"] == 5
    assert len(data["spans"]) == 1


def test_get_span_not_found(client, mock_db_pool):
    """Test getting a span that doesn't exist."""
    pool, conn = mock_db_pool
    conn.fetchrow.return_value = None

    response = client.get("/api/spans/nonexistent")

    assert response.status_code == 404


def test_get_span_success(client, mock_db_pool):
    """Test getting a span successfully."""
    pool, conn = mock_db_pool

    mock_span = {
        "span_id": "span-1",
        "trace_id": "trace-1",
        "parent_span_id": None,
        "agent_id": "agent-1",
        "agent_name": "TestAgent",
        "agent_role": "coordinator",
        "name": "agent_execution",
        "kind": "agent",
        "status": "ok",
        "start_time": datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        "end_time": datetime(2026, 1, 31, 12, 0, 5, tzinfo=UTC),
        "input": {"query": "test"},
        "output": {"result": "success"},
        "error_message": None,
        "attributes": {},
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_usd": 0.01,
    }
    conn.fetchrow.return_value = mock_span

    response = client.get("/api/spans/span-1")

    assert response.status_code == 200
    data = response.json()
    assert data["span_id"] == "span-1"
    assert data["agent_name"] == "TestAgent"
    assert data["duration_ms"] == 5000.0  # 5 seconds
    assert data["input_tokens"] == 100


def test_classify_trace_not_found(client, mock_db_pool):
    """Test classifying a nonexistent trace."""
    pool, conn = mock_db_pool
    conn.fetchrow.return_value = None

    response = client.post("/api/traces/nonexistent/classify")

    assert response.status_code == 404


def test_api_pagination_limits(client, mock_db_pool):
    """Test that pagination parameters have correct limits."""
    pool, conn = mock_db_pool
    conn.fetchval.return_value = 0
    conn.fetch.return_value = []

    # Test max limit
    response = client.get("/api/traces?limit=2000")
    assert response.status_code == 422  # Validation error

    # Test negative offset
    response = client.get("/api/traces?offset=-1")
    assert response.status_code == 422

    # Test valid parameters
    response = client.get("/api/traces?limit=100&offset=0")
    assert response.status_code == 200
