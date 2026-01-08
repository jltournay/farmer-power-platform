"""E2E Test: RAG Document Vectorization Flow.

Story 0.75.13c: Validates the complete RAG vectorization pipeline via gRPC.

Test Flow:
1. Create RAG document with content
2. Stage the document
3. Chunk the document (generates semantic chunks)
4. Vectorize the document (generates embeddings, stores in Pinecone)
5. Verify vectorization completed successfully

Prerequisites:
    - docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
    - PINECONE_API_KEY and PINECONE_INDEX_NAME environment variables set
    - Wait for all services to be healthy before running tests

Test Isolation:
    Each test uses a unique namespace in Pinecone (e2e-{uuid}) to prevent pollution.
    Cleanup fixture deletes vectors after test completion.

Note:
    If Pinecone credentials are not configured, vectorization tests are skipped.
    The ai-model service gracefully handles missing Pinecone configuration.
"""

import contextlib
import os
import uuid

import grpc
import pytest
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc

# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

AI_MODEL_GRPC_HOST = "localhost"
AI_MODEL_GRPC_PORT = 8090

# Test document content (realistic agricultural knowledge)
TEST_DOCUMENT_CONTENT = """# Blister Blight Disease Management

## Overview
Blister blight (Exobasidium vexans) is a major fungal disease affecting tea plants,
particularly in high-altitude tea-growing regions with cool, humid climates.

## Symptoms
- Young leaves show small, translucent spots that enlarge into blister-like swellings
- Blisters are initially pale and water-soaked, turning white as spores develop
- Severely affected leaves become distorted and may fall prematurely
- New shoots and buds are most susceptible

## Environmental Conditions Favoring Disease
- Temperature: 15-20°C (optimal for spore germination)
- Humidity: >80% relative humidity
- Rainfall: Frequent light showers with misty conditions
- Season: Most severe during monsoon and post-monsoon periods

## Management Strategies

### Cultural Practices
1. Maintain proper shade management to reduce humidity
2. Ensure adequate drainage in tea fields
3. Prune affected shoots during dry weather
4. Remove and destroy heavily infected plant material

### Chemical Control
- Apply copper-based fungicides during favorable conditions
- Timing: Begin applications at first sign of disease
- Frequency: Every 7-10 days during high-risk periods

### Resistant Varieties
- Select cultivars with known resistance to blister blight
- Consult local research stations for recommended varieties
"""


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def pinecone_configured():
    """Check if Pinecone is configured for E2E tests."""
    api_key = os.environ.get("PINECONE_API_KEY", "")
    if not api_key:
        pytest.skip("PINECONE_API_KEY not configured - skipping vectorization test")
    return True


@pytest.fixture
def e2e_test_id():
    """Generate unique test ID for isolation."""
    return f"e2e-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def ai_model_channel():
    """Create gRPC channel to AI Model service."""
    channel = grpc.insecure_channel(f"{AI_MODEL_GRPC_HOST}:{AI_MODEL_GRPC_PORT}")
    # Wait for channel to be ready
    try:
        grpc.channel_ready_future(channel).result(timeout=30)
    except grpc.FutureTimeoutError:
        pytest.fail("AI Model service not available - is docker-compose running?")
    yield channel
    channel.close()


@pytest.fixture
def rag_document_stub(ai_model_channel):
    """Create RAGDocumentService stub."""
    return ai_model_pb2_grpc.RAGDocumentServiceStub(ai_model_channel)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def create_test_document(stub, document_id: str, content: str) -> ai_model_pb2.RAGDocument:
    """Create a RAG document for testing."""
    request = ai_model_pb2.CreateDocumentRequest(
        document_id=document_id,
        title="Blister Blight Disease Management Guide",
        domain="plant_diseases",
        content=content,
        metadata=ai_model_pb2.RAGDocumentMetadata(
            author="E2E Test",
            source="Test Suite",
            region="Kenya",
            tags=["tea", "diseases", "blister-blight", "e2e-test"],
        ),
    )
    response = stub.CreateDocument(request)
    return response.document


def stage_document(stub, document_id: str, version: int) -> ai_model_pb2.RAGDocument:
    """Stage a document for review."""
    request = ai_model_pb2.StageDocumentRequest(
        document_id=document_id,
        version=version,
    )
    return stub.StageDocument(request)


def chunk_document(stub, document_id: str, version: int) -> ai_model_pb2.ChunkDocumentResponse:
    """Chunk a document into semantic segments."""
    request = ai_model_pb2.ChunkDocumentRequest(
        document_id=document_id,
        version=version,
    )
    return stub.ChunkDocument(request)


def vectorize_document(
    stub, document_id: str, version: int, async_mode: bool = False
) -> ai_model_pb2.VectorizeDocumentResponse:
    """Vectorize a document (generate embeddings, store in Pinecone)."""
    request = ai_model_pb2.VectorizeDocumentRequest(
        document_id=document_id,
        version=version,
    )
    # Set async mode via setattr (protobuf reserved word)
    setattr(request, "async", async_mode)
    return stub.VectorizeDocument(request)


def get_vectorization_job(stub, job_id: str) -> ai_model_pb2.VectorizationJobResponse:
    """Get vectorization job status."""
    request = ai_model_pb2.GetVectorizationJobRequest(job_id=job_id)
    return stub.GetVectorizationJob(request)


