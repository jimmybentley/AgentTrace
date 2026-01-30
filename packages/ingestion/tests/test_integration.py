"""Integration tests for ingestion pipeline.

These tests require a running PostgreSQL database with TimescaleDB.
Run with: make docker-up && make test
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from agenttrace_core.config import Settings

# Mark all tests in this module as requiring database
pytestmark = pytest.mark.asyncio


@pytest.fixture
def settings():
    """Get settings."""
    return Settings()


@pytest.fixture
async def db_connection(settings):
    """Create database connection for testing."""
    import asyncpg

    try:
        conn = await asyncpg.connect(settings.database_url)
        yield conn
        await conn.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
async def clean_database(db_connection):
    """Clean database before each test."""
    await db_connection.execute("TRUNCATE traces, spans, agents, agent_messages CASCADE")
    yield
    await db_connection.execute("TRUNCATE traces, spans, agents, agent_messages CASCADE")


@pytest.fixture
async def app_client():
    """Create test client for FastAPI app."""
    from agenttrace_ingestion.server import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_health_check(self, app_client):
        """Test health check endpoint."""
        response = await app_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "agenttrace-ingestion"

    async def test_readiness_check_with_db(self, app_client, db_connection):
        """Test readiness check with database connection."""
        response = await app_client.get("/ready")

        # If DB is available, should be ready
        if db_connection:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"


class TestOTLPIngestion:
    """Tests for OTLP trace ingestion."""

    async def test_ingest_simple_trace(self, app_client, clean_database, db_connection):
        """Test ingesting a simple OTLP trace."""
        # Create minimal OTLP JSON request
        otlp_data = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "test-service"}},
                            {"key": "agent.framework", "value": {"stringValue": "langgraph"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "0102030405060708090a0b0c0d0e0f10",
                                    "spanId": "0102030405060708",
                                    "name": "test_span",
                                    "startTimeUnixNano": str(
                                        int(
                                            datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC).timestamp()
                                            * 1_000_000_000
                                        )
                                    ),
                                    "endTimeUnixNano": str(
                                        int(
                                            datetime(2026, 1, 29, 12, 0, 1, tzinfo=UTC).timestamp()
                                            * 1_000_000_000
                                        )
                                    ),
                                    "attributes": [
                                        {
                                            "key": "langgraph.node",
                                            "value": {"stringValue": "TestAgent"},
                                        }
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ]
        }

        response = await app_client.post(
            "/v1/traces", json=otlp_data, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["spans_processed"] == 1

        # Verify span was written to database
        span_count = await db_connection.fetchval("SELECT COUNT(*) FROM spans")
        assert span_count == 1

        # Verify agent was created
        agent = await db_connection.fetchrow("SELECT * FROM agents LIMIT 1")
        assert agent is not None
        assert agent["name"] == "TestAgent"
        assert agent["framework"] == "langgraph"

    async def test_ingest_multiple_spans(self, app_client, clean_database, db_connection):
        """Test ingesting multiple spans."""
        otlp_data = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "agent.framework", "value": {"stringValue": "generic"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "0102030405060708090a0b0c0d0e0f10",
                                    "spanId": f"010203040506070{i}",
                                    "name": f"span_{i}",
                                    "startTimeUnixNano": str(
                                        int(
                                            datetime(2026, 1, 29, 12, 0, i, tzinfo=UTC).timestamp()
                                            * 1_000_000_000
                                        )
                                    ),
                                    "attributes": [],
                                }
                                for i in range(5)
                            ]
                        }
                    ],
                }
            ]
        }

        response = await app_client.post("/v1/traces", json=otlp_data)

        assert response.status_code == 200
        data = response.json()
        assert data["spans_processed"] == 5

        # Verify all spans were written
        span_count = await db_connection.fetchval("SELECT COUNT(*) FROM spans")
        assert span_count == 5

    async def test_ingest_with_agent_message(self, app_client, clean_database, db_connection):
        """Test ingesting span with inter-agent message."""
        otlp_data = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "agent.framework", "value": {"stringValue": "langgraph"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "0102030405060708090a0b0c0d0e0f10",
                                    "spanId": "0102030405060708",
                                    "name": "langgraph.edge",
                                    "startTimeUnixNano": str(
                                        int(
                                            datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC).timestamp()
                                            * 1_000_000_000
                                        )
                                    ),
                                    "attributes": [
                                        {
                                            "key": "langgraph.source_node",
                                            "value": {"stringValue": "Planner"},
                                        },
                                        {
                                            "key": "langgraph.target_node",
                                            "value": {"stringValue": "Coder"},
                                        },
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ]
        }

        response = await app_client.post("/v1/traces", json=otlp_data)

        assert response.status_code == 200

        # Verify agent_message was created
        message_count = await db_connection.fetchval("SELECT COUNT(*) FROM agent_messages")
        assert message_count == 1


class TestErrorHandling:
    """Tests for error handling."""

    async def test_empty_request_body(self, app_client):
        """Test empty request body returns 400."""
        response = await app_client.post("/v1/traces", content=b"")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    async def test_invalid_json(self, app_client):
        """Test invalid JSON returns 400."""
        response = await app_client.post(
            "/v1/traces", content=b"not valid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid OTLP request" in data["error"]

    async def test_unsupported_content_type(self, app_client):
        """Test unsupported content type returns 400."""
        response = await app_client.post(
            "/v1/traces", content=b"data", headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 400
