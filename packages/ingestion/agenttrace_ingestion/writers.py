"""Database writer for ingested traces."""

import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg

from agenttrace_core.models import NormalizedSpan


class DatabaseWriter:
    """
    Manages database writes for ingested traces.

    Features:
    - Connection pooling (min 5, max 20 connections)
    - Batch writes (default batch size: 100 spans)
    - Upsert logic for traces and agents
    - Automatic agent_messages extraction
    """

    def __init__(self, database_url: str, batch_size: int = 100):
        """
        Initialize database writer.

        Args:
            database_url: PostgreSQL connection string
            batch_size: Number of spans to batch before flushing
        """
        self.database_url = database_url
        self.batch_size = batch_size
        self._pool: asyncpg.Pool | None = None
        self._batch: list[NormalizedSpan] = []
        self._lock = asyncio.Lock()

    async def connect(self):
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(
            self.database_url, min_size=5, max_size=20, command_timeout=60
        )

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()

    async def write(self, span: NormalizedSpan):
        """
        Buffer span and batch write for efficiency.

        Args:
            span: Normalized span to write
        """
        async with self._lock:
            self._batch.append(span)

            if len(self._batch) >= self.batch_size:
                await self._flush()

    async def flush(self):
        """Manually flush the current batch."""
        async with self._lock:
            await self._flush()

    async def _flush(self):
        """Internal flush implementation (assumes lock is held)."""
        if not self._batch or not self._pool:
            return

        batch = self._batch.copy()
        self._batch = []

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 1. Upsert traces
                await self._upsert_traces(conn, batch)

                # 2. Upsert agents
                await self._upsert_agents(conn, batch)

                # 3. Insert spans
                await self._insert_spans(conn, batch)

                # 4. Insert agent messages
                await self._insert_agent_messages(conn, batch)

    async def _upsert_traces(self, conn: asyncpg.Connection, batch: list[NormalizedSpan]):
        """Upsert traces from batch."""
        # Group by trace_id
        traces: dict[str, NormalizedSpan] = {}
        for span in batch:
            if span.trace_id not in traces:
                traces[span.trace_id] = span

        if not traces:
            return

        # Upsert each trace
        for trace_id, span in traces.items():
            await conn.execute(
                """
                INSERT INTO traces (trace_id, name, start_time, status, metadata)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (trace_id) DO UPDATE SET
                    end_time = CASE
                        WHEN EXCLUDED.end_time IS NOT NULL
                        THEN GREATEST(traces.end_time, EXCLUDED.end_time)
                        ELSE traces.end_time
                    END,
                    status = CASE
                        WHEN EXCLUDED.status IN ('failed', 'timeout')
                        THEN EXCLUDED.status
                        ELSE traces.status
                    END
                """,
                UUID(trace_id),
                None,  # name will be set later if needed
                span.start_time,
                "running",
                {},
            )

    async def _upsert_agents(self, conn: asyncpg.Connection, batch: list[NormalizedSpan]):
        """Upsert agents from batch."""
        # Collect unique agents
        agents: dict[tuple[str, str], NormalizedSpan] = {}
        for span in batch:
            if span.agent:
                key = (span.trace_id, span.agent.name)
                if key not in agents:
                    agents[key] = span

        if not agents:
            return

        # Upsert each agent
        for (trace_id, _agent_name), span in agents.items():
            agent = span.agent
            await conn.execute(
                """
                INSERT INTO agents (
                    agent_id, trace_id, name, role, model, framework, config
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (trace_id, name) DO UPDATE SET
                    role = COALESCE(EXCLUDED.role, agents.role),
                    model = COALESCE(EXCLUDED.model, agents.model),
                    framework = COALESCE(EXCLUDED.framework, agents.framework),
                    config = COALESCE(EXCLUDED.config, agents.config)
                RETURNING agent_id
                """,
                uuid4(),
                UUID(trace_id),
                agent.name,
                agent.role,
                agent.model,
                agent.framework,
                agent.config,
            )

    async def _insert_spans(self, conn: asyncpg.Connection, batch: list[NormalizedSpan]):
        """Insert spans from batch."""
        for span in batch:
            # Get agent_id if agent exists
            agent_id = None
            if span.agent:
                agent_id = await conn.fetchval(
                    """
                    SELECT agent_id FROM agents
                    WHERE trace_id = $1 AND name = $2
                    """,
                    UUID(span.trace_id),
                    span.agent.name,
                )

            # Convert cost_usd to Decimal if it's a float
            cost_usd = Decimal(str(span.cost_usd)) if span.cost_usd is not None else None

            await conn.execute(
                """
                INSERT INTO spans (
                    span_id, trace_id, parent_span_id, agent_id,
                    name, kind, start_time, end_time, status,
                    model, input_tokens, output_tokens, cost_usd,
                    input, output, error, attributes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (span_id) DO NOTHING
                """,
                UUID(span.span_id),
                UUID(span.trace_id),
                UUID(span.parent_span_id) if span.parent_span_id else None,
                agent_id,
                span.name,
                span.kind,
                span.start_time,
                span.end_time,
                span.status,
                span.model,
                span.input_tokens,
                span.output_tokens,
                cost_usd,
                span.input,
                span.output,
                span.error,
                span.attributes,
            )

    async def _insert_agent_messages(
        self, conn: asyncpg.Connection, batch: list[NormalizedSpan]
    ):
        """Insert agent messages extracted from spans."""
        for span in batch:
            if not span.messages:
                continue

            for message in span.messages:
                # Get agent IDs
                from_agent_id = None
                to_agent_id = None

                if message.from_agent:
                    from_agent_id = await conn.fetchval(
                        """
                        SELECT agent_id FROM agents
                        WHERE trace_id = $1 AND name = $2
                        """,
                        UUID(span.trace_id),
                        message.from_agent,
                    )

                if message.to_agent:
                    to_agent_id = await conn.fetchval(
                        """
                        SELECT agent_id FROM agents
                        WHERE trace_id = $1 AND name = $2
                        """,
                        UUID(span.trace_id),
                        message.to_agent,
                    )

                await conn.execute(
                    """
                    INSERT INTO agent_messages (
                        message_id, trace_id, span_id,
                        from_agent_id, to_agent_id,
                        message_type, content, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    uuid4(),
                    UUID(span.trace_id),
                    UUID(span.span_id),
                    from_agent_id,
                    to_agent_id,
                    message.message_type,
                    message.content,
                    message.timestamp or span.start_time,
                )
