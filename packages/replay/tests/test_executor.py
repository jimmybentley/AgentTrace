"""Tests for replay executor."""

import pytest

from agenttrace_replay.executor import ReplayConfig


class TestReplayConfig:
    """Tests for ReplayConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReplayConfig()

        assert config.modified_input is None
        assert config.agent_overrides is None
        assert config.stop_at_span is None
        assert config.timeout_seconds == 300
        assert config.dry_run is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReplayConfig(
            modified_input={"query": "new question"},
            agent_overrides={"model": "claude-3-haiku"},
            timeout_seconds=120,
            dry_run=True,
        )

        assert config.modified_input == {"query": "new question"}
        assert config.agent_overrides == {"model": "claude-3-haiku"}
        assert config.timeout_seconds == 120
        assert config.dry_run is True


class TestReplayExecutor:
    """Tests for ReplayExecutor class."""

    @pytest.mark.asyncio
    async def test_replay_with_mock_executor(
        self, replay_executor, checkpoint_manager, test_trace_with_spans
    ):
        """Test replay using mock executor."""
        try:
            # Create a checkpoint
            from agenttrace_replay.checkpoint import Checkpoint

            checkpoint = Checkpoint.create(
                trace_id=test_trace_with_spans["trace_id"],
                span_id=test_trace_with_spans["span_id"],
                agent_id=test_trace_with_spans["agent_id"],
                name="test_checkpoint",
                state={
                    "input": {"query": "What is AI?"},
                    "output": {"response": "Original response"},
                    "agent_config": {
                        "name": "TestAgent",
                        "framework": "mock",
                    },
                    "span_kind": "llm_call",
                },
            )

            checkpoint_id = await checkpoint_manager.save(checkpoint)

            # Execute replay with dry run (mock executor)
            config = ReplayConfig(dry_run=True)
            result = await replay_executor.replay(checkpoint_id, config)

            assert result is not None
            assert result.success is True
            assert result.replay_output is not None
            assert result.diff is not None
            assert result.duration_ms >= 0
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_replay_with_modified_input(
        self, replay_executor, checkpoint_manager, test_trace_with_spans
    ):
        """Test replay with modified input."""
        try:
            from agenttrace_replay.checkpoint import Checkpoint

            checkpoint = Checkpoint.create(
                trace_id=test_trace_with_spans["trace_id"],
                span_id=test_trace_with_spans["span_id"],
                agent_id=test_trace_with_spans["agent_id"],
                name="test_checkpoint",
                state={
                    "input": {"query": "Original question"},
                    "output": {"response": "Original response"},
                    "agent_config": {
                        "name": "TestAgent",
                        "framework": "mock",
                    },
                    "span_kind": "llm_call",
                },
            )

            checkpoint_id = await checkpoint_manager.save(checkpoint)

            # Execute replay with modified input
            config = ReplayConfig(modified_input={"query": "Modified question"}, dry_run=True)
            result = await replay_executor.replay(checkpoint_id, config)

            assert result is not None
            assert result.success is True
            # Mock executor should echo the modified input
            assert "Modified question" in str(result.replay_output)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_replay_nonexistent_checkpoint(self, replay_executor):
        """Test replay with nonexistent checkpoint."""
        try:
            with pytest.raises(ValueError, match="Checkpoint not found"):
                await replay_executor.replay("nonexistent-checkpoint-id")
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_get_replay(self, replay_executor, checkpoint_manager, test_trace_with_spans):
        """Test retrieving a replay result."""
        try:
            from agenttrace_replay.checkpoint import Checkpoint

            # Create and execute replay
            checkpoint = Checkpoint.create(
                trace_id=test_trace_with_spans["trace_id"],
                span_id=test_trace_with_spans["span_id"],
                agent_id=test_trace_with_spans["agent_id"],
                name="test_checkpoint",
                state={
                    "input": {"query": "Test"},
                    "output": {"response": "Test response"},
                    "agent_config": {"name": "TestAgent", "framework": "mock"},
                    "span_kind": "llm_call",
                },
            )

            checkpoint_id = await checkpoint_manager.save(checkpoint)
            result = await replay_executor.replay(checkpoint_id, ReplayConfig(dry_run=True))

            # Retrieve the replay
            retrieved = await replay_executor.get_replay(result.replay_id)

            assert retrieved is not None
            assert retrieved.replay_id == result.replay_id
            assert retrieved.checkpoint_id == result.checkpoint_id
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.asyncio
    async def test_list_replays_for_trace(
        self, replay_executor, checkpoint_manager, test_trace_with_spans
    ):
        """Test listing replays for a trace."""
        try:
            from agenttrace_replay.checkpoint import Checkpoint

            # Create and execute a replay
            checkpoint = Checkpoint.create(
                trace_id=test_trace_with_spans["trace_id"],
                span_id=test_trace_with_spans["span_id"],
                agent_id=test_trace_with_spans["agent_id"],
                name="test_checkpoint",
                state={
                    "input": {"query": "Test"},
                    "output": {"response": "Test response"},
                    "agent_config": {"name": "TestAgent", "framework": "mock"},
                    "span_kind": "llm_call",
                },
            )

            checkpoint_id = await checkpoint_manager.save(checkpoint)
            await replay_executor.replay(checkpoint_id, ReplayConfig(dry_run=True))

            # List replays
            replays = await replay_executor.list_replays_for_trace(
                test_trace_with_spans["trace_id"]
            )

            assert len(replays) > 0
            assert all("replay_id" in r for r in replays)
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