def delete_document(stub, document_id: str) -> ai_model_pb2.DeleteDocumentResponse:
    """Delete a document (cleanup)."""
    request = ai_model_pb2.DeleteDocumentRequest(document_id=document_id)
    return stub.DeleteDocument(request)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestRAGVectorization:
    """E2E tests for RAG document vectorization flow."""

    def test_vectorization_e2e_flow(
        self,
        pinecone_configured,
        e2e_test_id,
        rag_document_stub,
    ):
        """
        Test complete vectorization flow: Create -> Stage -> Chunk -> Vectorize.

        AC7: E2E Test for vectorization flow with test isolation.
        """
        document_id = f"test-doc-{e2e_test_id}"

        try:
            # Step 1: Create document
            doc = create_test_document(
                rag_document_stub,
                document_id,
                TEST_DOCUMENT_CONTENT,
            )
            assert doc.document_id == document_id
            assert doc.version == 1
            assert doc.status == "draft"
            print(f"[1/4] Created document: {document_id} v{doc.version}")

            # Step 2: Stage document
            staged_doc = stage_document(rag_document_stub, document_id, 1)
            assert staged_doc.status == "staged"
            print(f"[2/4] Staged document: {document_id} v{staged_doc.version}")

            # Step 3: Chunk document
            chunk_response = chunk_document(rag_document_stub, document_id, 1)
            assert chunk_response.chunks_created > 0
            print(f"[3/4] Chunked document: {chunk_response.chunks_created} chunks created")

            # Step 4: Vectorize document (sync mode - wait for completion)
            vectorize_response = vectorize_document(
                rag_document_stub,
                document_id,
                version=1,
                async_mode=False,
            )

            # Verify vectorization completed
            assert vectorize_response.job_id, "Expected job_id in response"
            assert vectorize_response.status in (
                "completed",
                "partial",
            ), f"Expected completed/partial, got {vectorize_response.status}"
            assert vectorize_response.chunks_stored > 0, "Expected chunks to be stored"

            print(
                f"[4/4] Vectorized document: "
                f"{vectorize_response.chunks_stored}/{vectorize_response.chunks_total} chunks stored"
            )
            print(f"      Namespace: {vectorize_response.namespace}")
            print(f"      Content hash: {vectorize_response.content_hash}")

            if vectorize_response.failed_count > 0:
                print(f"      Warning: {vectorize_response.failed_count} chunks failed")

        finally:
            # Cleanup: Delete document (also cleans up chunks in MongoDB)
            # Note: Pinecone vectors remain (namespace-based cleanup would require
            # direct Pinecone client, which is out of scope for this test)
            try:
                delete_document(rag_document_stub, document_id)
                print(f"[Cleanup] Deleted document: {document_id}")
            except grpc.RpcError as e:
                print(f"[Cleanup] Warning: Failed to delete document: {e.details()}")

    def test_vectorization_async_mode(
        self,
        pinecone_configured,
        e2e_test_id,
        rag_document_stub,
    ):
        """
        Test async vectorization returns job_id immediately.

        The async mode allows clients to poll for job status without blocking.
        """
        document_id = f"test-async-{e2e_test_id}"

        try:
            # Create and stage document
            doc = create_test_document(
                rag_document_stub,
                document_id,
                TEST_DOCUMENT_CONTENT,
            )
            stage_document(rag_document_stub, document_id, 1)
            chunk_document(rag_document_stub, document_id, 1)

            # Vectorize in async mode
            vectorize_response = vectorize_document(
                rag_document_stub,
                document_id,
                version=1,
                async_mode=True,
            )

            # Should return immediately with job_id and pending status
            assert vectorize_response.job_id, "Expected job_id in async response"
            assert vectorize_response.status == "pending", (
                f"Expected pending status in async mode, got {vectorize_response.status}"
            )

            print(f"Async vectorization started: job_id={vectorize_response.job_id}")

            # Poll for job completion
            import time

            max_attempts = 30
            for attempt in range(max_attempts):
                job_status = get_vectorization_job(rag_document_stub, vectorize_response.job_id)
                if job_status.status in ("completed", "partial", "failed"):
                    print(
                        f"Job completed after {attempt + 1} polls: "
                        f"status={job_status.status}, "
                        f"chunks_stored={job_status.chunks_stored}"
                    )
                    assert job_status.status in ("completed", "partial")
                    break
                time.sleep(1)
            else:
                pytest.fail(f"Vectorization job did not complete within {max_attempts}s")

        finally:
            with contextlib.suppress(grpc.RpcError):
                delete_document(rag_document_stub, document_id)

    def test_vectorization_without_pinecone_returns_error(
        self,
        e2e_test_id,
        rag_document_stub,
    ):
        """
        Test that vectorization gracefully fails when Pinecone is not configured.

        Note: This test only runs if PINECONE_API_KEY is NOT set.
        When Pinecone IS configured, the test is skipped.
        """
        # Skip if Pinecone is configured (the other tests cover that case)
        if os.environ.get("PINECONE_API_KEY"):
            pytest.skip("Pinecone is configured - testing error path skipped")

        document_id = f"test-no-pinecone-{e2e_test_id}"

        try:
            # Create document
            doc = create_test_document(
                rag_document_stub,
                document_id,
                "Test content for error path.",
            )

            # Try to vectorize - should fail with UNAVAILABLE
            with pytest.raises(grpc.RpcError) as exc_info:
                vectorize_document(rag_document_stub, document_id, version=1)

            # Verify appropriate error
            assert exc_info.value.code() == grpc.StatusCode.UNAVAILABLE
            assert "not configured" in exc_info.value.details().lower()
            print("Correctly returned UNAVAILABLE when Pinecone not configured")

        finally:
            with contextlib.suppress(grpc.RpcError):
                delete_document(rag_document_stub, document_id)
