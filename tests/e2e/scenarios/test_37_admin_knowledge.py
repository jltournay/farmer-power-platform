"""E2E Tests: Platform Admin Knowledge Management API Flows.

Story 9.9a: Tests for knowledge management via BFF admin endpoints.
These tests verify the API operations that the platform-admin frontend relies on
for managing knowledge documents, lifecycle transitions, chunking, vectorization,
and knowledge base queries.

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

Test Flow:
    1. CRUD operations (create, list, get, update, delete)
    2. Lifecycle transitions (draft -> staged -> active -> archived, rollback)
    3. File upload with extraction job tracking
    4. Chunk listing after document processing
    5. Vectorization trigger and job status polling
    6. Knowledge base query (semantic search)
    7. Authorization enforcement (non-admin access denied)
    8. Input validation (invalid domains, empty titles, etc.)

Note:
    - Tests create their own documents via the BFF API (no seed data dependency)
    - Documents created in tests are isolated by unique IDs
    - Vectorization/Pinecone tests verify graceful handling when not configured
"""

import uuid
from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient

pytestmark = pytest.mark.e2e  # Mark all tests in this module for E2E CI


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

TEST_DOCUMENT_CONTENT = """# Blister Blight Disease Management

## Overview
Blister blight (Exobasidium vexans) is a major fungal disease affecting tea plants,
particularly in high-altitude tea-growing regions with cool, humid climates.

## Symptoms
- Young leaves show small, translucent spots
- Blisters are initially pale and water-soaked
- Severely affected leaves become distorted

## Management
1. Maintain proper shade management
2. Ensure adequate drainage
3. Apply copper-based fungicides
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _unique_id() -> str:
    """Generate unique test ID for document isolation."""
    return f"e2e-{uuid.uuid4().hex[:8]}"


async def _create_test_document(
    bff_api: BFFClient,
    title: str | None = None,
    domain: str = "plant_diseases",
    content: str = "",
    author: str = "E2E Test",
) -> dict[str, Any]:
    """Helper to create a document for testing."""
    data = {
        "title": title or f"E2E Test Doc {_unique_id()}",
        "domain": domain,
        "content": content or TEST_DOCUMENT_CONTENT,
        "author": author,
        "source": "E2E Test Suite",
        "region": "Kenya",
        "tags": ["e2e-test", "tea"],
    }
    return await bff_api.admin_create_knowledge_document(data)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestKnowledgeDocumentCRUD:
    """E2E tests for Knowledge Document CRUD operations (AC 9.9a.1)."""

    @pytest.mark.asyncio
    async def test_create_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test creating a new knowledge document via BFF."""
        doc = await _create_test_document(bff_api, title="E2E Create Test")

        # Verify response is DocumentDetail
        assert "document_id" in doc
        assert "version" in doc
        assert doc["version"] == 1
        assert doc["title"] == "E2E Create Test"
        assert doc["status"] == "draft"
        assert "created_at" in doc
        assert "updated_at" in doc

    @pytest.mark.asyncio
    async def test_create_document_with_metadata(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test creating a document with full metadata."""
        data = {
            "title": "E2E Metadata Test",
            "domain": "tea_cultivation",
            "content": "Tea cultivation best practices.",
            "author": "Dr. Tea Expert",
            "source": "Research Paper",
            "region": "Sri Lanka",
            "tags": ["cultivation", "best-practices"],
        }
        doc = await bff_api.admin_create_knowledge_document(data)

        assert doc["title"] == "E2E Metadata Test"
        assert "metadata" in doc
        assert doc["metadata"]["author"] == "Dr. Tea Expert"
        assert doc["metadata"]["region"] == "Sri Lanka"

    @pytest.mark.asyncio
    async def test_list_documents(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing knowledge documents returns expected structure."""
        # Create a document to ensure list is non-empty
        await _create_test_document(bff_api)

        result = await bff_api.admin_list_knowledge_documents()

        # Verify paginated response structure
        assert "data" in result
        assert "pagination" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) >= 1

        pagination = result["pagination"]
        assert "total_count" in pagination
        assert "page" in pagination
        assert "page_size" in pagination

    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing documents with pagination parameters."""
        result = await bff_api.admin_list_knowledge_documents(page=1, page_size=5)

        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 5

    @pytest.mark.asyncio
    async def test_list_documents_filter_by_domain(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering documents by domain (AC 9.9a.1)."""
        # Create documents in different domains
        await _create_test_document(bff_api, domain="plant_diseases")

        result = await bff_api.admin_list_knowledge_documents(domain="plant_diseases")

        # All returned documents should be in the filtered domain
        for doc in result["data"]:
            assert doc["domain"] == "plant_diseases"

    @pytest.mark.asyncio
    async def test_get_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test getting a specific document by ID.

        Note: version=0 in gRPC means "get active version". Since newly created
        documents are in draft status, we must request version=1 explicitly.
        """
        created = await _create_test_document(bff_api, title="E2E Get Test")
        document_id = created["document_id"]

        doc = await bff_api.admin_get_knowledge_document(document_id, version=1)

        assert doc["document_id"] == document_id
        assert doc["title"] == "E2E Get Test"
        assert doc["version"] == 1
        assert doc["status"] == "draft"
        assert "content" in doc

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test 404 response for non-existent document."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/knowledge/non-existent-doc-12345",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test updating a document creates new version."""
        created = await _create_test_document(bff_api, title="E2E Update Test")
        document_id = created["document_id"]

        updated = await bff_api.admin_update_knowledge_document(
            document_id,
            {
                "title": "E2E Updated Title",
                "content": "Updated content for testing.",
                "change_summary": "Updated title and content",
            },
        )

        assert updated["document_id"] == document_id
        assert updated["version"] == 2
        assert updated["title"] == "E2E Updated Title"

    @pytest.mark.asyncio
    async def test_delete_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test deleting (archiving) a document."""
        created = await _create_test_document(bff_api, title="E2E Delete Test")
        document_id = created["document_id"]

        result = await bff_api.admin_delete_knowledge_document(document_id)

        assert "versions_archived" in result
        assert result["versions_archived"] >= 1

    @pytest.mark.asyncio
    async def test_search_documents(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test searching documents by query text."""
        # Create a document with known content
        await _create_test_document(
            bff_api,
            title="Blister Blight E2E Search",
            content="Blister blight is caused by Exobasidium vexans fungus.",
        )

        results = await bff_api.admin_search_knowledge_documents(
            query="blister blight",
        )

        assert isinstance(results, list)
        # Should find at least the document we just created
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_documents_with_domain_filter(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test search with domain filter."""
        results = await bff_api.admin_search_knowledge_documents(
            query="tea",
            domain="plant_diseases",
        )

        assert isinstance(results, list)
        for doc in results:
            assert doc["domain"] == "plant_diseases"


@pytest.mark.e2e
class TestKnowledgeDocumentLifecycle:
    """E2E tests for document lifecycle transitions (AC 9.9a.2)."""

    @pytest.mark.asyncio
    async def test_stage_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test staging a draft document.

        Note: gRPC StageDocument requires version > 0 explicitly.
        """
        created = await _create_test_document(bff_api, title="E2E Stage Test")
        document_id = created["document_id"]
        assert created["status"] == "draft"

        staged = await bff_api.admin_stage_knowledge_document(document_id, version=1)

        assert staged["document_id"] == document_id
        assert staged["status"] == "staged"

    @pytest.mark.asyncio
    async def test_activate_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test activating a staged document."""
        created = await _create_test_document(bff_api, title="E2E Activate Test")
        document_id = created["document_id"]

        # Stage first (version=1 required by gRPC)
        await bff_api.admin_stage_knowledge_document(document_id, version=1)

        # Then activate (version=1)
        activated = await bff_api.admin_activate_knowledge_document(document_id, version=1)

        assert activated["document_id"] == document_id
        assert activated["status"] == "active"

    @pytest.mark.asyncio
    async def test_archive_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test archiving a document."""
        created = await _create_test_document(bff_api, title="E2E Archive Test")
        document_id = created["document_id"]

        archived = await bff_api.admin_archive_knowledge_document(document_id, version=1)

        assert archived["document_id"] == document_id
        assert archived["status"] == "archived"

    @pytest.mark.asyncio
    async def test_full_lifecycle_flow(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test complete lifecycle: draft -> staged -> active -> archived."""
        created = await _create_test_document(bff_api, title="E2E Lifecycle Test")
        document_id = created["document_id"]
        assert created["status"] == "draft"

        # draft -> staged (version=1 required by gRPC)
        staged = await bff_api.admin_stage_knowledge_document(document_id, version=1)
        assert staged["status"] == "staged"

        # staged -> active (version=1)
        activated = await bff_api.admin_activate_knowledge_document(document_id, version=1)
        assert activated["status"] == "active"

        # active -> archived (version=1)
        archived = await bff_api.admin_archive_knowledge_document(document_id, version=1)
        assert archived["status"] == "archived"

    @pytest.mark.asyncio
    async def test_rollback_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test rolling back to a previous version creates new draft."""
        # Create and update to get v2
        created = await _create_test_document(bff_api, title="E2E Rollback Test v1")
        document_id = created["document_id"]

        await bff_api.admin_update_knowledge_document(
            document_id,
            {"title": "E2E Rollback Test v2", "change_summary": "Version 2"},
        )

        # Rollback to v1 creates a new version
        rolled_back = await bff_api.admin_rollback_knowledge_document(
            document_id,
            target_version=1,
        )

        assert rolled_back["document_id"] == document_id
        assert rolled_back["status"] == "draft"
        # New version should be >= 3 (rollback creates new)
        assert rolled_back["version"] >= 3


@pytest.mark.e2e
class TestKnowledgeDocumentUpload:
    """E2E tests for file upload and extraction (AC 9.9a.3, 9.9a.4)."""

    @pytest.mark.asyncio
    async def test_upload_markdown_file(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test uploading a markdown file triggers extraction."""
        file_content = b"# E2E Upload Test\n\nThis is test content for upload.\n"

        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/upload",
            files={"file": ("e2e-test-upload.md", file_content, "application/octet-stream")},
            data={
                "title": "E2E Upload Test",
                "domain": "plant_diseases",
                "author": "E2E Test",
            },
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        result = response.json()
        assert "job_id" in result
        assert "document_id" in result

    @pytest.mark.asyncio
    async def test_upload_text_file(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test uploading a plain text file triggers extraction."""
        file_content = b"Plain text content for E2E testing.\nMultiple lines.\n"

        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/upload",
            files={"file": ("e2e-test.txt", file_content, "application/octet-stream")},
            data={"title": "E2E Text Upload", "domain": "tea_cultivation", "author": "E2E Test"},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that unsupported file types are rejected with 400."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/upload",
            files={"file": ("test.exe", b"binary content", "application/octet-stream")},
            data={"title": "Bad File", "domain": "plant_diseases"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Unsupported file type" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_extraction_job_status(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test polling extraction job status after upload."""
        file_content = b"# Extraction Status Test\n\nContent.\n"
        upload_response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/upload",
            files={"file": ("extraction-test.md", file_content, "application/octet-stream")},
            data={"title": "E2E Extraction Status", "domain": "plant_diseases", "author": "E2E Test"},
        )

        assert upload_response.status_code == 201, (
            f"Expected 201, got {upload_response.status_code}: {upload_response.text}"
        )

        upload_result = upload_response.json()
        job_id = upload_result["job_id"]
        document_id = upload_result["document_id"]

        # Poll extraction job status
        job_status = await bff_api.admin_get_extraction_job(document_id, job_id)

        assert job_status["job_id"] == job_id
        assert "status" in job_status
        assert "progress_percent" in job_status


@pytest.mark.e2e
class TestKnowledgeChunks:
    """E2E tests for document chunk operations (AC 9.9a.5)."""

    @pytest.mark.asyncio
    async def test_list_chunks_structure(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing chunks returns expected structure."""
        # Create and stage a document (version=1 required by gRPC)
        created = await _create_test_document(
            bff_api,
            title="E2E Chunk List Test",
            content=TEST_DOCUMENT_CONTENT,
        )
        document_id = created["document_id"]
        await bff_api.admin_stage_knowledge_document(document_id, version=1)

        result = await bff_api.admin_list_knowledge_chunks(document_id, version=1)

        # Verify paginated chunk response structure
        assert "data" in result
        assert "pagination" in result
        assert isinstance(result["data"], list)

        pagination = result["pagination"]
        assert "total_count" in pagination
        assert "page" in pagination
        assert "page_size" in pagination

    @pytest.mark.asyncio
    async def test_list_chunks_with_pagination(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing chunks with pagination parameters."""
        created = await _create_test_document(bff_api, title="E2E Chunk Pagination")
        document_id = created["document_id"]

        result = await bff_api.admin_list_knowledge_chunks(
            document_id,
            version=1,
            page=1,
            page_size=10,
        )

        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 10


@pytest.mark.e2e
class TestKnowledgeVectorization:
    """E2E tests for vectorization operations (AC 9.9a.5)."""

    @pytest.mark.asyncio
    async def test_vectorize_document_trigger(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test triggering vectorization returns job status."""
        # Create and stage a document (version=1 required by gRPC)
        created = await _create_test_document(
            bff_api,
            title="E2E Vectorize Test",
            content=TEST_DOCUMENT_CONTENT,
        )
        document_id = created["document_id"]
        await bff_api.admin_stage_knowledge_document(document_id, version=1)

        response = await bff_api.admin_request_raw(
            "POST",
            f"/api/admin/knowledge/{document_id}/vectorize",
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "job_id" in result
        assert "status" in result
        assert "namespace" in result

    @pytest.mark.asyncio
    async def test_get_vectorization_job_status(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test polling vectorization job status."""
        # Create and stage a document
        created = await _create_test_document(
            bff_api,
            title="E2E Vec Job Test",
            content=TEST_DOCUMENT_CONTENT,
        )
        document_id = created["document_id"]
        await bff_api.admin_stage_knowledge_document(document_id, version=1)

        # Trigger vectorization
        vec_response = await bff_api.admin_request_raw(
            "POST",
            f"/api/admin/knowledge/{document_id}/vectorize",
        )
        assert vec_response.status_code == 200, f"Expected 200, got {vec_response.status_code}: {vec_response.text}"

        vec_result = vec_response.json()
        job_id = vec_result["job_id"]

        # Poll job status
        job_status = await bff_api.admin_get_vectorization_job(document_id, job_id)

        assert job_status["job_id"] == job_id
        assert "status" in job_status
        assert "chunks_total" in job_status
        assert "chunks_embedded" in job_status
        assert "chunks_stored" in job_status


@pytest.mark.e2e
class TestKnowledgeQuery:
    """E2E tests for knowledge base query (AC 9.9a.6)."""

    @pytest.mark.asyncio
    async def test_query_knowledge_base(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test querying the knowledge base returns expected structure."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            json={"query": "How to treat blister blight in tea?"},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "matches" in result
        assert "query" in result
        assert "total_matches" in result
        assert isinstance(result["matches"], list)

    @pytest.mark.asyncio
    async def test_query_with_domain_filter(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test querying with domain filter."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            json={"query": "tea diseases", "domains": ["plant_diseases"]},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "matches" in result
        assert isinstance(result["matches"], list)

    @pytest.mark.asyncio
    async def test_query_with_top_k(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test query respects top_k parameter."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            json={"query": "tea cultivation best practices", "top_k": 3},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "matches" in result
        assert len(result["matches"]) <= 3

    @pytest.mark.asyncio
    async def test_query_result_item_structure(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test query result items have expected fields."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            json={"query": "blister blight treatment"},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        if result["matches"]:
            match = result["matches"][0]
            assert "chunk_id" in match
            assert "content" in match
            assert "score" in match
            assert "document_id" in match
            assert "title" in match
            assert "domain" in match


@pytest.mark.e2e
class TestKnowledgeAuthorization:
    """E2E tests for knowledge management authorization (AC 9.9a.1-6)."""

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_documents(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that non-admin roles get 403 on list documents."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/knowledge",
            role="factory_manager",
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_create_document(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that non-admin roles get 403 on create document."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge",
            role="factory_manager",
            json={
                "title": "Unauthorized Doc",
                "domain": "plant_diseases",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_query_knowledge(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that non-admin roles get 403 on knowledge query."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            role="factory_manager",
            json={"query": "test query"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that requests without auth token are rejected.

        Note: BFF auth middleware returns 403 (Forbidden) for missing tokens,
        not 401 (Unauthorized). This is the established BFF pattern.
        """
        response = await bff_api.client.get("/api/admin/knowledge")
        assert response.status_code == 403


@pytest.mark.e2e
class TestKnowledgeInputValidation:
    """E2E tests for input validation on knowledge endpoints."""

    @pytest.mark.asyncio
    async def test_create_document_empty_title_rejected(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that empty title is rejected with 422."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge",
            json={
                "title": "",
                "domain": "plant_diseases",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_document_invalid_domain_rejected(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that invalid domain is rejected with 422."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge",
            json={
                "title": "Valid Title",
                "domain": "invalid_domain_xyz",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_empty_query_rejected(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that empty query string is rejected with 422."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            json={"query": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_invalid_top_k_rejected(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that out-of-range top_k is rejected with 422."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/query",
            json={"query": "test", "top_k": 200},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rollback_invalid_version_rejected(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that rollback with version 0 is rejected with 422."""
        # Create a document first
        created = await _create_test_document(bff_api, title="E2E Rollback Validation")
        document_id = created["document_id"]

        response = await bff_api.admin_request_raw(
            "POST",
            f"/api/admin/knowledge/{document_id}/rollback",
            json={"target_version": 0},
        )
        assert response.status_code == 422


@pytest.mark.e2e
class TestKnowledgeIntegration:
    """E2E tests for BFF-to-backend integration flows."""

    @pytest.mark.asyncio
    async def test_create_then_get_consistency(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that created document can be immediately retrieved.

        Note: version=1 required since version=0 means "active version"
        and newly created docs are in draft status.
        """
        created = await _create_test_document(bff_api, title="E2E Consistency Test")
        document_id = created["document_id"]

        retrieved = await bff_api.admin_get_knowledge_document(document_id, version=1)

        assert retrieved["document_id"] == document_id
        assert retrieved["title"] == "E2E Consistency Test"
        assert retrieved["version"] == created["version"]

    @pytest.mark.asyncio
    async def test_update_then_get_shows_new_version(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that update creates new version visible in get."""
        created = await _create_test_document(bff_api, title="E2E Version Test v1")
        document_id = created["document_id"]

        await bff_api.admin_update_knowledge_document(
            document_id,
            {"title": "E2E Version Test v2", "change_summary": "Update for testing"},
        )

        # Get v2 explicitly
        v2 = await bff_api.admin_get_knowledge_document(document_id, version=2)
        assert v2["version"] == 2
        assert v2["title"] == "E2E Version Test v2"

        # Get specific version should show v1
        v1 = await bff_api.admin_get_knowledge_document(document_id, version=1)
        assert v1["version"] == 1
        assert v1["title"] == "E2E Version Test v1"

    @pytest.mark.asyncio
    async def test_lifecycle_then_list_filter(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that lifecycle transitions are reflected in list filter."""
        created = await _create_test_document(bff_api, title="E2E Filter Test")
        document_id = created["document_id"]

        # Stage the document (version=1 required by gRPC)
        await bff_api.admin_stage_knowledge_document(document_id, version=1)

        # List with status=staged should include our document
        result = await bff_api.admin_list_knowledge_documents(status="staged")

        staged_ids = [d["document_id"] for d in result["data"]]
        assert document_id in staged_ids

    @pytest.mark.asyncio
    async def test_create_upload_extraction_flow(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test the complete upload -> extraction flow via BFF."""
        file_content = b"# Integration Test\n\nFull flow content.\n"

        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/knowledge/upload",
            files={"file": ("integration-test.md", file_content, "application/octet-stream")},
            data={
                "title": "E2E Integration Upload",
                "domain": "plant_diseases",
                "author": "E2E Tester",
            },
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        upload_result = response.json()
        assert "job_id" in upload_result
        assert "document_id" in upload_result

        # Can poll extraction status
        job_status = await bff_api.admin_get_extraction_job(
            upload_result["document_id"],
            upload_result["job_id"],
        )
        assert job_status["job_id"] == upload_result["job_id"]
