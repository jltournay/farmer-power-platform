"""Unit tests for SourceSummary model.

Story 0.6.1: Shared Pydantic Models in fp-common
"""

from fp_common.models import SourceSummary


class TestSourceSummary:
    """Tests for SourceSummary model."""

    def test_create_valid_source_summary(self) -> None:
        """Test creating a valid SourceSummary."""
        summary = SourceSummary(
            source_id="qc-analyzer-result",
            display_name="QC Analyzer Results",
            description="Quality control results from QC Analyzer CV system",
            enabled=True,
            ingestion_mode="blob_trigger",
            ingestion_schedule=None,
        )

        assert summary.source_id == "qc-analyzer-result"
        assert summary.display_name == "QC Analyzer Results"
        assert summary.description == "Quality control results from QC Analyzer CV system"
        assert summary.enabled is True
        assert summary.ingestion_mode == "blob_trigger"
        assert summary.ingestion_schedule is None

    def test_source_summary_with_schedule(self) -> None:
        """Test SourceSummary with scheduled pull mode."""
        summary = SourceSummary(
            source_id="weather-data",
            display_name="Weather Data",
            description="Weather data from Open-Meteo API",
            enabled=True,
            ingestion_mode="scheduled_pull",
            ingestion_schedule="0 6 * * *",
        )

        assert summary.source_id == "weather-data"
        assert summary.ingestion_mode == "scheduled_pull"
        assert summary.ingestion_schedule == "0 6 * * *"

    def test_source_summary_defaults(self) -> None:
        """Test SourceSummary default values."""
        summary = SourceSummary(
            source_id="test-source",
            display_name="Test Source",
        )

        assert summary.description == ""
        assert summary.enabled is True
        assert summary.ingestion_mode == "unknown"
        assert summary.ingestion_schedule is None

    def test_source_summary_disabled(self) -> None:
        """Test SourceSummary with disabled state."""
        summary = SourceSummary(
            source_id="deprecated-source",
            display_name="Deprecated Source",
            enabled=False,
        )

        assert summary.enabled is False

    def test_source_summary_serialization(self) -> None:
        """Test SourceSummary serialization to dict."""
        summary = SourceSummary(
            source_id="qc-analyzer-result",
            display_name="QC Analyzer Results",
            description="Quality control results",
            enabled=True,
            ingestion_mode="blob_trigger",
        )

        data = summary.model_dump()

        assert data["source_id"] == "qc-analyzer-result"
        assert data["display_name"] == "QC Analyzer Results"
        assert data["enabled"] is True
        assert "ingestion_mode" in data
