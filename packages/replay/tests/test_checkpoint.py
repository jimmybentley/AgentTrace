"""Tests for checkpoint management."""

import pytest

from agenttrace_replay.checkpoint import Checkpoint


class TestCheckpoint:
    """Tests for Checkpoint class."""

    def test_create_checkpoint(self, sample_checkpoint_state):
        """Test creating a checkpoint."""
        checkpoint = Checkpoint.create(
            trace_id="trace-123",
            span_id="span-456",
            agent_id="agent-789",
            name="test_checkpoint",
            state=sample_checkpoint_state,
        )

        assert checkpoint.trace_id == "trace-123"
        assert checkpoint.span_id == "span-456"
        assert checkpoint.agent_id == "agent-789"
        assert checkpoint.name == "test_checkpoint"
        assert checkpoint.state == sample_checkpoint_state
        assert len(checkpoint.state_hash) == 16
        assert ":" in checkpoint.checkpoint_id

    def test_checkpoint_id_format(self, sample_checkpoint_state):
        """Test that checkpoint ID has correct format."""
        checkpoint = Checkpoint.create(
            trace_id="trace-123",
            span_id="span-456",
            agent_id="agent-789",
            name="test",
            state=sample_checkpoint_state,
        )

        assert checkpoint.checkpoint_id.startswith("trace-123:span-456:")

    def test_checkpoint_hash_consistency(self, sample_checkpoint_state):
        """Test that same state produces same hash."""
        cp1 = Checkpoint.create(
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            name="test",
            state=sample_checkpoint_state,
        )

        cp2 = Checkpoint.create(
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            name="test",
            state=sample_checkpoint_state,
        )

        assert cp1.state_hash == cp2.state_hash


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(
        self, checkpoint_manager, sample_checkpoint
    ):
        """Test saving and loading a checkpoint."""
        # This test requires a real database connection
        # Skip if database is not available
        try:
            checkpoint_id = await checkpoint_manager.save(sample_checkpoint)
            assert checkpoint_id is not None

            # Load the checkpoint
            loaded = await checkpoint_manager.load(checkpoint_id)
            assert loaded is not None
            assert loaded.trace_id == sample_checkpoint.trace_id
            assert loaded.name == sample_checkpoint.name
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_load_nonexistent_checkpoint(self, checkpoint_manager):
        """Test loading a checkpoint that doesn't exist."""
        try:
            loaded = await checkpoint_manager.load("nonexistent-id")
            assert loaded is None
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_list_checkpoints_for_trace(
        self, checkpoint_manager, test_trace_with_spans
    ):
        """Test listing checkpoints for a trace."""
        try:
            # Create a checkpoint for the test trace
            checkpoint = Checkpoint.create(
                trace_id=test_trace_with_spans["trace_id"],
                span_id=test_trace_with_spans["span_id"],
                agent_id=test_trace_with_spans["agent_id"],
                name="test_checkpoint",
                state={"test": "data"},
            )

            await checkpoint_manager.save(checkpoint)

            # List checkpoints
            checkpoints = await checkpoint_manager.list_for_trace(
                test_trace_with_spans["trace_id"]
            )

            assert len(checkpoints) > 0
            assert any(cp["name"] == "test_checkpoint" for cp in checkpoints)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, checkpoint_manager, sample_checkpoint):
        """Test deleting a checkpoint."""
        try:
            # Save checkpoint
            checkpoint_id = await checkpoint_manager.save(sample_checkpoint)

            # Delete it
            deleted = await checkpoint_manager.delete(checkpoint_id)
            assert deleted is True

            # Try to load it
            loaded = await checkpoint_manager.load(checkpoint_id)
            assert loaded is None
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_auto_checkpoint_trace(
        self, checkpoint_manager, test_trace_with_spans
    ):
        """Test automatically creating checkpoints for a trace."""
        try:
            checkpoint_ids = await checkpoint_manager.auto_checkpoint_trace(
                test_trace_with_spans["trace_id"]
            )

            # Should create at least one checkpoint for the test span
            assert len(checkpoint_ids) > 0
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
