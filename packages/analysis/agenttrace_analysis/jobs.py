"""Background jobs for trace analysis and classification."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg

from .mast import RuleBasedClassifier

logger = logging.getLogger(__name__)


async def classify_failed_traces(db: asyncpg.Pool, batch_size: int = 10) -> int:
    """
    Find traces with status="failed" that have no annotations and classify them.

    This function can be run as a one-off task or scheduled periodically.

    Args:
        db: Database connection pool
        batch_size: Number of traces to process in one batch

    Returns:
        Number of traces classified
    """
    logger.info("Starting classification job for failed traces")
    classifier = RuleBasedClassifier()
    traces_classified = 0

    async with db.acquire() as conn:
        # Find failed traces without annotations
        unclassified_traces = await conn.fetch(
            """
            SELECT t.trace_id, t.status
            FROM traces t
            WHERE t.status = 'failed'
            AND NOT EXISTS (
                SELECT 1 FROM failure_annotations fa
                WHERE fa.trace_id = t.trace_id
            )
            ORDER BY t.start_time DESC
            LIMIT $1
            """,
            batch_size,
        )

        logger.info(f"Found {len(unclassified_traces)} unclassified failed traces")

        for trace_row in unclassified_traces:
            trace_id = trace_row["trace_id"]

            try:
                # Get trace details
                trace = await conn.fetchrow("SELECT * FROM traces WHERE trace_id = $1", trace_id)

                # Get spans
                span_rows = await conn.fetch(
                    """
                    SELECT
                        span_id, parent_span_id, agent_id, name, kind, status,
                        start_time, end_time, input, output, error_message,
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

                # Run classification
                trace_dict = dict(trace)
                results = classifier.classify(trace_dict, spans, agents)

                # Store results
                for result in results:
                    await conn.execute(
                        """
                        INSERT INTO failure_annotations
                        (trace_id, span_id, agent_id, failure_mode, category, confidence, reasoning)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        trace_id,
                        result.span_id,
                        result.agent_id,
                        result.failure_mode,
                        result.category.value,
                        result.confidence,
                        result.reasoning,
                    )

                traces_classified += 1
                logger.info(f"Classified trace {trace_id}: found {len(results)} failures")

            except Exception as e:
                logger.error(f"Error classifying trace {trace_id}: {e}", exc_info=True)
                continue

    logger.info(f"Classification job complete: {traces_classified} traces processed")
    return traces_classified


async def classify_trace(
    trace_id: str, db: asyncpg.Pool, overwrite: bool = False
) -> list[dict[str, Any]]:
    """
    Classify a specific trace and store annotations.

    Args:
        trace_id: Trace ID to classify
        db: Database connection pool
        overwrite: If True, delete existing annotations before classifying

    Returns:
        List of stored annotation dictionaries
    """
    classifier = RuleBasedClassifier()

    async with db.acquire() as conn:
        # Check if trace exists
        trace = await conn.fetchrow("SELECT * FROM traces WHERE trace_id = $1", trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        # Optionally delete existing annotations
        if overwrite:
            await conn.execute("DELETE FROM failure_annotations WHERE trace_id = $1", trace_id)

        # Get spans
        span_rows = await conn.fetch(
            """
            SELECT
                span_id, parent_span_id, agent_id, name, kind, status,
                start_time, end_time, input, output, error_message,
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

        # Run classification
        trace_dict = dict(trace)
        results = classifier.classify(trace_dict, spans, agents)

        # Store results
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
                    "trace_id": trace_id,
                    "span_id": result.span_id,
                    "agent_id": result.agent_id,
                    "failure_mode": result.failure_mode,
                    "category": result.category.value,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                }
            )

        logger.info(f"Classified trace {trace_id}: stored {len(stored_annotations)} annotations")
        return stored_annotations


async def periodic_classification_job(
    db: asyncpg.Pool, interval_seconds: int = 300, batch_size: int = 10
) -> None:
    """
    Run classification job periodically in the background.

    Args:
        db: Database connection pool
        interval_seconds: Time between job runs
        batch_size: Number of traces to process per run
    """
    logger.info(f"Starting periodic classification job (interval: {interval_seconds}s)")

    while True:
        try:
            await classify_failed_traces(db, batch_size=batch_size)
        except Exception as e:
            logger.error(f"Error in periodic classification job: {e}", exc_info=True)

        await asyncio.sleep(interval_seconds)
