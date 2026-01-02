#!/usr/bin/env python3
"""Generate ZIP test fixtures for Story 0.4.9 (ZIP Processor E2E Tests).

This script creates all ZIP fixtures required for E2E testing of the
ZipExtractionProcessor. Each fixture tests a specific acceptance criterion.

Fixtures created:
- valid_exception_batch.zip: Valid ZIP with manifest and 3 exception images (AC1, AC2, AC3)
- corrupt_zip.zip: Intentionally corrupt ZIP file (AC4)
- missing_manifest.zip: ZIP without manifest.json (AC5)
- invalid_manifest_schema.zip: ZIP with malformed manifest (AC6)
- path_traversal_attempt.zip: ZIP with path traversal attempt (AC7)

Usage:
    python tests/e2e/fixtures/generate_zip_fixtures.py

Run from repository root.
"""

import io
import json
import zipfile
from pathlib import Path

# Fixture output directory
FIXTURES_DIR = Path(__file__).parent

# Valid manifest template following Generic ZIP Manifest Format
# See: services/collection-model/src/collection_model/domain/manifest.py
VALID_MANIFEST = {
    "manifest_version": "1.0",
    "source_id": "e2e-exception-images-zip",
    "created_at": "2025-01-01T00:00:00Z",
    "linkage": {
        "plantation_id": "PLT-E2E-001",
        "batch_id": "BATCH-E2E-001",
        "batch_result_ref": "QC-RESULT-001",
    },
    "payload": {
        "exception_count": 3,
        "grading_session_id": "GS-001",
    },
    "documents": [
        {
            "document_id": "exception_001",
            "files": [
                {
                    "path": "images/exception_001.jpg",
                    "role": "image",
                    "mime_type": "image/jpeg",
                },
                {
                    "path": "metadata/exception_001.json",
                    "role": "metadata",
                },
            ],
            "attributes": {
                "exception_type": "foreign_matter",
                "severity": "high",
                "notes": "Detected debris in sample",
            },
        },
        {
            "document_id": "exception_002",
            "files": [
                {
                    "path": "images/exception_002.jpg",
                    "role": "image",
                    "mime_type": "image/jpeg",
                },
                {
                    "path": "metadata/exception_002.json",
                    "role": "metadata",
                },
            ],
            "attributes": {
                "exception_type": "discoloration",
                "severity": "medium",
                "notes": "Unusual leaf color detected",
            },
        },
        {
            "document_id": "exception_003",
            "files": [
                {
                    "path": "images/exception_003.jpg",
                    "role": "image",
                    "mime_type": "image/jpeg",
                },
                {
                    "path": "metadata/exception_003.json",
                    "role": "metadata",
                },
            ],
            "attributes": {
                "exception_type": "pest_damage",
                "severity": "high",
                "notes": "Visible pest damage on leaf",
            },
        },
    ],
}


