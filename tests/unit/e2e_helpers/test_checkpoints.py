"""Unit tests for E2E checkpoint helpers.

Story 0.6.16: AC3 - Checkpoint Test Helpers
"""

from unittest.mock import AsyncMock, patch

import pytest

from tests.e2e.helpers.checkpoints import (
    CheckpointDiagnostics,
    CheckpointFailure,
    checkpoint_documents_created,
    checkpoint_extraction_complete,
)


class TestCheckpointDiagnostics:
    """Tests for CheckpointDiagnostics dataclass."""

    def test_to_dict_returns_all_fields(self):
        """Given a CheckpointDiagnostics, to_dict returns all fields."""
        diagnostics = CheckpointDiagnostics(
            checkpoint_name="1-TEST",
            layer="Collection Model",
            timeout_seconds=15.0,
            elapsed_seconds=10.5,
            last_observed_value=0,
            expected_condition=">= 1 documents",
            mongodb_state={"count": 0},
            service_health={"Collection Model": "healthy"},
            recent_errors=["Error 1"],
            likely_issue="No documents",
            suggested_check="Check logs",
        )

        result = diagnostics.to_dict()

        assert result["checkpoint"] == "1-TEST"
        assert result["layer"] == "Collection Model"
        assert result["timeout_seconds"] == 15.0
        assert result["elapsed_seconds"] == 10.5
        assert result["mongodb_state"] == {"count": 0}
        assert result["likely_issue"] == "No documents"


class TestCheckpointFailure:
    """Tests for CheckpointFailure exception."""

    def test_checkpoint_failure_includes_diagnostics(self):
        """CheckpointFailure exception includes diagnostic dict."""
        diagnostics = CheckpointDiagnostics(
            checkpoint_name="1-TEST",
            layer="Collection Model",
            timeout_seconds=15.0,
            elapsed_seconds=15.0,
            last_observed_value=0,
            expected_condition=">= 1",
        )

        error = CheckpointFailure("Test failed", diagnostics)

        assert error.diagnostics == diagnostics
        assert "Test failed" in str(error)
        assert "Diagnostics:" in str(error)

    def test_checkpoint_failure_diagnostics_accessible(self):
        """CheckpointFailure.diagnostics is accessible for programmatic use."""
        diagnostics = CheckpointDiagnostics(
            checkpoint_name="2-EVENT",
            layer="AI Model",
            timeout_seconds=10.0,
            elapsed_seconds=10.0,
            last_observed_value=None,
            expected_condition="event received",
            likely_issue="Event not published",
            suggested_check="Check DAPR",
        )

        error = CheckpointFailure("Event not found", diagnostics)

        assert error.diagnostics.likely_issue == "Event not published"
        assert error.diagnostics.suggested_check == "Check DAPR"


class TestCheckpointDocumentsCreated:
    """Tests for checkpoint_documents_created function."""

    @pytest.mark.asyncio
    async def test_checkpoint_documents_created_returns_docs_on_success(self):
        """Given documents exist, checkpoint returns them."""
        mock_mongodb = AsyncMock()
        mock_mongodb.find_documents = AsyncMock(return_value=[{"_id": "doc1", "ingestion": {"source_id": "test"}}])

        result = await checkpoint_documents_created(
            mock_mongodb,
            source_id="test",
            min_count=1,
            timeout=1.0,
        )

        assert len(result) == 1
        assert result[0]["_id"] == "doc1"

    @pytest.mark.asyncio
    async def test_checkpoint_documents_created_raises_on_timeout(self):
        """Given no documents, checkpoint raises CheckpointFailure."""
        mock_mongodb = AsyncMock()
        mock_mongodb.find_documents = AsyncMock(return_value=[])

        with (
            patch("tests.e2e.helpers.checkpoints._get_collection_count", return_value=0),
            patch("tests.e2e.helpers.checkpoints._get_service_health", return_value={}),
            patch("tests.e2e.helpers.checkpoints._get_recent_errors", return_value=[]),
            pytest.raises(CheckpointFailure) as exc_info,
        ):
            await checkpoint_documents_created(
                mock_mongodb,
                source_id="test",
                min_count=1,
                timeout=0.1,
                poll_interval=0.05,
            )

        assert "CHECKPOINT" in str(exc_info.value)
        assert exc_info.value.diagnostics.layer == "Collection Model"


class TestCheckpointExtractionComplete:
    """Tests for checkpoint_extraction_complete function."""

    @pytest.mark.asyncio
    async def test_checkpoint_extraction_complete_returns_doc_on_success(self):
        """Given extraction complete, checkpoint returns document."""
        mock_mongodb = AsyncMock()
        mock_mongodb.find_documents = AsyncMock(
            return_value=[
                {
                    "_id": "doc1",
                    "ingestion": {"source_id": "test"},
                    "extraction": {"status": "complete", "data": {"temp": 25}},
                }
            ]
        )

        result = await checkpoint_extraction_complete(
            mock_mongodb,
            source_id="test",
            timeout=1.0,
        )

        assert result["extraction"]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_checkpoint_extraction_complete_detects_failed_status(self):
        """Given extraction.status='failed', raises immediately."""
        mock_mongodb = AsyncMock()
        mock_mongodb.find_documents = AsyncMock(
            return_value=[
                {
                    "_id": "doc1",
                    "ingestion": {"source_id": "test"},
                    "extraction": {"status": "failed", "error_message": "LLM error"},
                }
            ]
        )

        with (
            patch("tests.e2e.helpers.checkpoints._get_service_health", return_value={}),
            patch("tests.e2e.helpers.checkpoints._get_recent_errors", return_value=[]),
            pytest.raises(CheckpointFailure) as exc_info,
        ):
            await checkpoint_extraction_complete(
                mock_mongodb,
                source_id="test",
                timeout=1.0,
            )

        assert "failed" in exc_info.value.diagnostics.likely_issue.lower()
        assert "LLM error" in exc_info.value.diagnostics.likely_issue
