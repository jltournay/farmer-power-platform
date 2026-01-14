"""Unit tests for AiModelClient.

Story 0.75.23: RAG Query Service with BFF Integration

Tests query_knowledge method, DAPR service invocation, error handling, and retry logic.
"""

from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from bff.infrastructure.clients.ai_model_client import AiModelClient
from bff.infrastructure.clients.base import ServiceUnavailableError
from fp_common.models import (
    RetrievalResult,
)
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc


def create_query_knowledge_response(
    query: str = "What causes blister blight?",
    namespace: str = "knowledge-v1",
    total_matches: int = 10,
) -> ai_model_pb2.QueryKnowledgeResponse:
    """Create a QueryKnowledgeResponse proto for testing."""
    response = ai_model_pb2.QueryKnowledgeResponse(
        query=query,
        namespace=namespace,
        total_matches=total_matches,
    )
    response.matches.append(
        ai_model_pb2.RetrievalMatch(
            chunk_id="disease-guide-v1-chunk-0",
            content="Blister blight is a fungal disease caused by...",
            score=0.95,
            document_id="disease-guide",
            title="Blister Blight Treatment Guide",
            domain="plant_diseases",
            metadata_json='{"region": "Kenya", "tags": ["fungal"]}',
        )
    )
    response.matches.append(
        ai_model_pb2.RetrievalMatch(
            chunk_id="disease-guide-v1-chunk-1",
            content="Treatment options include fungicide application...",
            score=0.85,
            document_id="disease-guide",
            title="Blister Blight Treatment Guide",
            domain="plant_diseases",
            metadata_json='{"region": "Kenya"}',
        )
    )
    return response


class TestAiModelClientInit:
    """Tests for AiModelClient initialization."""

    def test_default_initialization(self):
        """Client initializes with default DAPR settings."""
        client = AiModelClient()

        assert client._target_app_id == "ai-model"
        assert client._dapr_grpc_port == 50001
        assert client._direct_host is None

    def test_direct_host_initialization(self):
        """Client can be initialized with direct host for testing."""
        client = AiModelClient(direct_host="localhost:50051")

        assert client._target_app_id == "ai-model"
        assert client._direct_host == "localhost:50051"


