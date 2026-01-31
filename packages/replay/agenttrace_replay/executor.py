"""Replay executor for re-running agents from checkpoints.

This module provides the core replay functionality, allowing developers to:
1. Load a checkpoint
2. Optionally modify the input
3. Re-execute the agent
4. Compare the new output with the original
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import asyncpg

from .checkpoint import CheckpointManager
from .differ import compute_diff
from .executors import get_executor


@dataclass
class ReplayConfig:
    """Configuration for a replay execution.

    Attributes:
        modified_input: Override input for replay (if None, use original)
        agent_overrides: Override agent config (model, temperature, etc.)
        stop_at_span: Partial replay - stop at this span ID
        timeout_seconds: Maximum time to wait for replay
        dry_run: If True, use mock executor (no LLM calls)
    """

    modified_input: dict[str, Any] | None = None
    agent_overrides: dict[str, Any] | None = None
    stop_at_span: str | None = None
    timeout_seconds: int = 300
    dry_run: bool = False


@dataclass
class ReplayResult:
    """Result of a replay execution.

    Attributes:
        replay_id: Unique identifier for this replay
        checkpoint_id: ID of the checkpoint that was replayed
        original_output: Original output from the trace
        replay_output: New output from the replay
        diff: Structured diff between original and replay
        success: Whether replay completed successfully
        error: Error message if replay failed
        duration_ms: Time taken to execute replay
        tokens_used: Tokens consumed (if LLM was called)
        cost_usd: Estimated cost (if LLM was called)
    """

    replay_id: str
    checkpoint_id: str
    original_output: Any
    replay_output: Any
    diff: dict[str, Any]
    success: bool
    error: str | None = None
    duration_ms: int = 0
    tokens_used: int | None = None
    cost_usd: float | None = None


class ReplayExecutor:
    """Executes replays from checkpoints.

    The ReplayExecutor orchestrates the replay process:
    1. Loads checkpoint from database
    2. Selects appropriate framework executor
    3. Executes with optional modifications
    4. Compares output and generates diff
    5. Stores replay result

    Usage:
        executor = ReplayExecutor(checkpoint_manager, db_pool)

        # Simple replay
        result = await executor.replay("checkpoint-123")

        # Replay with modified input
        config = ReplayConfig(modified_input={"query": "new question"})
        result = await executor.replay("checkpoint-123", config)

        # Dry run (no LLM calls)
        config = ReplayConfig(dry_run=True)
        result = await executor.replay("checkpoint-123", config)
    """

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        db_pool: asyncpg.Pool,
    ):
        """Initialize the replay executor.

        Args:
            checkpoint_manager: Manager for loading checkpoints
            db_pool: Database connection pool for storing results
        """
        self.checkpoints = checkpoint_manager
        self.db = db_pool

    async def replay(
        self,
        checkpoint_id: str,
        config: ReplayConfig | None = None,
    ) -> ReplayResult:
        """Replay execution from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to replay from
            config: Optional configuration for the replay

        Returns:
            ReplayResult with comparison to original

        Raises:
            ValueError: If checkpoint not found
            asyncio.TimeoutError: If replay times out
        """
        config = config or ReplayConfig()

        # Load checkpoint
        checkpoint = await self.checkpoints.load(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        # Get original span for comparison
        original_span = await self._get_original_span(checkpoint.span_id)
        if not original_span:
            raise ValueError(f"Original span not found: {checkpoint.span_id}")

        # Prepare input (with modifications if any)
        replay_input = config.modified_input or checkpoint.state.get("input", {})

        # Get agent configuration
        agent_config = checkpoint.state.get("agent_config", {})

        # Determine which executor to use
        if config.dry_run:
            framework = "mock"
        else:
            framework = agent_config.get("framework", "generic")

        executor = get_executor(framework)

        # Execute with timeout
        start_time = datetime.utcnow()
        replay_output = None
        error = None
        success = True

        try:
            replay_output = await asyncio.wait_for(
                executor(
                    input=replay_input,
                    state=checkpoint.state,
                    config=agent_config,
                    overrides=config.agent_overrides,
                ),
                timeout=config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            success = False
            error = f"Replay timed out after {config.timeout_seconds} seconds"
        except Exception as e:
            success = False
            error = f"{type(e).__name__}: {str(e)}"

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Compute diff
        original_output = original_span.get("output")
        diff = compute_diff(original_output, replay_output)

        # Extract token usage and cost if available
        tokens_used = None
        cost_usd = None

        if isinstance(replay_output, dict):
            if "tokens" in replay_output:
                tokens_data = replay_output["tokens"]
                if isinstance(tokens_data, dict):
                    tokens_used = tokens_data.get("input", 0) + tokens_data.get("output", 0)
            if "cost_usd" in replay_output:
                cost_usd = replay_output["cost_usd"]

        # Generate replay ID
        replay_id = f"replay-{uuid.uuid4()}"

        # Create result
        result = ReplayResult(
            replay_id=replay_id,
            checkpoint_id=checkpoint_id,
            original_output=original_output,
            replay_output=replay_output,
            diff=diff,
            success=success,
            error=error,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

        # Store replay result
        await self._store_replay(result, checkpoint.trace_id, config)

        # Update checkpoint replay count
        await self._update_checkpoint_stats(checkpoint_id)

        return result

    async def _get_original_span(self, span_id: str) -> dict[str, Any] | None:
        """Get the original span from the database.

        Args:
            span_id: ID of the span

        Returns:
            Span data as a dictionary, or None if not found
        """
        from uuid import UUID

        span_uuid = UUID(span_id) if isinstance(span_id, str) else span_id

        row = await self.db.fetchrow(
            """
            SELECT * FROM spans WHERE span_id = $1
            """,
            span_uuid,
        )

        if not row:
            return None

        return dict(row)

    async def _store_replay(
        self, result: ReplayResult, trace_id: str, config: ReplayConfig
    ):
        """Store replay result in the database.

        Args:
            result: The replay result to store
            trace_id: ID of the trace
            config: Replay configuration used
        """
        from uuid import UUID

        trace_uuid = UUID(trace_id) if isinstance(trace_id, str) else trace_id

        # Convert checkpoint_id to UUID
        # For now, we'll try to extract a UUID from the checkpoint_id string
        # In production, we'd want a better ID scheme
        checkpoint_uuid = None
        try:
            # Try to get the first UUID-like part
            parts = result.checkpoint_id.split(":")
            for part in parts:
                try:
                    checkpoint_uuid = UUID(part)
                    break
                except ValueError:
                    continue
        except Exception:
            pass

        # Build config dict
        config_dict = {
            "modified_input": config.modified_input,
            "agent_overrides": config.agent_overrides,
            "stop_at_span": config.stop_at_span,
            "timeout_seconds": config.timeout_seconds,
            "dry_run": config.dry_run,
        }

        await self.db.execute(
            """
            INSERT INTO replays (
                replay_id, checkpoint_id, trace_id,
                config, original_output, replay_output, diff,
                success, error, duration_ms, tokens_used, cost_usd
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            result.replay_id,
            checkpoint_uuid,
            trace_uuid,
            config_dict,
            result.original_output,
            result.replay_output,
            result.diff,
            result.success,
            result.error,
            result.duration_ms,
            result.tokens_used,
            result.cost_usd,
        )

    async def _update_checkpoint_stats(self, checkpoint_id: str):
        """Update checkpoint replay statistics.

        Args:
            checkpoint_id: ID of the checkpoint
        """
        await self.db.execute(
            """
            UPDATE checkpoints
            SET replay_count = replay_count + 1,
                last_replayed = NOW()
            WHERE checkpoint_id::text LIKE $1
            """,
            f"%{checkpoint_id}%",
        )

    async def get_replay(self, replay_id: str) -> ReplayResult | None:
        """Get a replay result by ID.

        Args:
            replay_id: ID of the replay

        Returns:
            ReplayResult, or None if not found
        """
        row = await self.db.fetchrow(
            """
            SELECT * FROM replays WHERE replay_id = $1
            """,
            replay_id,
        )

        if not row:
            return None

        return ReplayResult(
            replay_id=row["replay_id"],
            checkpoint_id=str(row["checkpoint_id"]),
            original_output=row["original_output"],
            replay_output=row["replay_output"],
            diff=row["diff"],
            success=row["success"],
            error=row["error"],
            duration_ms=row["duration_ms"],
            tokens_used=row["tokens_used"],
            cost_usd=float(row["cost_usd"]) if row["cost_usd"] else None,
        )

    async def list_replays_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """List all replays for a trace.

        Args:
            trace_id: ID of the trace

        Returns:
            List of replay metadata dictionaries
        """
        from uuid import UUID

        trace_uuid = UUID(trace_id) if isinstance(trace_id, str) else trace_id

        rows = await self.db.fetch(
            """
            SELECT
                replay_id, checkpoint_id, success, error,
                duration_ms, tokens_used, cost_usd, created_at
            FROM replays
            WHERE trace_id = $1
            ORDER BY created_at DESC
            """,
            trace_uuid,
        )

        return [
            {
                "replay_id": row["replay_id"],
                "checkpoint_id": str(row["checkpoint_id"]),
                "success": row["success"],
                "error": row["error"],
                "duration_ms": row["duration_ms"],
                "tokens_used": row["tokens_used"],
                "cost_usd": float(row["cost_usd"]) if row["cost_usd"] else None,
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]
