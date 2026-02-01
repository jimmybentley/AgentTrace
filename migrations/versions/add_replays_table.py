"""add replays table and update checkpoints

Revision ID: a1b2c3d4e5f6
Revises: 9c0f0295e741
Create Date: 2026-01-31 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9c0f0295e741"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add state_bytea column to checkpoints for binary state storage
    op.execute(
        """
        ALTER TABLE checkpoints
        ADD COLUMN state_bytea BYTEA;
        """
    )

    # Create replays table
    op.execute(
        """
        CREATE TABLE replays (
            replay_id       TEXT PRIMARY KEY,
            checkpoint_id   UUID REFERENCES checkpoints(checkpoint_id) ON DELETE CASCADE,
            trace_id        UUID REFERENCES traces(trace_id) ON DELETE CASCADE,

            config          JSONB,              -- ReplayConfig as JSON
            original_output JSONB,
            replay_output   JSONB,
            diff            JSONB,

            success         BOOLEAN NOT NULL,
            error           TEXT,
            duration_ms     INTEGER,
            tokens_used     INTEGER,
            cost_usd        DECIMAL(10, 6),

            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # Create indexes for replays table
    op.execute("CREATE INDEX idx_replays_trace ON replays(trace_id);")
    op.execute("CREATE INDEX idx_replays_checkpoint ON replays(checkpoint_id);")
    op.execute("CREATE INDEX idx_replays_created_at ON replays(created_at DESC);")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop replays table
    op.execute("DROP TABLE IF EXISTS replays CASCADE;")

    # Remove state_bytea column from checkpoints
    op.execute(
        """
        ALTER TABLE checkpoints
        DROP COLUMN IF EXISTS state_bytea;
        """
    )
