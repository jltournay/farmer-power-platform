"""Integration tests for MongoDB checkpointer.

These tests validate the MongoDB checkpointer integration.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver


class TestMongoDBCheckpointerFactory:
    """Tests for MongoDB checkpointer factory function."""

    @pytest.mark.integration
    def test_create_checkpointer_returns_base_saver(self) -> None:
        """Test that factory returns a BaseCheckpointSaver."""
        from ai_model.workflows.checkpointer import create_mongodb_checkpointer

        # Mock MongoClient with necessary methods
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Set up mock chain
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        # Mock the MongoDBSaver class to avoid actual MongoDB operations
        with patch("ai_model.workflows.checkpointer.MongoDBSaver") as mock_saver_class:
            mock_saver = MagicMock(spec=BaseCheckpointSaver)
            mock_saver_class.return_value = mock_saver

            checkpointer = create_mongodb_checkpointer(
                client=mock_client,
                database="test_db",
            )

            assert checkpointer == mock_saver
            mock_saver_class.assert_called_once()

    @pytest.mark.integration
    def test_create_checkpointer_with_ttl(self) -> None:
        """Test checkpointer creation with custom TTL."""
        from ai_model.workflows.checkpointer import create_mongodb_checkpointer

        mock_client = MagicMock()

        with patch("ai_model.workflows.checkpointer.MongoDBSaver") as mock_saver_class:
            mock_saver = MagicMock(spec=BaseCheckpointSaver)
            mock_saver_class.return_value = mock_saver

            create_mongodb_checkpointer(
                client=mock_client,
                database="test_db",
                ttl_seconds=600,  # 10 minutes
            )

            # Verify TTL was passed
            call_kwargs = mock_saver_class.call_args[1]
            assert call_kwargs["ttl"] == 600

    @pytest.mark.integration
    def test_create_checkpointer_no_ttl(self) -> None:
        """Test checkpointer creation with TTL disabled."""
        from ai_model.workflows.checkpointer import create_mongodb_checkpointer

        mock_client = MagicMock()

        with patch("ai_model.workflows.checkpointer.MongoDBSaver") as mock_saver_class:
            mock_saver = MagicMock(spec=BaseCheckpointSaver)
            mock_saver_class.return_value = mock_saver

            create_mongodb_checkpointer(
                client=mock_client,
                database="test_db",
                ttl_seconds=0,
            )

            # Verify TTL is None (disabled)
            call_kwargs = mock_saver_class.call_args[1]
            assert call_kwargs["ttl"] is None

    @pytest.mark.integration
    def test_create_checkpointer_collection_names(self) -> None:
        """Test checkpointer uses correct collection names."""
        from ai_model.workflows.checkpointer import (
            CHECKPOINT_COLLECTION,
            CHECKPOINT_WRITES_COLLECTION,
            create_mongodb_checkpointer,
        )

        mock_client = MagicMock()

        with patch("ai_model.workflows.checkpointer.MongoDBSaver") as mock_saver_class:
            mock_saver = MagicMock(spec=BaseCheckpointSaver)
            mock_saver_class.return_value = mock_saver

            create_mongodb_checkpointer(
                client=mock_client,
                database="test_db",
            )

            call_kwargs = mock_saver_class.call_args[1]
            assert call_kwargs["checkpoint_collection_name"] == CHECKPOINT_COLLECTION
            assert call_kwargs["writes_collection_name"] == CHECKPOINT_WRITES_COLLECTION


class TestCleanupCheckpoints:
    """Tests for checkpoint cleanup function."""

    @pytest.mark.integration
    def test_cleanup_all_checkpoints(self) -> None:
        """Test cleaning up all checkpoints."""
        from ai_model.workflows.checkpointer import cleanup_checkpoints

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_checkpoints = MagicMock()
        mock_writes = MagicMock()

        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(
            side_effect=lambda name: mock_checkpoints if name == "checkpoints" else mock_writes
        )

        # Mock delete results
        mock_checkpoints.delete_many.return_value.deleted_count = 5
        mock_writes.delete_many.return_value.deleted_count = 3

        deleted = cleanup_checkpoints(
            client=mock_client,
            database="test_db",
        )

        assert deleted == 8
        mock_checkpoints.delete_many.assert_called_once_with({})
        mock_writes.delete_many.assert_called_once_with({})

    @pytest.mark.integration
    def test_cleanup_specific_thread(self) -> None:
        """Test cleaning up checkpoints for specific thread."""
        from ai_model.workflows.checkpointer import cleanup_checkpoints

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_checkpoints = MagicMock()
        mock_writes = MagicMock()

        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(
            side_effect=lambda name: mock_checkpoints if name == "checkpoints" else mock_writes
        )

        mock_checkpoints.delete_many.return_value.deleted_count = 2
        mock_writes.delete_many.return_value.deleted_count = 1

        deleted = cleanup_checkpoints(
            client=mock_client,
            database="test_db",
            thread_id="thread-123",
        )

        assert deleted == 3
        mock_checkpoints.delete_many.assert_called_once_with({"thread_id": "thread-123"})
        mock_writes.delete_many.assert_called_once_with({"thread_id": "thread-123"})

    @pytest.mark.integration
    def test_cleanup_nonexistent_thread(self) -> None:
        """Test cleaning up nonexistent thread returns 0."""
        from ai_model.workflows.checkpointer import cleanup_checkpoints

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_checkpoints = MagicMock()
        mock_writes = MagicMock()

        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(
            side_effect=lambda name: mock_checkpoints if name == "checkpoints" else mock_writes
        )

        mock_checkpoints.delete_many.return_value.deleted_count = 0
        mock_writes.delete_many.return_value.deleted_count = 0

        deleted = cleanup_checkpoints(
            client=mock_client,
            database="test_db",
            thread_id="nonexistent-thread",
        )

        assert deleted == 0


class TestCheckpointerWithWorkflow:
    """Tests for checkpointer integration with workflows."""

    @pytest.mark.integration
    def test_checkpointer_can_be_passed_to_workflow(self) -> None:
        """Test that checkpointer can be used with workflows."""
        from ai_model.workflows.extractor import ExtractorWorkflow

        mock_checkpointer = MagicMock(spec=BaseCheckpointSaver)
        mock_llm = MagicMock()

        workflow = ExtractorWorkflow(
            llm_gateway=mock_llm,
            checkpointer=mock_checkpointer,
        )

        assert workflow._checkpointer == mock_checkpointer

    @pytest.mark.integration
    def test_checkpointer_multiple_workflows(self) -> None:
        """Test that same checkpointer can be used by multiple workflows."""
        from ai_model.workflows.extractor import ExtractorWorkflow
        from ai_model.workflows.generator import GeneratorWorkflow

        mock_checkpointer = MagicMock(spec=BaseCheckpointSaver)
        mock_llm = MagicMock()
        mock_ranking = MagicMock()

        extractor = ExtractorWorkflow(
            llm_gateway=mock_llm,
            checkpointer=mock_checkpointer,
        )

        generator = GeneratorWorkflow(
            llm_gateway=mock_llm,
            ranking_service=mock_ranking,
            checkpointer=mock_checkpointer,
        )

        # Both should have the same checkpointer
        assert extractor._checkpointer == mock_checkpointer
        assert generator._checkpointer == mock_checkpointer

    @pytest.mark.integration
    def test_workflow_compiles_with_checkpointer(self) -> None:
        """Test that workflow compiles with checkpointer."""
        from ai_model.workflows.extractor import ExtractorWorkflow

        mock_checkpointer = MagicMock(spec=BaseCheckpointSaver)
        mock_llm = MagicMock()

        workflow = ExtractorWorkflow(
            llm_gateway=mock_llm,
            checkpointer=mock_checkpointer,
        )

        graph = workflow.compile()
        assert graph is not None

    @pytest.mark.integration
    def test_workflow_compiles_without_checkpointer(self) -> None:
        """Test that workflow compiles without checkpointer."""
        from ai_model.workflows.extractor import ExtractorWorkflow

        mock_llm = MagicMock()

        workflow = ExtractorWorkflow(
            llm_gateway=mock_llm,
            checkpointer=None,
        )

        graph = workflow.compile()
        assert graph is not None