class TestQueryKnowledge:
    """Tests for query_knowledge method."""

    @pytest.fixture
    def mock_stub(self):
        """Create a mock gRPC stub."""
        stub = MagicMock(spec=ai_model_pb2_grpc.RAGDocumentServiceStub)
        stub.QueryKnowledge = AsyncMock(return_value=create_query_knowledge_response())
        return stub

    @pytest.fixture
    def client_with_mock_stub(self, mock_stub):
        """Create a client with a mocked stub."""
        channel = MagicMock(spec=grpc.aio.Channel)
        client = AiModelClient(channel=channel)
        client._stubs[ai_model_pb2_grpc.RAGDocumentServiceStub] = mock_stub
        return client

    @pytest.mark.asyncio
    async def test_returns_retrieval_result(self, client_with_mock_stub, mock_stub):
        """query_knowledge returns a RetrievalResult."""
        result = await client_with_mock_stub.query_knowledge(
            query="What causes blister blight?",
            domains=["plant_diseases"],
            top_k=5,
            confidence_threshold=0.7,
            namespace="knowledge-v1",
        )

        assert isinstance(result, RetrievalResult)
        assert result.query == "What causes blister blight?"
        assert result.namespace == "knowledge-v1"
        assert result.total_matches == 10
        assert len(result.matches) == 2
        assert result.matches[0].chunk_id == "disease-guide-v1-chunk-0"
        assert result.matches[0].domain == "plant_diseases"

    @pytest.mark.asyncio
    async def test_passes_correct_request(self, client_with_mock_stub, mock_stub):
        """query_knowledge builds correct proto request."""
        await client_with_mock_stub.query_knowledge(
            query="How to treat blister blight?",
            domains=["plant_diseases", "tea_cultivation"],
            top_k=10,
            confidence_threshold=0.8,
            namespace="test-namespace",
        )

        mock_stub.QueryKnowledge.assert_called_once()
        call_args = mock_stub.QueryKnowledge.call_args
        request = call_args[0][0]

        assert request.query == "How to treat blister blight?"
        assert list(request.domains) == ["plant_diseases", "tea_cultivation"]
        assert request.top_k == 10
        assert request.confidence_threshold == pytest.approx(0.8, rel=1e-5)
        assert request.namespace == "test-namespace"

    @pytest.mark.asyncio
    async def test_empty_query_raises_value_error(self, client_with_mock_stub):
        """Empty query raises ValueError."""
        with pytest.raises(ValueError, match="query is required"):
            await client_with_mock_stub.query_knowledge(query="")

    @pytest.mark.asyncio
    async def test_whitespace_query_raises_value_error(self, client_with_mock_stub):
        """Whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="query is required"):
            await client_with_mock_stub.query_knowledge(query="   ")

    @pytest.mark.asyncio
    async def test_default_parameters(self, client_with_mock_stub, mock_stub):
        """Default parameters are applied correctly."""
        await client_with_mock_stub.query_knowledge(query="Test query")

        call_args = mock_stub.QueryKnowledge.call_args
        request = call_args[0][0]

        assert request.top_k == 5
        assert request.confidence_threshold == 0.0
        assert request.namespace == ""
        assert len(request.domains) == 0


class TestQueryKnowledgeErrorHandling:
    """Tests for error handling in query_knowledge."""

    @pytest.fixture
    def mock_channel(self):
        """Create a mock channel."""
        return MagicMock(spec=grpc.aio.Channel)

    @pytest.fixture
    def client_with_failing_stub(self, mock_channel):
        """Create a client with a stub that raises errors."""
        client = AiModelClient(channel=mock_channel)
        return client

    @pytest.mark.asyncio
    async def test_unavailable_service_raises_error(self, client_with_failing_stub):
        """UNAVAILABLE status raises ServiceUnavailableError."""
        mock_stub = MagicMock(spec=ai_model_pb2_grpc.RAGDocumentServiceStub)
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=grpc.aio.Metadata(),
            trailing_metadata=grpc.aio.Metadata(),
            details="Service temporarily unavailable",
            debug_error_string="",
        )
        mock_stub.QueryKnowledge = AsyncMock(side_effect=error)
        client_with_failing_stub._stubs[ai_model_pb2_grpc.RAGDocumentServiceStub] = mock_stub

        with pytest.raises(ServiceUnavailableError):
            await client_with_failing_stub.query_knowledge(query="Test query")


class TestQueryKnowledgeFromQuery:
    """Tests for query_knowledge_from_query method."""

    @pytest.fixture
    def mock_stub(self):
        """Create a mock gRPC stub."""
        stub = MagicMock(spec=ai_model_pb2_grpc.RAGDocumentServiceStub)
        stub.QueryKnowledge = AsyncMock(return_value=create_query_knowledge_response())
        return stub

    @pytest.fixture
    def client_with_mock_stub(self, mock_stub):
        """Create a client with a mocked stub."""
        channel = MagicMock(spec=grpc.aio.Channel)
        client = AiModelClient(channel=channel)
        client._stubs[ai_model_pb2_grpc.RAGDocumentServiceStub] = mock_stub
        return client

    @pytest.mark.asyncio
    async def test_accepts_retrieval_query_object(self, client_with_mock_stub, mock_stub):
        """query_knowledge_from_query accepts RetrievalQuery object."""
        from fp_common.models import RetrievalQuery

        query = RetrievalQuery(
            query="What causes blister blight?",
            domains=["plant_diseases"],
            top_k=5,
            confidence_threshold=0.7,
            namespace="knowledge-v1",
        )

        result = await client_with_mock_stub.query_knowledge_from_query(query)

        assert isinstance(result, RetrievalResult)
        assert result.query == "What causes blister blight?"

        # Verify the query was forwarded with correct parameters
        call_args = mock_stub.QueryKnowledge.call_args
        request = call_args[0][0]
        assert request.query == "What causes blister blight?"
        assert list(request.domains) == ["plant_diseases"]
        assert request.top_k == 5
