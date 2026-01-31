"""Metrics aggregation for traces and spans."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import asyncpg


@dataclass
class TraceMetrics:
    """Aggregated metrics for a trace."""

    trace_id: str

    # Overall metrics
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Counts
    agent_count: int = 0
    span_count: int = 0
    error_count: int = 0

    # Per-agent breakdowns
    tokens_by_agent: dict[str, int] = field(default_factory=dict)
    latency_by_agent: dict[str, float] = field(default_factory=dict)
    cost_by_agent: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "trace_id": self.trace_id,
            "total_duration_ms": self.total_duration_ms,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "agent_count": self.agent_count,
            "span_count": self.span_count,
            "error_count": self.error_count,
            "tokens_by_agent": self.tokens_by_agent,
            "latency_by_agent": self.latency_by_agent,
            "cost_by_agent": self.cost_by_agent,
        }


async def compute_trace_metrics(trace_id: str, db: asyncpg.Pool) -> TraceMetrics:
    """
    Compute aggregated metrics for a trace from the database.

    Args:
        trace_id: Trace ID to compute metrics for
        db: Database connection pool

    Returns:
        TraceMetrics with all fields populated
    """
    metrics = TraceMetrics(trace_id=trace_id)

    async with db.acquire() as conn:
        # Get overall trace-level metrics
        trace_data = await conn.fetchrow(
            """
            SELECT
                COUNT(DISTINCT agent_id) as agent_count,
                COUNT(*) as span_count,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0.0) as total_cost_usd,
                COALESCE(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END), 0) as error_count,
                MIN(start_time) as trace_start,
                MAX(end_time) as trace_end
            FROM spans
            WHERE trace_id = $1
            """,
            trace_id,
        )

        if trace_data:
            metrics.agent_count = trace_data["agent_count"] or 0
            metrics.span_count = trace_data["span_count"] or 0
            metrics.total_tokens = trace_data["total_tokens"] or 0
            metrics.total_cost_usd = float(trace_data["total_cost_usd"] or 0.0)
            metrics.error_count = trace_data["error_count"] or 0

            # Calculate total duration
            if trace_data["trace_start"] and trace_data["trace_end"]:
                duration = trace_data["trace_end"] - trace_data["trace_start"]
                metrics.total_duration_ms = duration.total_seconds() * 1000

        # Get per-agent breakdowns
        agent_metrics = await conn.fetch(
            """
            SELECT
                s.agent_id,
                a.name as agent_name,
                COALESCE(SUM(s.input_tokens + s.output_tokens), 0) as total_tokens,
                COALESCE(SUM(s.cost_usd), 0.0) as total_cost,
                COALESCE(AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time)) * 1000), 0.0) as avg_latency_ms
            FROM spans s
            LEFT JOIN agents a ON s.agent_id = a.agent_id
            WHERE s.trace_id = $1 AND s.agent_id IS NOT NULL
            GROUP BY s.agent_id, a.name
            """,
            trace_id,
        )

        for row in agent_metrics:
            agent_id = row["agent_id"]
            agent_name = row["agent_name"] or agent_id

            metrics.tokens_by_agent[agent_name] = row["total_tokens"]
            metrics.cost_by_agent[agent_name] = float(row["total_cost"])
            metrics.latency_by_agent[agent_name] = float(row["avg_latency_ms"])

    return metrics


async def compute_agent_metrics(
    agent_id: str, trace_id: str | None, db: asyncpg.Pool
) -> dict[str, Any]:
    """
    Compute metrics for a specific agent, optionally scoped to a trace.

    Args:
        agent_id: Agent ID to compute metrics for
        trace_id: Optional trace ID to scope metrics to
        db: Database connection pool

    Returns:
        Dictionary with agent metrics
    """
    async with db.acquire() as conn:
        query = """
            SELECT
                COUNT(*) as span_count,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0.0) as total_cost_usd,
                COALESCE(AVG(EXTRACT(EPOCH FROM (end_time - start_time)) * 1000), 0.0) as avg_latency_ms,
                COALESCE(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END), 0) as error_count
            FROM spans
            WHERE agent_id = $1
        """

        params = [agent_id]
        if trace_id:
            query += " AND trace_id = $2"
            params.append(trace_id)

        data = await conn.fetchrow(query, *params)

        return {
            "agent_id": agent_id,
            "span_count": data["span_count"] or 0,
            "total_tokens": data["total_tokens"] or 0,
            "total_cost_usd": float(data["total_cost_usd"] or 0.0),
            "avg_latency_ms": float(data["avg_latency_ms"] or 0.0),
            "error_count": data["error_count"] or 0,
        }