def create_dummy_jpeg(width: int = 10, height: int = 10) -> bytes:
    """Create a minimal valid JPEG image.

    Args:
        width: Unused (kept for API compatibility)
        height: Unused (kept for API compatibility)

    Returns:
        A valid minimal JPEG file that can be extracted and stored.
    """
    # Minimal JPEG: Start of Image, JFIF header, minimal DQT, SOF0, DHT, SOS, EOI
    # This is a valid minimal JPEG that will pass MIME type detection
    return bytes(
        [
            0xFF,
            0xD8,  # SOI
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,  # JFIF
            0xFF,
            0xDB,
            0x00,
            0x43,
            0x00,  # DQT
            0x08,
            0x06,
            0x06,
            0x07,
            0x06,
            0x05,
            0x08,
            0x07,
            0x07,
            0x07,
            0x09,
            0x09,
            0x08,
            0x0A,
            0x0C,
            0x14,
            0x0D,
            0x0C,
            0x0B,
            0x0B,
            0x0C,
            0x19,
            0x12,
            0x13,
            0x0F,
            0x14,
            0x1D,
            0x1A,
            0x1F,
            0x1E,
            0x1D,
            0x1A,
            0x1C,
            0x1C,
            0x20,
            0x24,
            0x2E,
            0x27,
            0x20,
            0x22,
            0x2C,
            0x23,
            0x1C,
            0x1C,
            0x28,
            0x37,
            0x29,
            0x2C,
            0x30,
            0x31,
            0x34,
            0x34,
            0x34,
            0x1F,
            0x27,
            0x39,
            0x3D,
            0x38,
            0x32,
            0x3C,
            0x2E,
            0x33,
            0x34,
            0x32,
            0xFF,
            0xC0,
            0x00,
            0x0B,
            0x08,
            0x00,
            0x01,
            0x00,
            0x01,
            0x01,
            0x01,
            0x11,
            0x00,  # SOF0
            0xFF,
            0xC4,
            0x00,
            0x1F,
            0x00,
            0x00,
            0x01,
            0x05,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x02,
            0x03,
            0x04,
            0x05,
            0x06,
            0x07,
            0x08,
            0x09,
            0x0A,
            0x0B,  # DHT
            0xFF,
            0xC4,
            0x00,
            0xB5,
            0x10,
            0x00,
            0x02,
            0x01,
            0x03,
            0x03,
            0x02,
            0x04,
            0x03,
            0x05,
            0x05,
            0x04,
            0x04,
            0x00,
            0x00,
            0x01,
            0x7D,
            0x01,
            0x02,
            0x03,
            0x00,
            0x04,
            0x11,
            0x05,
            0x12,
            0x21,
            0x31,
            0x41,
            0x06,
            0x13,
            0x51,
            0x61,
            0x07,
            0x22,
            0x71,
            0x14,
            0x32,
            0x81,
            0x91,
            0xA1,
            0x08,
            0x23,
            0x42,
            0xB1,
            0xC1,
            0x15,
            0x52,
            0xD1,
            0xF0,
            0x24,
            0x33,
            0x62,
            0x72,
            0x82,
            0x09,
            0x0A,
            0x16,
            0x17,
            0x18,
            0x19,
            0x1A,
            0x25,
            0x26,
            0x27,
            0x28,
            0x29,
            0x2A,
            0x34,
            0x35,
            0x36,
            0x37,
            0x38,
            0x39,
            0x3A,
            0x43,
            0x44,
            0x45,
            0x46,
            0x47,
            0x48,
            0x49,
            0x4A,
            0x53,
            0x54,
            0x55,
            0x56,
            0x57,
            0x58,
            0x59,
            0x5A,
            0x63,
            0x64,
            0x65,
            0x66,
            0x67,
            0x68,
            0x69,
            0x6A,
            0x73,
            0x74,
            0x75,
            0x76,
            0x77,
            0x78,
            0x79,
            0x7A,
            0x83,
            0x84,
            0x85,
            0x86,
            0x87,
            0x88,
            0x89,
            0x8A,
            0x92,
            0x93,
            0x94,
            0x95,
            0x96,
            0x97,
            0x98,
            0x99,
            0x9A,
            0xA2,
            0xA3,
            0xA4,
            0xA5,
            0xA6,
            0xA7,
            0xA8,
            0xA9,
            0xAA,
            0xB2,
            0xB3,
            0xB4,
            0xB5,
            0xB6,
            0xB7,
            0xB8,
            0xB9,
            0xBA,
            0xC2,
            0xC3,
            0xC4,
            0xC5,
            0xC6,
            0xC7,
            0xC8,
            0xC9,
            0xCA,
            0xD2,
            0xD3,
            0xD4,
            0xD5,
            0xD6,
            0xD7,
            0xD8,
            0xD9,
            0xDA,
            0xE1,
            0xE2,
            0xE3,
            0xE4,
            0xE5,
            0xE6,
            0xE7,
            0xE8,
            0xE9,
            0xEA,
            0xF1,
            0xF2,
            0xF3,
            0xF4,
            0xF5,
            0xF6,
            0xF7,
            0xF8,
            0xF9,
            0xFA,  # DHT
            0xFF,
            0xDA,
            0x00,
            0x08,
            0x01,
            0x01,
            0x00,
            0x00,
            0x3F,
            0x00,
            0x7F,
            0xFF,  # SOS
            0xFF,
            0xD9,  # EOI
        ]
    )


def create_metadata_json(doc_id: str, exception_type: str, severity: str) -> str:
    """Create metadata JSON for an exception document."""
    return json.dumps(
        {
            "document_id": doc_id,
            "exception_type": exception_type,
            "severity": severity,
            "capture_timestamp": "2025-01-01T10:00:00Z",
            "device_id": "CAM-001",
        },
        indent=2,
    )


