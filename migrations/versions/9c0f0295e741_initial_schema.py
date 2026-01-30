"""initial schema

Revision ID: 9c0f0295e741
Revises:
Create Date: 2026-01-29 20:31:58.906627

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c0f0295e741"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # Create traces table
    op.execute(
        """
        CREATE TABLE traces (
            trace_id        UUID PRIMARY KEY,
            name            TEXT,
            start_time      TIMESTAMPTZ NOT NULL,
            end_time        TIMESTAMPTZ,
            status          TEXT CHECK (status IN ('running', 'completed', 'failed', 'timeout')),
            metadata        JSONB,

            -- Aggregated metrics
            total_tokens    INTEGER,
            total_cost_usd  DECIMAL(10, 6),
            total_latency_ms INTEGER,
            agent_count     INTEGER,

            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # Create agents table
    op.execute(
        """
        CREATE TABLE agents (
            agent_id        UUID PRIMARY KEY,
            trace_id        UUID REFERENCES traces(trace_id) ON DELETE CASCADE,

            name            TEXT NOT NULL,
            role            TEXT,
            model           TEXT,
            framework       TEXT,

            config          JSONB,

            -- Aggregated metrics for this agent in this trace
            total_spans     INTEGER,
            total_tokens    INTEGER,
            total_cost_usd  DECIMAL(10, 6),
            error_count     INTEGER,

            created_at      TIMESTAMPTZ DEFAULT NOW(),

            UNIQUE(trace_id, name)
        );
        """
    )

    # Create spans table
    op.execute(
        """
        CREATE TABLE spans (
            span_id         UUID PRIMARY KEY,
            trace_id        UUID REFERENCES traces(trace_id) ON DELETE CASCADE,
            parent_span_id  UUID REFERENCES spans(span_id) ON DELETE CASCADE,
            agent_id        UUID REFERENCES agents(agent_id) ON DELETE SET NULL,

            name            TEXT NOT NULL,
            kind            TEXT CHECK (kind IN ('llm_call', 'tool_call', 'agent_message', 'checkpoint', 'handoff')),
            start_time      TIMESTAMPTZ NOT NULL,
            end_time        TIMESTAMPTZ,
            status          TEXT CHECK (status IN ('ok', 'error', 'timeout')),

            -- LLM-specific
            model           TEXT,
            input_tokens    INTEGER,
            output_tokens   INTEGER,
            cost_usd        DECIMAL(10, 6),

            -- Content (encrypted at rest in production)
            input           JSONB,
            output          JSONB,
            error           JSONB,

            attributes      JSONB,

            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # Create agent_messages table
    op.execute(
        """
        CREATE TABLE agent_messages (
            message_id      UUID PRIMARY KEY,
            trace_id        UUID REFERENCES traces(trace_id) ON DELETE CASCADE,
            span_id         UUID REFERENCES spans(span_id) ON DELETE CASCADE,

            from_agent_id   UUID REFERENCES agents(agent_id) ON DELETE CASCADE,
            to_agent_id     UUID REFERENCES agents(agent_id) ON DELETE CASCADE,

            message_type    TEXT CHECK (message_type IN ('request', 'response', 'broadcast', 'handoff')),
            content         JSONB,
            timestamp       TIMESTAMPTZ NOT NULL,

            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # Create checkpoints table
    op.execute(
        """
        CREATE TABLE checkpoints (
            checkpoint_id   UUID PRIMARY KEY,
            trace_id        UUID REFERENCES traces(trace_id) ON DELETE CASCADE,
            span_id         UUID REFERENCES spans(span_id) ON DELETE CASCADE,
            agent_id        UUID REFERENCES agents(agent_id) ON DELETE CASCADE,

            name            TEXT,
            state           JSONB NOT NULL,
            timestamp       TIMESTAMPTZ NOT NULL,

            -- Replay metadata
            replay_count    INTEGER DEFAULT 0,
            last_replayed   TIMESTAMPTZ,

            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # Create failure_annotations table
    op.execute(
        """
        CREATE TABLE failure_annotations (
            annotation_id   UUID PRIMARY KEY,
            trace_id        UUID REFERENCES traces(trace_id) ON DELETE CASCADE,
            span_id         UUID REFERENCES spans(span_id) ON DELETE CASCADE,
            agent_id        UUID REFERENCES agents(agent_id) ON DELETE CASCADE,

            -- MAST taxonomy
            category        TEXT CHECK (category IN ('specification', 'coordination', 'verification')),
            failure_mode    TEXT,
            confidence      DECIMAL(3, 2),

            -- Source
            source          TEXT CHECK (source IN ('auto', 'manual', 'llm_judge')),
            reasoning       TEXT,

            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # Create indexes for common queries
    op.execute("CREATE INDEX idx_spans_trace_id ON spans(trace_id);")
    op.execute("CREATE INDEX idx_spans_agent_id ON spans(agent_id);")
    op.execute("CREATE INDEX idx_spans_start_time ON spans(start_time DESC);")
    op.execute("CREATE INDEX idx_agent_messages_trace ON agent_messages(trace_id);")
    op.execute("CREATE INDEX idx_checkpoints_trace ON checkpoints(trace_id);")
    op.execute("CREATE INDEX idx_agents_trace ON agents(trace_id);")
    op.execute("CREATE INDEX idx_failure_annotations_trace ON failure_annotations(trace_id);")

    # Convert spans table to TimescaleDB hypertable for time-series queries
    op.execute(
        """
        SELECT create_hypertable('spans', 'start_time',
                                if_not_exists => TRUE,
                                migrate_data => TRUE);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (respecting foreign keys)
    op.execute("DROP TABLE IF EXISTS failure_annotations CASCADE;")
    op.execute("DROP TABLE IF EXISTS checkpoints CASCADE;")
    op.execute("DROP TABLE IF EXISTS agent_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS spans CASCADE;")
    op.execute("DROP TABLE IF EXISTS agents CASCADE;")
    op.execute("DROP TABLE IF EXISTS traces CASCADE;")
