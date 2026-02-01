"""Checkpoint management for replay debugging.

This module provides functionality for creating, storing, and loading checkpoints
that capture agent state at specific points in execution.
"""

import hashlib
import pickle
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

import asyncpg

T = TypeVar("T")


@dataclass
class Checkpoint(Generic[T]):
    """A checkpoint captures agent state at a specific point in execution.

    The checkpoint_id format is: {trace_id}:{span_id}:{state_hash}
    This provides a unique identifier while also making it easy to
    find checkpoints for a given trace or span.

    Attributes:
        checkpoint_id: Unique identifier for this checkpoint
        trace_id: ID of the trace this checkpoint belongs to
        span_id: ID of the span where this checkpoint was created
        agent_id: ID of the agent whose state was checkpointed
        name: Human-readable name (e.g., "auto:handoff:planner_to_executor")
        state: The serialized agent state (generic type T)
        timestamp: When this checkpoint was created
        state_hash: SHA256 hash of pickled state (first 16 chars)
    """

    checkpoint_id: str
    trace_id: str
    span_id: str
    agent_id: str
    name: str
    state: T
    timestamp: datetime
    state_hash: str

    @classmethod
    def create(
        cls,
        trace_id: str,
        span_id: str,
        agent_id: str,
        name: str,
        state: T,
    ) -> "Checkpoint[T]":
        """Create a new checkpoint with auto-generated ID and hash.

        Args:
            trace_id: ID of the trace
            span_id: ID of the span
            agent_id: ID of the agent
            name: Human-readable name for this checkpoint
            state: The state to checkpoint (will be pickled)

        Returns:
            A new Checkpoint instance
        """
        state_bytes = pickle.dumps(state)
        state_hash = hashlib.sha256(state_bytes).hexdigest()[:16]

        return cls(
            checkpoint_id=f"{trace_id}:{span_id}:{state_hash}",
            trace_id=trace_id,
            span_id=span_id,
            agent_id=agent_id,
            name=name,
            state=state,
            timestamp=datetime.utcnow(),
            state_hash=state_hash,
        )