def create_valid_exception_batch_zip() -> bytes:
    """Create valid_exception_batch.zip with manifest and 3 exception images.

    Tests: AC1 (Valid ZIP with Manifest), AC2 (File Extraction), AC3 (MCP Query)
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write manifest
        zf.writestr("manifest.json", json.dumps(VALID_MANIFEST, indent=2))

        # Write exception images and metadata
        for doc in VALID_MANIFEST["documents"]:
            doc_id = doc["document_id"]
            attrs = doc["attributes"]

            # Write image file
            for file_entry in doc["files"]:
                if file_entry["role"] == "image":
                    zf.writestr(file_entry["path"], create_dummy_jpeg())
                elif file_entry["role"] == "metadata":
                    zf.writestr(
                        file_entry["path"],
                        create_metadata_json(
                            doc_id,
                            attrs["exception_type"],
                            attrs["severity"],
                        ),
                    )

    return buffer.getvalue()


def create_corrupt_zip() -> bytes:
    """Create corrupt_zip.zip - intentionally corrupt ZIP file.

    Tests: AC4 (Corrupt ZIP Handling)

    Creates data that starts like a ZIP but has invalid structure.
    """
    # Start with ZIP magic bytes but corrupt the rest
    return b"PK\x03\x04" + b"\x00" * 100 + b"CORRUPT DATA"


def create_missing_manifest_zip() -> bytes:
    """Create missing_manifest.zip - ZIP without manifest.json.

    Tests: AC5 (Missing Manifest Handling)
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add some files but NO manifest.json
        zf.writestr("images/photo_001.jpg", create_dummy_jpeg())
        zf.writestr("metadata/photo_001.json", '{"id": "1"}')

    return buffer.getvalue()


def create_invalid_manifest_schema_zip() -> bytes:
    """Create invalid_manifest_schema.zip - ZIP with malformed manifest.

    Tests: AC6 (Invalid Manifest Schema)

    Manifest is valid JSON but doesn't match the ZipManifest Pydantic schema.
    """
    invalid_manifest = {
        # Missing required fields: manifest_version, source_id, linkage, documents
        "some_random_field": "value",
        "another_field": 123,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(invalid_manifest, indent=2))
        zf.writestr("images/photo.jpg", create_dummy_jpeg())

    return buffer.getvalue()


def create_path_traversal_attempt_zip() -> bytes:
    """Create path_traversal_attempt.zip - ZIP with path traversal attempt.

    Tests: AC7 (Path Traversal Security)

    Contains a file with '../' in the path attempting directory escape.
    """
    # Create a valid manifest but with a malicious file path
    malicious_manifest = {
        "manifest_version": "1.0",
        "source_id": "e2e-exception-images-zip",
        "created_at": "2025-01-01T00:00:00Z",
        "linkage": {
            "plantation_id": "PLT-E2E-001",
            "batch_id": "BATCH-MALICIOUS",
            "batch_result_ref": "QC-MALICIOUS",
        },
        "payload": {
            "exception_count": 1,
        },
        "documents": [
            {
                "document_id": "malicious_doc",
                "files": [
                    {
                        "path": "../etc/passwd",  # Path traversal attempt
                        "role": "image",
                        "mime_type": "text/plain",
                    },
                ],
                "attributes": {
                    "exception_type": "malicious",
                    "severity": "critical",
                },
            },
        ],
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(malicious_manifest, indent=2))
        # Add the malicious file reference (actual file doesn't need to exist for manifest validation test)
        # But we add it to the ZIP to make the test realistic
        zf.writestr("../etc/passwd", "root:x:0:0:root:/root:/bin/bash")

    return buffer.getvalue()


def main() -> None:
    """Generate all ZIP fixtures."""
    print("Generating ZIP fixtures for Story 0.4.9...")

    fixtures = [
        ("valid_exception_batch.zip", create_valid_exception_batch_zip()),
        ("corrupt_zip.zip", create_corrupt_zip()),
        ("missing_manifest.zip", create_missing_manifest_zip()),
        ("invalid_manifest_schema.zip", create_invalid_manifest_schema_zip()),
        ("path_traversal_attempt.zip", create_path_traversal_attempt_zip()),
    ]

    for filename, content in fixtures:
        filepath = FIXTURES_DIR / filename
        filepath.write_bytes(content)
        print(f"  ✓ Created {filename} ({len(content)} bytes)")

    print(f"\nAll fixtures written to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
