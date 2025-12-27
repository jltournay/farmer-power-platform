"""Tests for Collection MCP Blob URL Generator."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from collection_mcp.infrastructure.blob_url_generator import (
    BlobUrlGenerator,
    BlobUrlGeneratorError,
)


class TestBlobUriParsing:
    """Tests for blob URI parsing."""

    @pytest.fixture
    def generator(self) -> BlobUrlGenerator:
        """Create a blob URL generator."""
        return BlobUrlGenerator(
            account_name="teststorage",
            account_key="test_key_base64",
            validity_hours=1,
        )

    def test_parse_https_uri(self, generator: BlobUrlGenerator) -> None:
        """Verify parsing of https:// blob URIs."""
        blob_uri = "https://teststorage.blob.core.windows.net/container/path/to/blob.jpg"
        container, blob_name = generator._parse_blob_uri(blob_uri)

        assert container == "container"
        assert blob_name == "path/to/blob.jpg"

    def test_parse_https_uri_single_level(self, generator: BlobUrlGenerator) -> None:
        """Verify parsing of https:// blob URIs with single-level path."""
        blob_uri = "https://teststorage.blob.core.windows.net/container/file.jpg"
        container, blob_name = generator._parse_blob_uri(blob_uri)

        assert container == "container"
        assert blob_name == "file.jpg"

    def test_parse_wasbs_uri(self, generator: BlobUrlGenerator) -> None:
        """Verify parsing of wasbs:// blob URIs."""
        blob_uri = "wasbs://container@teststorage.blob.core.windows.net/path/to/blob.jpg"
        container, blob_name = generator._parse_blob_uri(blob_uri)

        assert container == "container"
        assert blob_name == "path/to/blob.jpg"

    def test_parse_unsupported_scheme_raises(self, generator: BlobUrlGenerator) -> None:
        """Verify unsupported schemes raise error."""
        with pytest.raises(BlobUrlGeneratorError) as exc_info:
            generator._parse_blob_uri("file:///path/to/file.jpg")

        assert "Unsupported blob URI scheme" in str(exc_info.value)

    def test_parse_invalid_https_uri_raises(self, generator: BlobUrlGenerator) -> None:
        """Verify invalid https URIs raise error."""
        with pytest.raises(BlobUrlGeneratorError):
            # Missing blob path - only container
            generator._parse_blob_uri("https://teststorage.blob.core.windows.net/container")


class TestSasUrlGeneration:
    """Tests for SAS URL generation."""

    @pytest.fixture
    def generator(self) -> BlobUrlGenerator:
        """Create a blob URL generator."""
        return BlobUrlGenerator(
            account_name="teststorage",
            account_key="dGVzdF9rZXk=",  # base64 encoded "test_key"
            validity_hours=1,
        )

    def test_generate_sas_url_returns_url_with_token(self, generator: BlobUrlGenerator) -> None:
        """Verify generate_sas_url returns URL with SAS token."""
        with patch("collection_mcp.infrastructure.blob_url_generator.generate_blob_sas") as mock_sas:
            mock_sas.return_value = "sv=2021-06-08&se=2024-12-25&sr=b&sp=r&sig=test"

            result = generator.generate_sas_url("https://teststorage.blob.core.windows.net/container/file.jpg")

            assert "https://teststorage.blob.core.windows.net/container/file.jpg" in result
            assert "?" in result
            assert "sig=" in result

    def test_generate_sas_url_uses_account_credentials(self, generator: BlobUrlGenerator) -> None:
        """Verify SAS generation uses correct account credentials."""
        with patch("collection_mcp.infrastructure.blob_url_generator.generate_blob_sas") as mock_sas:
            mock_sas.return_value = "token"

            generator.generate_sas_url("https://teststorage.blob.core.windows.net/container/file.jpg")

            mock_sas.assert_called_once()
            call_kwargs = mock_sas.call_args[1]
            assert call_kwargs["account_name"] == "teststorage"
            assert call_kwargs["container_name"] == "container"
            assert call_kwargs["blob_name"] == "file.jpg"
            assert call_kwargs["account_key"] == "dGVzdF9rZXk="

    def test_generate_sas_url_uses_custom_validity(self, generator: BlobUrlGenerator) -> None:
        """Verify SAS generation respects custom validity hours."""
        with patch("collection_mcp.infrastructure.blob_url_generator.generate_blob_sas") as mock_sas:
            mock_sas.return_value = "token"

            generator.generate_sas_url(
                "https://teststorage.blob.core.windows.net/container/file.jpg",
                validity_hours=2,
            )

            call_kwargs = mock_sas.call_args[1]
            expiry = call_kwargs["expiry"]
            # Verify expiry is approximately 2 hours from now
            now = datetime.now(timezone.utc)
            expected_expiry = now + timedelta(hours=2)
            assert abs((expiry - expected_expiry).total_seconds()) < 10  # Within 10 seconds

    def test_generate_sas_url_returns_original_when_not_configured(self) -> None:
        """Verify original URI returned when generator not configured."""
        generator = BlobUrlGenerator(
            account_name="",
            account_key="",
            validity_hours=1,
        )

        blob_uri = "https://storage.blob.core.windows.net/container/file.jpg"
        result = generator.generate_sas_url(blob_uri)

        assert result == blob_uri


