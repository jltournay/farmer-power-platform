"""Test fixtures for fp-knowledge CLI tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_knowledge.client import KnowledgeClient
from fp_knowledge.models import (
    DocumentMetadata,
    DocumentStatus,
    ExtractionJobResult,
    JobStatus,
    KnowledgeDomain,
    RagDocument,
    RagDocumentInput,
)
from fp_knowledge.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        grpc_endpoint_dev="localhost:50001",
        grpc_endpoint_staging="localhost:50001",
        grpc_endpoint_prod="localhost:50001",
        dapr_app_id="ai-model",
        grpc_timeout=5.0,
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock KnowledgeClient."""
    client = MagicMock(spec=KnowledgeClient)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.create = AsyncMock()
    client.get_by_id = AsyncMock()
    client.get_by_version = AsyncMock()
    client.list_documents = AsyncMock()
    client.list_versions = AsyncMock()
    client.stage = AsyncMock()
    client.activate = AsyncMock()
    client.archive = AsyncMock()
    client.rollback = AsyncMock()
    client.extract = AsyncMock()
    client.get_job_status = AsyncMock()
    client.stream_progress = AsyncMock()
    client.chunk = AsyncMock()
    client.list_chunks = AsyncMock()
    client.get_chunk = AsyncMock()
    client.delete_chunks = AsyncMock()
    return client


@pytest.fixture
def sample_document_input() -> RagDocumentInput:
    """Create a sample document input for testing."""
    return RagDocumentInput(
        document_id="blister-blight-guide",
        title="Blister Blight Disease Guide",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="# Blister Blight\n\nBlister blight is caused by...",
        metadata=DocumentMetadata(
            author="dr-kimani",
            source="Tea Research Foundation",
            region="Kenya",
            tags=["disease", "blister-blight", "tea"],
        ),
    )


@pytest.fixture
def sample_document() -> RagDocument:
    """Create a sample document for testing."""
    return RagDocument(
        id="blister-blight-guide:v1",
        document_id="blister-blight-guide",
        version=1,
        title="Blister Blight Disease Guide",
        domain="plant_diseases",
        content="# Blister Blight\n\nBlister blight is caused by...",
        status=DocumentStatus.DRAFT,
        metadata=DocumentMetadata(
            author="dr-kimani",
            source="Tea Research Foundation",
            region="Kenya",
            tags=["disease", "blister-blight", "tea"],
        ),
    )


@pytest.fixture
def sample_active_document(sample_document: RagDocument) -> RagDocument:
    """Create a sample active document for testing."""
    return sample_document.model_copy(
        update={
            "status": DocumentStatus.ACTIVE,
            "version": 2,
            "id": "blister-blight-guide:v2",
        }
    )


@pytest.fixture
def sample_staged_document(sample_document: RagDocument) -> RagDocument:
    """Create a sample staged document for testing."""
    return sample_document.model_copy(
        update={
            "status": DocumentStatus.STAGED,
            "version": 3,
            "id": "blister-blight-guide:v3",
        }
    )


@pytest.fixture
def sample_extraction_job() -> ExtractionJobResult:
    """Create a sample extraction job result."""
    return ExtractionJobResult(
        job_id="job-123",
        document_id="blister-blight-guide",
        status=JobStatus.IN_PROGRESS,
        progress_percent=50,
        pages_processed=5,
        total_pages=10,
    )


@pytest.fixture
def sample_yaml_file(tmp_path: Path, sample_document_input: RagDocumentInput) -> Path:
    """Create a temporary YAML file for testing.

    Uses pytest's tmp_path fixture for automatic cleanup.
    """
    # Note: content uses folded style (>) to avoid multiline indentation issues
    yaml_content = f"""document_id: {sample_document_input.document_id}
title: {sample_document_input.title}
domain: {sample_document_input.domain.value}
content: >
  Blister blight is caused by fungi and affects tea plants.
  This is expert knowledge for RAG retrieval.
metadata:
  author: {sample_document_input.metadata.author}
  source: {sample_document_input.metadata.source}
  region: {sample_document_input.metadata.region}
  tags:
    - disease
    - blister-blight
    - tea
"""
    yaml_file = tmp_path / "sample_document.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def invalid_yaml_file(tmp_path: Path) -> Path:
    """Create an invalid YAML file for testing.

    Uses pytest's tmp_path fixture for automatic cleanup.
    """
    yaml_content = """document_id: test
# Missing required fields
"""
    yaml_file = tmp_path / "invalid_document.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def malformed_yaml_file(tmp_path: Path) -> Path:
    """Create a malformed YAML file for testing.

    Uses pytest's tmp_path fixture for automatic cleanup.
    """
    yaml_content = """invalid: yaml: structure:
  - [broken
"""
    yaml_file = tmp_path / "malformed_document.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file
