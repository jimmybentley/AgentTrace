"""FastAPI router for analysis and trace querying."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import asyncpg
from fastapi import APIRouter, HTTPException, Query

from .graph import AgentGraph
from .mast import RuleBasedClassifier
from .metrics import compute_trace_metrics

router = APIRouter(prefix="/api", tags=["analysis"])

# Global database pool (will be injected by server)
_db_pool: asyncpg.Pool | None = None


def set_db_pool(pool: asyncpg.Pool) -> None:
    """Set the database connection pool for API handlers."""
    global _db_pool
    _db_pool = pool


def get_db() -> asyncpg.Pool:
    """Get database pool or raise error if not initialized."""
    if _db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return _db_pool


@router.get("/traces")
async def list_traces(
    limit: int = Query(50, ge=1, le=1000, description="Number of traces to return"),
    offset: int = Query(0, ge=0, description="Number of traces to skip"),
    status: str | None = Query(None, description="Filter by status (running, completed, failed)"),
    start_time: datetime | None = Query(None, description="Filter traces after this time"),
    end_time: datetime | None = Query(None, description="Filter traces before this time"),
) -> dict[str, Any]:
    """
    List traces with pagination and filtering.

    Returns:
        Dictionary with traces list, total count, and pagination info
    """
    db = get_db()

    # Build query with filters
    conditions = []
    params: list[Any] = []
    param_idx = 1

    if status:
        conditions.append(f"status = ${param_idx}")
        params.append(status)
        param_idx += 1

    if start_time:
        conditions.append(f"start_time >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        conditions.append(f"end_time <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with db.acquire() as conn:
        # Get total count
        count_query = f"SELECT COUNT(*) FROM traces {where_clause}"
        total = await conn.fetchval(count_query, *params)

        # Get paginated results
        list_query = f"""
            SELECT
                t.trace_id,
                t.name,
                t.status,
                t.start_time,
                t.end_time,
                t.metadata,
                t.total_tokens,
                t.total_cost_usd,
                t.agent_count,
                (SELECT COUNT(*) FROM spans WHERE trace_id = t.trace_id) as span_count
            FROM traces t
            {where_clause}
            ORDER BY t.start_time DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        rows = await conn.fetch(list_query, *params)

        traces = [
            {
                "trace_id": row["trace_id"],
                "name": row["name"],
                "status": row["status"],
                "start_time": row["start_time"].isoformat() if row["start_time"] else None,
                "end_time": row["end_time"].isoformat() if row["end_time"] else None,
                "metadata": row["metadata"],
                "total_tokens": row["total_tokens"] or 0,
                "total_cost_usd": float(row["total_cost_usd"]) if row["total_cost_usd"] else 0.0,
                "agent_count": row["agent_count"] or 0,
                "span_count": row["span_count"] or 0,
            }
            for row in rows
        ]

    return {
        "traces": traces,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    include_graph: bool = Query(False, description="Include agent communication graph"),
) -> dict[str, Any]:
    """
    Get detailed information about a specific trace.

    Args:
        trace_id: Trace ID
        include_graph: Whether to include the agent communication graph

    Returns:
        Trace details with optional graph
    """
    db = get_db()

    async with db.acquire() as conn:
        # Get trace
        trace = await conn.fetchrow("SELECT * FROM traces WHERE trace_id = $1", trace_id)

        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Get span count and agent count
        counts = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as span_count,
                COUNT(DISTINCT agent_id) as agent_count
            FROM spans
            WHERE trace_id = $1
            """,
            trace_id,
        )

        result = {
            "trace_id": trace["trace_id"],
            "name": trace["name"],
            "status": trace["status"],
            "start_time": trace["start_time"].isoformat() if trace["start_time"] else None,
            "end_time": trace["end_time"].isoformat() if trace["end_time"] else None,
            "metadata": trace["metadata"],
            "total_tokens": trace["total_tokens"] or 0,
            "total_cost_usd": float(trace["total_cost_usd"]) if trace["total_cost_usd"] else 0.0,
            "span_count": counts["span_count"],
            "agent_count": trace["agent_count"] or counts["agent_count"],
        }

        # Optionally include graph
        if include_graph:
            graph = await AgentGraph.from_trace(trace_id, db)
            result["graph"] = graph.to_dict()

    return result


@router.get("/traces/{trace_id}/graph")
async def get_trace_graph(trace_id: str) -> dict[str, Any]:
    """
    Get agent communication graph for a trace.

    Args:
        trace_id: Trace ID

    Returns:
        Graph with nodes, edges, and metrics
    """
    db = get_db()

    # Verify trace exists
    async with db.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM traces WHERE trace_id = $1)", trace_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Trace not found")

    # Build and return graph
    graph = await AgentGraph.from_trace(trace_id, db)
    result = graph.to_dict()
    result["trace_id"] = trace_id

    # Add analysis
    result["analysis"] = {
        "bottlenecks": graph.find_bottlenecks(),
        "isolated_agents": graph.find_isolated_agents(),
    }

    return result


@router.get("/traces/{trace_id}/failures")
async def get_trace_failures(trace_id: str) -> dict[str, Any]:
    """
    Get failure annotations for a trace.

    Args:
        trace_id: Trace ID

    Returns:
        List of failure annotations
    """
    db = get_db()

    async with db.acquire() as conn:
        # Verify trace exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM traces WHERE trace_id = $1)", trace_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Get failure annotations
        annotations = await conn.fetch(
            """
            SELECT
                annotation_id,
                span_id,
                agent_id,
                failure_mode,
                category,
                confidence,
                reasoning,
                created_at
            FROM failure_annotations
            WHERE trace_id = $1
            ORDER BY created_at DESC
            """,
            trace_id,
        )

        result_annotations = [
            {
                "annotation_id": ann["annotation_id"],
                "span_id": ann["span_id"],
                "agent_id": ann["agent_id"],
                "failure_mode": ann["failure_mode"],
                "category": ann["category"],
                "confidence": float(ann["confidence"]),
                "reasoning": ann["reasoning"],
                "created_at": ann["created_at"].isoformat(),
            }
            for ann in annotations
        ]

    return {
        "trace_id": trace_id,
        "annotations": result_annotations,
        "count": len(result_annotations),
    }


@router.get("/traces/{trace_id}/metrics")
async def get_trace_metrics(trace_id: str) -> dict[str, Any]:
    """
    Get aggregated metrics for a trace.

    Args:
        trace_id: Trace ID

    Returns:
        Trace metrics including tokens, cost, latency breakdowns
    """
    db = get_db()

    # Verify trace exists
    async with db.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM traces WHERE trace_id = $1)", trace_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Trace not found")

    # Compute and return metrics
    metrics = await compute_trace_metrics(trace_id, db)
    return metrics.to_dict()


@router.post("/traces/{trace_id}/classify")
async def classify_trace_failures(trace_id: str) -> dict[str, Any]:
    """
    Run failure classification on a trace and store results.

    Args:
        trace_id: Trace ID

    Returns:
        Classification results
    """
    db = get_db()

    async with db.acquire() as conn:
        # Get trace
        trace = await conn.fetchrow("SELECT * FROM traces WHERE trace_id = $1", trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Get spans
        span_rows = await conn.fetch(
            """
            SELECT
                span_id, parent_span_id, agent_id, name, kind, status,
                start_time, end_time, model, input, output, error,
                attributes, input_tokens, output_tokens, cost_usd
            FROM spans
            WHERE trace_id = $1
            ORDER BY start_time
            """,
            trace_id,
        )

        spans = [dict(row) for row in span_rows]

        # Get agents
        agent_rows = await conn.fetch(
            """
            SELECT DISTINCT a.agent_id, a.name, a.role, a.model, a.framework, a.config
            FROM agents a
            JOIN spans s ON s.agent_id = a.agent_id
            WHERE s.trace_id = $1
            """,
            trace_id,
        )

        agents = {row["agent_id"]: dict(row) for row in agent_rows}

        # Run classifier
        classifier = RuleBasedClassifier()
        trace_dict = dict(trace)
        results = classifier.classify(trace_dict, spans, agents)

        # Store results in database
        stored_annotations = []
        for result in results:
            annotation_id = await conn.fetchval(
                """
                INSERT INTO failure_annotations
                (trace_id, span_id, agent_id, failure_mode, category, confidence, reasoning)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING annotation_id
                """,
                trace_id,
                result.span_id,
                result.agent_id,
                result.failure_mode,
                result.category.value,
                result.confidence,
                result.reasoning,
            )

            stored_annotations.append(
                {
                    "annotation_id": annotation_id,
                    **result.to_dict(),
                }
            )

    return {
        "trace_id": trace_id,
        "annotations": stored_annotations,
        "count": len(stored_annotations),
    }


@router.get("/traces/{trace_id}/spans")
async def list_trace_spans(
    trace_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of spans to return"),
    offset: int = Query(0, ge=0, description="Number of spans to skip"),
) -> dict[str, Any]:
    """
    List spans for a trace with pagination.

    Args:
        trace_id: Trace ID
        limit: Max number of spans to return
        offset: Number of spans to skip

    Returns:
        List of spans with pagination info
    """
    db = get_db()

    async with db.acquire() as conn:
        # Verify trace exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM traces WHERE trace_id = $1)", trace_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Get total count
        total = await conn.fetchval("SELECT COUNT(*) FROM spans WHERE trace_id = $1", trace_id)

        # Get paginated spans
        spans = await conn.fetch(
            """
            SELECT
                span_id, trace_id, parent_span_id, agent_id, name, kind, status,
                start_time, end_time, model, input, output, error,
                attributes, input_tokens, output_tokens, cost_usd
            FROM spans
            WHERE trace_id = $1
            ORDER BY start_time
            LIMIT $2 OFFSET $3
            """,
            trace_id,
            limit,
            offset,
        )

        span_list = [
            {
                "span_id": span["span_id"],
                "trace_id": span["trace_id"],
                "parent_span_id": span["parent_span_id"],
                "agent_id": span["agent_id"],
                "name": span["name"],
                "kind": span["kind"],
                "status": span["status"],
                "start_time": span["start_time"].isoformat() if span["start_time"] else None,
                "end_time": span["end_time"].isoformat() if span["end_time"] else None,
                "model": span["model"],
                "input": span["input"],
                "output": span["output"],
                "error": span["error"],
                "attributes": span["attributes"],
                "input_tokens": span["input_tokens"],
                "output_tokens": span["output_tokens"],
                "cost_usd": float(span["cost_usd"]) if span["cost_usd"] else None,
            }
            for span in spans
        ]

    return {
        "trace_id": trace_id,
        "spans": span_list,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/spans/{span_id}")
async def get_span(span_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific span.

    Args:
        span_id: Span ID

    Returns:
        Span details
    """
    db = get_db()

    async with db.acquire() as conn:
        span = await conn.fetchrow(
            """
            SELECT
                s.span_id, s.trace_id, s.parent_span_id, s.agent_id,
                s.name, s.kind, s.status, s.start_time, s.end_time,
                s.model, s.input, s.output, s.error, s.attributes,
                s.input_tokens, s.output_tokens, s.cost_usd,
                a.name as agent_name, a.role as agent_role
            FROM spans s
            LEFT JOIN agents a ON s.agent_id = a.agent_id
            WHERE s.span_id = $1
            """,
            span_id,
        )

        if not span:
            raise HTTPException(status_code=404, detail="Span not found")

        # Calculate duration
        duration_ms = None
        if span["start_time"] and span["end_time"]:
            duration = span["end_time"] - span["start_time"]
            duration_ms = duration.total_seconds() * 1000

        result = {
            "span_id": span["span_id"],
            "trace_id": span["trace_id"],
            "parent_span_id": span["parent_span_id"],
            "agent_id": span["agent_id"],
            "agent_name": span["agent_name"],
            "agent_role": span["agent_role"],
            "name": span["name"],
            "kind": span["kind"],
            "status": span["status"],
            "start_time": span["start_time"].isoformat() if span["start_time"] else None,
            "end_time": span["end_time"].isoformat() if span["end_time"] else None,
            "duration_ms": duration_ms,
            "model": span["model"],
            "input": span["input"],
            "output": span["output"],
            "error": span["error"],
            "attributes": span["attributes"],
            "input_tokens": span["input_tokens"],
            "output_tokens": span["output_tokens"],
            "cost_usd": float(span["cost_usd"]) if span["cost_usd"] else None,
        }

    return result
