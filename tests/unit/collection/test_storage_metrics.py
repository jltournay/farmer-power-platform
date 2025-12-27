"""Tests for StorageMetrics OpenTelemetry integration.

Tests verify that storage metrics are correctly recorded via OpenTelemetry
counters for document storage and duplicate detection.
"""

from unittest.mock import MagicMock, patch


class TestStorageMetrics:
    """Tests for StorageMetrics class."""

    @patch("collection_model.infrastructure.storage_metrics.documents_counter")
    @patch("collection_model.infrastructure.storage_metrics.storage_bytes_counter")
    def test_record_stored_increments_counters(
        self,
        mock_bytes_counter: MagicMock,
        mock_docs_counter: MagicMock,
    ) -> None:
        """Test that record_stored increments both counters with correct labels."""
        from collection_model.infrastructure.storage_metrics import StorageMetrics

        # Act
        StorageMetrics.record_stored("test-source", 1024)

        # Assert
        mock_docs_counter.add.assert_called_once_with(1, {"source_id": "test-source", "status": "stored"})
        mock_bytes_counter.add.assert_called_once_with(1024, {"source_id": "test-source"})

    @patch("collection_model.infrastructure.storage_metrics.documents_counter")
    @patch("collection_model.infrastructure.storage_metrics.storage_bytes_counter")
    def test_record_stored_with_zero_bytes(
        self,
        mock_bytes_counter: MagicMock,
        mock_docs_counter: MagicMock,
    ) -> None:
        """Test record_stored handles zero-byte documents."""
        from collection_model.infrastructure.storage_metrics import StorageMetrics

        # Act
        StorageMetrics.record_stored("empty-source", 0)

        # Assert
        mock_docs_counter.add.assert_called_once_with(1, {"source_id": "empty-source", "status": "stored"})
        mock_bytes_counter.add.assert_called_once_with(0, {"source_id": "empty-source"})

    @patch("collection_model.infrastructure.storage_metrics.documents_counter")
    def test_record_duplicate_increments_counter(
        self,
        mock_docs_counter: MagicMock,
    ) -> None:
        """Test that record_duplicate increments counter with status=duplicate."""
        from collection_model.infrastructure.storage_metrics import StorageMetrics

        # Act
        StorageMetrics.record_duplicate("qc-analyzer-exceptions")

        # Assert
        mock_docs_counter.add.assert_called_once_with(1, {"source_id": "qc-analyzer-exceptions", "status": "duplicate"})

    @patch("collection_model.infrastructure.storage_metrics.documents_counter")
    @patch("collection_model.infrastructure.storage_metrics.storage_bytes_counter")
    def test_record_duplicate_does_not_increment_bytes(
        self,
        mock_bytes_counter: MagicMock,
        mock_docs_counter: MagicMock,
    ) -> None:
        """Test that record_duplicate does not increment bytes counter."""
        from collection_model.infrastructure.storage_metrics import StorageMetrics

        # Act
        StorageMetrics.record_duplicate("test-source")

        # Assert
        mock_bytes_counter.add.assert_not_called()

    @patch("collection_model.infrastructure.storage_metrics.documents_counter")
    @patch("collection_model.infrastructure.storage_metrics.storage_bytes_counter")
    def test_multiple_sources_tracked_separately(
        self,
        mock_bytes_counter: MagicMock,
        mock_docs_counter: MagicMock,
    ) -> None:
        """Test that multiple sources are tracked with their own labels."""
        from collection_model.infrastructure.storage_metrics import StorageMetrics

        # Act
        StorageMetrics.record_stored("source-a", 100)
        StorageMetrics.record_stored("source-b", 200)
        StorageMetrics.record_duplicate("source-a")

        # Assert - verify all three calls happened with correct labels
        assert mock_docs_counter.add.call_count == 3
        calls = mock_docs_counter.add.call_args_list

        assert calls[0] == ((1, {"source_id": "source-a", "status": "stored"}),)
        assert calls[1] == ((1, {"source_id": "source-b", "status": "stored"}),)
        assert calls[2] == ((1, {"source_id": "source-a", "status": "duplicate"}),)