class TestEnrichFilesWithSas:
    """Tests for enriching files with SAS URLs."""

    @pytest.fixture
    def generator(self) -> BlobUrlGenerator:
        """Create a blob URL generator."""
        return BlobUrlGenerator(
            account_name="teststorage",
            account_key="dGVzdF9rZXk=",
            validity_hours=1,
        )

    def test_enrich_files_adds_sas_url(self, generator: BlobUrlGenerator) -> None:
        """Verify enrich_files_with_sas adds sas_url to files."""
        with patch("collection_mcp.infrastructure.blob_url_generator.generate_blob_sas") as mock_sas:
            mock_sas.return_value = "token"

            files = [
                {
                    "blob_uri": "https://teststorage.blob.core.windows.net/container/file1.jpg",
                    "role": "image",
                },
                {
                    "blob_uri": "https://teststorage.blob.core.windows.net/container/file2.jpg",
                    "role": "thumbnail",
                },
            ]

            result = generator.enrich_files_with_sas(files)

            assert len(result) == 2
            assert all("sas_url" in f for f in result)
            assert all(f["sas_url"] is not None for f in result)
            # Verify original fields preserved
            assert result[0]["role"] == "image"
            assert result[1]["role"] == "thumbnail"

    def test_enrich_files_preserves_files_without_blob_uri(self, generator: BlobUrlGenerator) -> None:
        """Verify files without blob_uri are preserved."""
        files = [
            {"name": "metadata.json", "role": "metadata"},
        ]

        result = generator.enrich_files_with_sas(files)

        assert len(result) == 1
        assert result[0]["name"] == "metadata.json"
        assert "sas_url" not in result[0]

    def test_enrich_files_handles_empty_list(self, generator: BlobUrlGenerator) -> None:
        """Verify empty file list returns empty list."""
        result = generator.enrich_files_with_sas([])

        assert result == []

    def test_enrich_files_handles_sas_generation_failure(self, generator: BlobUrlGenerator) -> None:
        """Verify SAS generation failure sets sas_url to None."""
        with patch.object(generator, "generate_sas_url") as mock_generate:
            mock_generate.side_effect = BlobUrlGeneratorError("Failed")

            files = [
                {"blob_uri": "invalid://uri", "role": "image"},
            ]

            result = generator.enrich_files_with_sas(files)

            assert len(result) == 1
            assert result[0]["sas_url"] is None
            assert result[0]["blob_uri"] == "invalid://uri"
