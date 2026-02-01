"""FastAPI router for replay endpoints.

This module provides REST API endpoints for checkpoint management and replay execution.
"""

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .checkpoint import CheckpointManager
from .executor import ReplayConfig, ReplayExecutor

# Router for replay-related endpoints
router = APIRouter()

# Global database pool - will be set by the main application
_db_pool: asyncpg.Pool | None = None


def set_db_pool(pool: asyncpg.Pool):
    """Set the database pool for the replay API.

    This should be called by the main application during startup.

    Args:
        pool: PostgreSQL connection pool
    """
    global _db_pool
    _db_pool = pool


async def get_db_pool() -> asyncpg.Pool:
    """Dependency to get the database pool.

    Returns:
        Database pool

    Raises:
        HTTPException: If database pool is not configured
    """
    if _db_pool is None:
        raise HTTPException(status_code=500, detail="Database pool not configured")
    return _db_pool


async def get_checkpoint_manager(
    db: asyncpg.Pool = Depends(get_db_pool),
) -> CheckpointManager:
    """Dependency to get a checkpoint manager.

    Args:
        db: Database pool

    Returns:
        CheckpointManager instance
    """
    return CheckpointManager(db)


async def get_replay_executor(
    db: asyncpg.Pool = Depends(get_db_pool),
    checkpoint_mgr: CheckpointManager = Depends(get_checkpoint_manager),
) -> ReplayExecutor:
    """Dependency to get a replay executor.

    Args:
        db: Database pool
        checkpoint_mgr: Checkpoint manager

    Returns:
        ReplayExecutor instance
    """
    return ReplayExecutor(checkpoint_mgr, db)


# Request/Response models


class CreateCheckpointsRequest(BaseModel):
    """Request to create checkpoints for a trace."""

    auto: bool = Field(default=True, description="Auto-create checkpoints at key points")


class CreateCheckpointsResponse(BaseModel):
    """Response from creating checkpoints."""

    checkpoint_ids: list[str] = Field(description="IDs of created checkpoints")
    count: int = Field(description="Number of checkpoints created")


class CheckpointDetail(BaseModel):
    """Detailed checkpoint information."""

    checkpoint_id: str
    name: str
    timestamp: str
    span_id: str
    agent_id: str
    agent_name: str
    span_name: str
    span_kind: str


class ReplayRequest(BaseModel):
    """Request to execute a replay."""

    modified_input: dict[str, Any] | None = Field(
        default=None, description="Override input for replay"
    )
    agent_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Override agent config (model, temperature, etc.)",
    )
    timeout_seconds: int = Field(default=300, description="Maximum time to wait for replay")
    dry_run: bool = Field(default=False, description="Use mock executor (no LLM calls)")


class ReplayResponse(BaseModel):
    """Response from executing a replay."""

    replay_id: str
    checkpoint_id: str
    success: bool
    duration_ms: int
    diff: dict[str, Any]
    original_output: Any
    replay_output: Any
    error: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None


class ReplayListItem(BaseModel):
    """Summary of a replay for list views."""

    replay_id: str
    checkpoint_id: str
    success: bool
    error: str | None
    duration_ms: int
    tokens_used: int | None
    cost_usd: float | None
    created_at: str


# API Endpoints


@router.get("/traces/{trace_id}/checkpoints", response_model=list[CheckpointDetail])
async def list_checkpoints(
    trace_id: str,
    checkpoint_mgr: CheckpointManager = Depends(get_checkpoint_manager),
):
    """List all checkpoints for a trace.

    Args:
        trace_id: ID of the trace
        checkpoint_mgr: Checkpoint manager dependency

    Returns:
        List of checkpoints with metadata
    """
    checkpoints = await checkpoint_mgr.list_for_trace(trace_id)
    return [CheckpointDetail(**cp) for cp in checkpoints]


