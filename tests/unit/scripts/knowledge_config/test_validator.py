"""Tests for fp_knowledge.validator module."""

from pathlib import Path

from fp_knowledge.models import KnowledgeDomain
from fp_knowledge.validator import (
    VALID_FILE_TYPES,
    validate_document_dict,
    validate_document_yaml,
)


class TestValidateDocumentYaml:
    """Tests for validate_document_yaml function."""

    def test_valid_yaml_with_content(self, sample_yaml_file: Path) -> None:
        """Test validation of a valid YAML file with inline content."""
        result = validate_document_yaml(sample_yaml_file)

        assert result.is_valid is True
        assert result.errors == []
        assert result.document is not None
        assert result.document.document_id == "blister-blight-guide"
        assert result.document.domain == KnowledgeDomain.PLANT_DISEASES

    def test_file_not_found(self) -> None:
        """Test validation when file does not exist."""
        result = validate_document_yaml(Path("/nonexistent/file.yaml"))

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()

    def test_malformed_yaml(self, malformed_yaml_file: Path) -> None:
        """Test validation of malformed YAML syntax."""
        result = validate_document_yaml(malformed_yaml_file)

        assert result.is_valid is False
        assert any("yaml" in e.lower() for e in result.errors)

    def test_missing_required_fields(self, invalid_yaml_file: Path) -> None:
        """Test validation when required fields are missing."""
        result = validate_document_yaml(invalid_yaml_file)

        assert result.is_valid is False
        # Should report missing title and domain
        assert any("title" in e.lower() for e in result.errors)
        assert any("domain" in e.lower() for e in result.errors)

    def test_invalid_domain(self, tmp_path: Path) -> None:
        """Test validation with invalid domain value."""
        yaml_content = """document_id: test
title: Test Document
domain: invalid_domain
content: Test content
"""
        yaml_file = tmp_path / "invalid_domain.yaml"
        yaml_file.write_text(yaml_content)

        result = validate_document_yaml(yaml_file)

        assert result.is_valid is False
        assert any("domain" in e.lower() for e in result.errors)

    def test_neither_content_nor_file(self, tmp_path: Path) -> None:
        """Test validation when neither content nor file is provided."""
        yaml_content = """document_id: test
title: Test Document
domain: plant_diseases
"""
        yaml_file = tmp_path / "no_content.yaml"
        yaml_file.write_text(yaml_content)

        result = validate_document_yaml(yaml_file)

        assert result.is_valid is False
        assert any("content" in e.lower() and "file" in e.lower() for e in result.errors)

    def test_both_content_and_file(self, tmp_path: Path) -> None:
        """Test validation when both content and file are provided."""
        yaml_content = """document_id: test
title: Test Document
domain: plant_diseases
content: Inline content
file: guide.pdf
"""
        yaml_file = tmp_path / "both.yaml"
        yaml_file.write_text(yaml_content)

        result = validate_document_yaml(yaml_file)

        assert result.is_valid is False
        assert any("both" in e.lower() for e in result.errors)

    def test_invalid_file_type(self, tmp_path: Path) -> None:
        """Test validation with invalid file type."""
        yaml_content = """document_id: test
title: Test Document
domain: plant_diseases
file: guide.exe
"""
        yaml_file = tmp_path / "invalid_type.yaml"
        yaml_file.write_text(yaml_content)

        result = validate_document_yaml(yaml_file)

        assert result.is_valid is False
        assert any(".exe" in e.lower() for e in result.errors)

    def test_valid_file_types(self) -> None:
        """Test that expected file types are valid."""
        assert ".pdf" in VALID_FILE_TYPES
        assert ".md" in VALID_FILE_TYPES
        assert ".markdown" in VALID_FILE_TYPES
        assert ".txt" in VALID_FILE_TYPES
        assert ".docx" in VALID_FILE_TYPES

    def test_file_not_found_warning(self, tmp_path: Path) -> None:
        """Test that warning is added when referenced file doesn't exist."""
        yaml_content = """document_id: test
title: Test Document
domain: plant_diseases
file: nonexistent.pdf
"""
        yaml_file = tmp_path / "missing_ref.yaml"
        yaml_file.write_text(yaml_content)

        result = validate_document_yaml(yaml_file)

        # Should still be valid (file existence is a warning, not error)
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "not found" in result.warnings[0].lower()

    def test_default_metadata(self, tmp_path: Path) -> None:
        """Test that default metadata is applied when not provided."""
        yaml_content = """document_id: test
title: Test Document
domain: plant_diseases
content: Test content
"""
        yaml_file = tmp_path / "no_metadata.yaml"
        yaml_file.write_text(yaml_content)

        result = validate_document_yaml(yaml_file)

        assert result.is_valid is True
        assert result.document is not None
        assert result.document.metadata.author == "unknown"


class TestValidateDocumentDict:
    """Tests for validate_document_dict function."""

    def test_valid_dict_with_content(self) -> None:
        """Test validation of valid dictionary with inline content."""
        data = {
            "document_id": "test-doc",
            "title": "Test Document",
            "domain": "plant_diseases",
            "content": "Test content",
        }

        result = validate_document_dict(data)

        assert result.is_valid is True
        assert result.document is not None
        assert result.document.document_id == "test-doc"

    def test_invalid_data_type(self) -> None:
        """Test validation with non-dict input."""
        result = validate_document_dict("not a dict")  # type: ignore

        assert result.is_valid is False
        assert any("dictionary" in e.lower() for e in result.errors)

    def test_missing_required_fields(self) -> None:
        """Test validation when required fields are missing."""
        data = {
            "document_id": "test",
        }

        result = validate_document_dict(data)

        assert result.is_valid is False
        assert any("title" in e.lower() for e in result.errors)

    def test_default_metadata_applied(self) -> None:
        """Test that default metadata is applied."""
        data = {
            "document_id": "test-doc",
            "title": "Test Document",
            "domain": "plant_diseases",
            "content": "Test content",
        }

        result = validate_document_dict(data)

        assert result.is_valid is True
        assert result.document is not None
        assert result.document.metadata.author == "unknown"
