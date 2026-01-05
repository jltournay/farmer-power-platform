"""Unit tests for RagDocumentRepository.

Tests cover:
- create() - creates new RAG document
- get_by_id() - retrieves document by ID
- get_active() - gets active document for document_id
- get_by_version() - gets specific version
- list_versions() - lists all versions of a document
- list_by_domain() - lists documents by knowledge domain
- list_by_status() - lists documents by lifecycle status
- ensure_indexes() - creates proper indexes
"""

from typing import Any

import pytest
from ai_model.domain.rag_document import (
    KnowledgeDomain,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
)
from ai_model.infrastructure.repositories.rag_document_repository import (
    RagDocumentRepository,
)


class TestRagDocumentRepository:
    """Tests for RagDocumentRepository."""

    @pytest.fixture
    def mock_db(self, mock_mongodb_client: Any) -> Any:
        """Get mock database from mock client."""
        return mock_mongodb_client["ai_model"]

    @pytest.fixture
    def repository(self, mock_db: Any) -> RagDocumentRepository:
        """Create repository with mock database."""
        return RagDocumentRepository(mock_db)

    @pytest.fixture
    def sample_document(self) -> RagDocument:
        """Create a sample RAG document for testing."""
        return RagDocument(
            id="disease-guide:v1",
            document_id="disease-guide",
            version=1,
            title="Blister Blight Treatment Guide",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="# Blister Blight\n\nBlister blight is caused by...",
            status=RagDocumentStatus.ACTIVE,
            metadata=RAGDocumentMetadata(
                author="Dr. Wanjiku",
                region="Kenya",
                tags=["blister-blight", "fungal"],
            ),
        )

    @pytest.fixture
    def sample_document_v2(self) -> RagDocument:
        """Create a second version of the sample document."""
        return RagDocument(
            id="disease-guide:v2",
            document_id="disease-guide",
            version=2,
            title="Blister Blight Treatment Guide v2",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="# Blister Blight v2\n\nUpdated content...",
            status=RagDocumentStatus.STAGED,
            metadata=RAGDocumentMetadata(
                author="Dr. Wanjiku",
                region="Kenya",
                tags=["blister-blight", "fungal", "updated"],
            ),
            change_summary="Added new treatment protocol",
        )

    @pytest.fixture
    def weather_document(self) -> RagDocument:
        """Create a weather domain document."""
        return RagDocument(
            id="weather-guide:v1",
            document_id="weather-guide",
            version=1,
            title="Weather Patterns Guide",
            domain=KnowledgeDomain.WEATHER_PATTERNS,
            content="Weather content...",
            status=RagDocumentStatus.ACTIVE,
            metadata=RAGDocumentMetadata(
                author="Operations",
                region="East Africa",
            ),
        )

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_document(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
    ) -> None:
        """Create stores document and returns it."""
        result = await repository.create(sample_document)

        assert result.id == sample_document.id
        assert result.document_id == sample_document.document_id
        assert result.version == sample_document.version

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
    ) -> None:
        """Get by ID returns document when it exists."""
        await repository.create(sample_document)

        result = await repository.get_by_id(sample_document.id)

        assert result is not None
        assert result.id == sample_document.id
        assert result.document_id == sample_document.document_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: RagDocumentRepository,
    ) -> None:
        """Get by ID returns None when document doesn't exist."""
        result = await repository.get_by_id("nonexistent:v1")

        assert result is None

    # =========================================================================
    # get_active() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_active_returns_active_document(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
        sample_document_v2: RagDocument,
    ) -> None:
        """Get active returns the active document for a document_id."""
        await repository.create(sample_document)  # ACTIVE
        await repository.create(sample_document_v2)  # STAGED

        result = await repository.get_active("disease-guide")

        assert result is not None
        assert result.status == RagDocumentStatus.ACTIVE
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_get_active_returns_none_when_no_active(
        self,
        repository: RagDocumentRepository,
        sample_document_v2: RagDocument,
    ) -> None:
        """Get active returns None when no active document exists."""
        # Only staged version exists
        await repository.create(sample_document_v2)

        result = await repository.get_active("disease-guide")

        assert result is None

    # =========================================================================
    # get_by_version() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_by_version_returns_specific_version(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
        sample_document_v2: RagDocument,
    ) -> None:
        """Get by version returns specific version."""
        await repository.create(sample_document)
        await repository.create(sample_document_v2)

        result = await repository.get_by_version("disease-guide", 2)

        assert result is not None
        assert result.version == 2
        assert result.status == RagDocumentStatus.STAGED

    @pytest.mark.asyncio
    async def test_get_by_version_not_found(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
    ) -> None:
        """Get by version returns None for nonexistent version."""
        await repository.create(sample_document)

        result = await repository.get_by_version("disease-guide", 99)

        assert result is None

    # =========================================================================
    # list_versions() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_versions_returns_all_versions(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
        sample_document_v2: RagDocument,
        weather_document: RagDocument,
    ) -> None:
        """List versions returns all versions of a document."""
        await repository.create(sample_document)
        await repository.create(sample_document_v2)
        await repository.create(weather_document)  # Different document_id

        result = await repository.list_versions("disease-guide")

        assert len(result) == 2
        # All should be for disease-guide
        assert all(doc.document_id == "disease-guide" for doc in result)

    @pytest.mark.asyncio
    async def test_list_versions_excludes_archived(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
    ) -> None:
        """List versions can exclude archived documents."""
        await repository.create(sample_document)

        # Create an archived version
        archived_doc = RagDocument(
            id="disease-guide:v3",
            document_id="disease-guide",
            version=3,
            title="Archived Guide",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="Archived content...",
            status=RagDocumentStatus.ARCHIVED,
            metadata=RAGDocumentMetadata(author="admin"),
        )
        await repository.create(archived_doc)

        result = await repository.list_versions(
            "disease-guide",
            include_archived=False,
        )

        assert len(result) == 1
        assert result[0].status != RagDocumentStatus.ARCHIVED

    # =========================================================================
    # list_by_domain() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_by_domain_returns_matching_documents(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
        sample_document_v2: RagDocument,
        weather_document: RagDocument,
    ) -> None:
        """List by domain returns documents in specified domain."""
        await repository.create(sample_document)
        await repository.create(sample_document_v2)
        await repository.create(weather_document)

        result = await repository.list_by_domain(KnowledgeDomain.PLANT_DISEASES)

        assert len(result) == 2
        assert all(doc.domain == KnowledgeDomain.PLANT_DISEASES for doc in result)

    @pytest.mark.asyncio
    async def test_list_by_domain_with_status_filter(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
        sample_document_v2: RagDocument,
    ) -> None:
        """List by domain respects status filter."""
        await repository.create(sample_document)  # ACTIVE
        await repository.create(sample_document_v2)  # STAGED

        result = await repository.list_by_domain(
            KnowledgeDomain.PLANT_DISEASES,
            status=RagDocumentStatus.ACTIVE,
        )

        assert len(result) == 1
        assert result[0].status == RagDocumentStatus.ACTIVE

    # =========================================================================
    # list_by_status() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_by_status_returns_matching_documents(
        self,
        repository: RagDocumentRepository,
        sample_document: RagDocument,
        sample_document_v2: RagDocument,
        weather_document: RagDocument,
    ) -> None:
        """List by status returns documents with specified status."""
        await repository.create(sample_document)  # ACTIVE
        await repository.create(sample_document_v2)  # STAGED
        await repository.create(weather_document)  # ACTIVE

        result = await repository.list_by_status(RagDocumentStatus.ACTIVE)

        assert len(result) == 2
        assert all(doc.status == RagDocumentStatus.ACTIVE for doc in result)

    # =========================================================================
    # Index Creation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self,
        repository: RagDocumentRepository,
    ) -> None:
        """Ensure indexes creates required indexes without error."""
        # This should not raise any exceptions
        await repository.ensure_indexes()
        # Note: MockMongoCollection implements create_index returning a mock name