@router.post(
    "/traces/{trace_id}/checkpoints",
    response_model=CreateCheckpointsResponse,
    status_code=201,
)
async def create_checkpoints(
    trace_id: str,
    request: CreateCheckpointsRequest,
    checkpoint_mgr: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Create checkpoints for a trace.

    If auto=True, automatically creates checkpoints at:
    - Agent handoffs
    - Before tool calls
    - After LLM calls

    Args:
        trace_id: ID of the trace
        request: Request parameters
        checkpoint_mgr: Checkpoint manager dependency

    Returns:
        Created checkpoint IDs
    """
    if request.auto:
        checkpoint_ids = await checkpoint_mgr.auto_checkpoint_trace(trace_id)
    else:
        # Manual checkpoint creation not implemented in V1
        raise HTTPException(
            status_code=400,
            detail="Manual checkpoint creation not yet supported. Use auto=True.",
        )

    return CreateCheckpointsResponse(checkpoint_ids=checkpoint_ids, count=len(checkpoint_ids))


@router.get("/checkpoints/{checkpoint_id}", response_model=CheckpointDetail)
async def get_checkpoint(
    checkpoint_id: str,
    checkpoint_mgr: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Get checkpoint details.

    Args:
        checkpoint_id: ID of the checkpoint
        checkpoint_mgr: Checkpoint manager dependency

    Returns:
        Checkpoint details

    Raises:
        HTTPException: If checkpoint not found
    """
    checkpoint = await checkpoint_mgr.load(checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Get additional metadata
    checkpoints = await checkpoint_mgr.list_for_trace(checkpoint.trace_id)
    checkpoint_detail = next(
        (cp for cp in checkpoints if checkpoint_id in cp["checkpoint_id"]),
        None,
    )

    if not checkpoint_detail:
        # Fall back to basic info
        return CheckpointDetail(
            checkpoint_id=checkpoint.checkpoint_id,
            name=checkpoint.name,
            timestamp=checkpoint.timestamp.isoformat(),
            span_id=checkpoint.span_id,
            agent_id=checkpoint.agent_id,
            agent_name="unknown",
            span_name="unknown",
            span_kind="unknown",
        )

    return CheckpointDetail(**checkpoint_detail)


@router.delete("/checkpoints/{checkpoint_id}", status_code=204)
async def delete_checkpoint(
    checkpoint_id: str,
    checkpoint_mgr: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Delete a checkpoint.

    Args:
        checkpoint_id: ID of the checkpoint
        checkpoint_mgr: Checkpoint manager dependency

    Raises:
        HTTPException: If checkpoint not found
    """
    deleted = await checkpoint_mgr.delete(checkpoint_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Checkpoint not found")


@router.post(
    "/checkpoints/{checkpoint_id}/replay",
    response_model=ReplayResponse,
    status_code=201,
)
async def execute_replay(
    checkpoint_id: str,
    request: ReplayRequest,
    executor: ReplayExecutor = Depends(get_replay_executor),
):
    """Execute a replay from a checkpoint.

    Args:
        checkpoint_id: ID of the checkpoint to replay from
        request: Replay configuration
        executor: Replay executor dependency

    Returns:
        Replay result with diff

    Raises:
        HTTPException: If checkpoint not found or replay fails
    """
    config = ReplayConfig(
        modified_input=request.modified_input,
        agent_overrides=request.agent_overrides,
        timeout_seconds=request.timeout_seconds,
        dry_run=request.dry_run,
    )

    try:
        result = await executor.replay(checkpoint_id, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay execution failed: {str(e)}") from e

    return ReplayResponse(
        replay_id=result.replay_id,
        checkpoint_id=result.checkpoint_id,
        success=result.success,
        duration_ms=result.duration_ms,
        diff=result.diff,
        original_output=result.original_output,
        replay_output=result.replay_output,
        error=result.error,
        tokens_used=result.tokens_used,
        cost_usd=result.cost_usd,
    )


@router.get("/replays/{replay_id}", response_model=ReplayResponse)
async def get_replay(
    replay_id: str,
    executor: ReplayExecutor = Depends(get_replay_executor),
):
    """Get a replay result by ID.

    Args:
        replay_id: ID of the replay
        executor: Replay executor dependency

    Returns:
        Replay result

    Raises:
        HTTPException: If replay not found
    """
    result = await executor.get_replay(replay_id)

    if not result:
        raise HTTPException(status_code=404, detail="Replay not found")

    return ReplayResponse(
        replay_id=result.replay_id,
        checkpoint_id=result.checkpoint_id,
        success=result.success,
        duration_ms=result.duration_ms,
        diff=result.diff,
        original_output=result.original_output,
        replay_output=result.replay_output,
        error=result.error,
        tokens_used=result.tokens_used,
        cost_usd=result.cost_usd,
    )


@router.get("/replays/{replay_id}/diff", response_model=dict)
async def get_replay_diff(
    replay_id: str,
    executor: ReplayExecutor = Depends(get_replay_executor),
):
    """Get detailed diff for a replay.

    Args:
        replay_id: ID of the replay
        executor: Replay executor dependency

    Returns:
        Diff details

    Raises:
        HTTPException: If replay not found
    """
    result = await executor.get_replay(replay_id)

    if not result:
        raise HTTPException(status_code=404, detail="Replay not found")

    return result.diff


@router.get("/traces/{trace_id}/replays", response_model=list[ReplayListItem])
async def list_replays(
    trace_id: str,
    executor: ReplayExecutor = Depends(get_replay_executor),
):
    """List all replays for a trace.

    Args:
        trace_id: ID of the trace
        executor: Replay executor dependency

    Returns:
        List of replays
    """
    replays = await executor.list_replays_for_trace(trace_id)
    return [ReplayListItem(**replay) for replay in replays]
