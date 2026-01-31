"""Pytest configuration and fixtures for replay tests."""

import asyncio
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

import asyncpg
import pytest

from agenttrace_replay.checkpoint import Checkpoint, CheckpointManager
from agenttrace_replay.executor import ReplayExecutor


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create a test database connection pool.

    Note: This assumes a test database is available at the default location.
    In a real test environment, you might want to use a separate test database.
    """
    pool = await asyncpg.create_pool(
        "postgresql://agenttrace:dev_password@localhost:5432/agenttrace",
        min_size=1,
        max_size=5,
    )

    yield pool

    await pool.close()


@pytest.fixture
async def checkpoint_manager(db_pool: asyncpg.Pool) -> CheckpointManager:
    """Create a checkpoint manager for testing."""
    return CheckpointManager(db_pool)


@pytest.fixture
async def replay_executor(
    checkpoint_manager: CheckpointManager, db_pool: asyncpg.Pool
) -> ReplayExecutor:
    """Create a replay executor for testing."""
    return ReplayExecutor(checkpoint_manager, db_pool)


@pytest.fixture
def sample_checkpoint_state() -> dict:
    """Sample checkpoint state for testing."""
    return {
        "input": {"query": "What is AI?"},
        "output": {"response": "AI is artificial intelligence..."},
        "prior_output": {"context": "Previous conversation..."},
        "agent_config": {
            "name": "TestAgent",
            "role": "assistant",
            "model": "claude-3-opus",
            "framework": "mock",
            "config": {"temperature": 0.7},
        },
        "span_kind": "llm_call",
        "span_name": "test_span",
    }


@pytest.fixture
def sample_checkpoint(sample_checkpoint_state: dict) -> Checkpoint:
    """Create a sample checkpoint for testing."""
    return Checkpoint.create(
        trace_id=str(uuid4()),
        span_id=str(uuid4()),
        agent_id=str(uuid4()),
        name="test_checkpoint",
        state=sample_checkpoint_state,
    )


@pytest.fixture
async def test_trace_with_spans(db_pool: asyncpg.Pool) -> dict:
    """Create a test trace with spans in the database for testing."""
    trace_id = uuid4()
    agent_id = uuid4()
    span_id = uuid4()

    # Insert test trace
    await db_pool.execute(
        """
        INSERT INTO traces (trace_id, name, start_time, status)
        VALUES ($1, $2, $3, $4)
        """,
        trace_id,
        "test_trace",
        datetime.utcnow(),
        "running",
    )

    # Insert test agent
    await db_pool.execute(
        """
        INSERT INTO agents (agent_id, trace_id, name, role, model, framework)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        agent_id,
        trace_id,
        "TestAgent",
        "assistant",
        "claude-3-opus",
        "mock",
    )

    # Insert test span
    await db_pool.execute(
        """
        INSERT INTO spans (
            span_id, trace_id, agent_id, name, kind,
            start_time, status, input, output
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        span_id,
        trace_id,
        agent_id,
        "test_span",
        "llm_call",
        datetime.utcnow(),
        "ok",
        {"query": "What is AI?"},
        {"response": "AI is artificial intelligence..."},
    )

    yield {
        "trace_id": str(trace_id),
        "agent_id": str(agent_id),
        "span_id": str(span_id),
    }

    # Cleanup
    await db_pool.execute("DELETE FROM traces WHERE trace_id = $1", trace_id)
