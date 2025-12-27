"""Tests for deduplication behavior in processors.

Tests verify that ProcessorResult correctly reports duplicate detection
via the is_duplicate field.
"""

from collection_model.processors.base import ProcessorResult


class TestProcessorResultDuplication:
    """Tests for ProcessorResult is_duplicate field."""

    def test_processor_result_is_duplicate_default_false(self) -> None:
        """Test that is_duplicate defaults to False."""
        result = ProcessorResult(success=True)
        assert result.is_duplicate is False

    def test_processor_result_is_duplicate_can_be_set_true(self) -> None:
        """Test that is_duplicate can be set to True."""
        result = ProcessorResult(success=True, is_duplicate=True)
        assert result.is_duplicate is True

    def test_processor_result_duplicate_with_success_true(self) -> None:
        """Test that duplicate detection is a success case."""
        # Duplicate is not an error - it's expected behavior
        result = ProcessorResult(success=True, is_duplicate=True)
        assert result.success is True
        assert result.is_duplicate is True
        assert result.error_message is None
        assert result.error_type is None

    def test_processor_result_stored_document(self) -> None:
        """Test ProcessorResult for successfully stored document."""
        result = ProcessorResult(
            success=True,
            document_id="doc-123",
            extracted_data={"field": "value"},
            is_duplicate=False,
        )
        assert result.success is True
        assert result.document_id == "doc-123"
        assert result.is_duplicate is False
        assert result.extracted_data == {"field": "value"}

    def test_processor_result_failed_not_duplicate(self) -> None:
        """Test that failed results are not marked as duplicates."""
        result = ProcessorResult(
            success=False,
            error_message="Processing failed",
            error_type="extraction",
        )
        assert result.success is False
        assert result.is_duplicate is False
        assert result.error_message == "Processing failed"

    def test_processor_result_serialization(self) -> None:
        """Test ProcessorResult serialization includes is_duplicate."""
        result = ProcessorResult(success=True, is_duplicate=True)
        serialized = result.model_dump()

        assert "is_duplicate" in serialized
        assert serialized["is_duplicate"] is True
        assert serialized["success"] is True
