"""Manifest models for ZIP content processing.

This module defines Pydantic models for the Generic ZIP Manifest Format
as specified in collection-model-architecture.md. These models are used
by ZipExtractionProcessor to parse and validate manifest.json files.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ManifestFile(BaseModel):
    """File entry in manifest document.

    Attributes:
        path: Path to the file within the ZIP archive.
        role: File role (image, metadata, primary, thumbnail, attachment).
        mime_type: Optional MIME type of the file.
        size_bytes: Optional size of the file in bytes.
    """

    path: str
    role: str  # image, metadata, primary, thumbnail, attachment
    mime_type: str | None = None
    size_bytes: int | None = None


class ManifestDocument(BaseModel):
    """Document entry in manifest.

    Each document represents a logical unit (e.g., a leaf image with its metadata).
    Multiple files can belong to a single document, distinguished by role.

    Attributes:
        document_id: Local identifier within the manifest (e.g., "leaf_001").
        files: List of files belonging to this document.
        attributes: Optional pre-extracted attributes from the source.
    """

    document_id: str
    files: list[ManifestFile]
    attributes: dict[str, Any] | None = None


class ZipManifest(BaseModel):
    """Generic ZIP manifest following collection-model-architecture.md spec.

    The manifest is the authoritative source of information for ZIP content.
    It provides structured data that eliminates the need for AI extraction.

    Attributes:
        manifest_version: Version of the manifest format (default "1.0").
        source_id: ID of the source configuration that produced this ZIP.
        created_at: When the ZIP was created by the source system.
        linkage: Cross-reference fields for entity relationships (copied AS-IS).
        documents: List of documents in this ZIP.
        payload: Batch-level domain-specific data (merged into each document).
    """

    manifest_version: str = "1.0"
    source_id: str
    created_at: datetime

    # Cross-reference fields for entity relationships
    linkage: dict[str, Any] = Field(default_factory=dict)

    # Documents in this ZIP
    documents: list[ManifestDocument]

    # Batch-level domain-specific data
    payload: dict[str, Any] = Field(default_factory=dict)