class CheckpointManager:
    """Manages checkpoints for replay debugging.

    The CheckpointManager handles saving and loading checkpoints from the database.
    It supports both manual checkpoints (created explicitly) and automatic
    checkpoints (created at key points like agent handoffs).

    Checkpoints are stored with pickle serialization for now. In V2, we could
    move to JSON-serializable state for better security and portability.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize the checkpoint manager.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db = db_pool

    async def save(self, checkpoint: Checkpoint) -> str:
        """Save a checkpoint to the database.

        Args:
            checkpoint: The checkpoint to save

        Returns:
            The checkpoint_id of the saved checkpoint
        """
        state_bytes = pickle.dumps(checkpoint.state)

        # Convert string UUIDs to UUID objects for database
        trace_uuid = (
            UUID(checkpoint.trace_id)
            if isinstance(checkpoint.trace_id, str)
            else checkpoint.trace_id
        )
        span_uuid = (
            UUID(checkpoint.span_id) if isinstance(checkpoint.span_id, str) else checkpoint.span_id
        )
        agent_uuid = (
            UUID(checkpoint.agent_id)
            if isinstance(checkpoint.agent_id, str)
            else checkpoint.agent_id
        )

        # We'll store in the new state_bytea column for binary data
        # and keep state as JSONB NULL for compatibility
        await self.db.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, trace_id, span_id, agent_id,
                name, state, state_bytea, timestamp
            ) VALUES ($1, $2, $3, $4, $5, NULL, $6, $7)
            ON CONFLICT (checkpoint_id) DO NOTHING
            """,
            UUID(checkpoint.checkpoint_id.split(":")[-1])
            if ":" not in checkpoint.checkpoint_id[:8]
            else UUID(checkpoint.checkpoint_id.split(":")[0]),  # For now, use first part as UUID
            trace_uuid,
            span_uuid,
            agent_uuid,
            checkpoint.name,
            state_bytes,
            checkpoint.timestamp,
        )

        return checkpoint.checkpoint_id

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        """Load a checkpoint from the database.

        Args:
            checkpoint_id: ID of the checkpoint to load

        Returns:
            The Checkpoint instance, or None if not found
        """
        # For now, we'll search by name since checkpoint_id format is complex
        # In production, we'd want a better ID scheme
        rows = await self.db.fetch(
            """
            SELECT * FROM checkpoints
            WHERE checkpoint_id::text LIKE $1 OR name = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            f"%{checkpoint_id}%",
        )

        if not rows:
            return None

        row = rows[0]

        # Try to load from state_bytea first, fall back to state
        if row["state_bytea"]:
            state = pickle.loads(bytes(row["state_bytea"]))
        elif row["state"]:
            state = row["state"]
        else:
            return None

        return Checkpoint(
            checkpoint_id=str(row["checkpoint_id"]),
            trace_id=str(row["trace_id"]),
            span_id=str(row["span_id"]),
            agent_id=str(row["agent_id"]),
            name=row["name"],
            state=state,
            timestamp=row["timestamp"],
            state_hash=hashlib.sha256(
                row["state_bytea"] if row["state_bytea"] else pickle.dumps(row["state"])
            ).hexdigest()[:16],
        )

    async def list_for_trace(self, trace_id: str) -> list[dict]:
        """List all checkpoints for a trace with metadata.

        Args:
            trace_id: ID of the trace

        Returns:
            List of checkpoint metadata dictionaries
        """
        trace_uuid = UUID(trace_id) if isinstance(trace_id, str) else trace_id

        rows = await self.db.fetch(
            """
            SELECT
                c.checkpoint_id, c.name, c.timestamp, c.span_id, c.agent_id,
                a.name as agent_name,
                s.name as span_name,
                s.kind as span_kind
            FROM checkpoints c
            JOIN agents a ON c.agent_id = a.agent_id
            JOIN spans s ON c.span_id = s.span_id
            WHERE c.trace_id = $1
            ORDER BY c.timestamp
            """,
            trace_uuid,
        )

        return [
            {
                "checkpoint_id": str(row["checkpoint_id"]),
                "name": row["name"],
                "timestamp": row["timestamp"].isoformat(),
                "span_id": str(row["span_id"]),
                "agent_id": str(row["agent_id"]),
                "agent_name": row["agent_name"],
                "span_name": row["span_name"],
                "span_kind": row["span_kind"],
            }
            for row in rows
        ]

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            """
            DELETE FROM checkpoints
            WHERE checkpoint_id::text LIKE $1 OR name = $1
            """,
            f"%{checkpoint_id}%",
        )

        return result != "DELETE 0"

    async def auto_checkpoint_trace(self, trace_id: str) -> list[str]:
        """Automatically create checkpoints for a trace at key points.

        Creates checkpoints at:
        - Agent handoffs
        - Before tool calls
        - After LLM calls

        Args:
            trace_id: ID of the trace to checkpoint

        Returns:
            List of created checkpoint IDs
        """
        trace_uuid = UUID(trace_id) if isinstance(trace_id, str) else trace_id

        # Get all spans that should have checkpoints
        spans = await self.db.fetch(
            """
            SELECT * FROM spans
            WHERE trace_id = $1 AND kind IN ('handoff', 'tool_call', 'llm_call')
            ORDER BY start_time
            """,
            trace_uuid,
        )

        checkpoint_ids = []

        for span in spans:
            # Build state from span input + prior context
            state = {
                "input": span["input"],
                "output": span["output"],
                "prior_output": await self._get_prior_output(trace_uuid, span["span_id"]),
                "agent_config": await self._get_agent_config(span["agent_id"]),
                "span_kind": span["kind"],
                "span_name": span["name"],
            }

            checkpoint = Checkpoint.create(
                trace_id=str(trace_uuid),
                span_id=str(span["span_id"]),
                agent_id=str(span["agent_id"]),
                name=f"auto:{span['kind']}:{span['name']}",
                state=state,
            )

            checkpoint_id = await self.save(checkpoint)
            checkpoint_ids.append(checkpoint_id)

        return checkpoint_ids

    async def _get_prior_output(self, trace_id: UUID, span_id: UUID) -> dict[str, Any]:
        """Get the output from the most recent prior span in the trace."""
        row = await self.db.fetchrow(
            """
            SELECT output FROM spans
            WHERE trace_id = $1 AND start_time < (
                SELECT start_time FROM spans WHERE span_id = $2
            )
            ORDER BY start_time DESC
            LIMIT 1
            """,
            trace_id,
            span_id,
        )

        return row["output"] if row and row["output"] else {}

    async def _get_agent_config(self, agent_id: UUID) -> dict[str, Any]:
        """Get agent configuration."""
        row = await self.db.fetchrow(
            """
            SELECT name, role, model, framework, config
            FROM agents
            WHERE agent_id = $1
            """,
            agent_id,
        )

        if not row:
            return {}

        return {
            "name": row["name"],
            "role": row["role"],
            "model": row["model"],
            "framework": row["framework"],
            "config": row["config"] or {},
        }
