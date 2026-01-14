"""Unit tests for rag_converters module.

Story 0.75.23: RAG Query Service with BFF Integration

Tests verify Proto-to-Pydantic and Pydantic-to-Proto conversion correctness including:
- Basic field mapping
- JSON metadata serialization/deserialization
- List handling
- Round-trip validation (proto -> pydantic -> proto)
"""

import json

import pytest
from fp_common.converters import (
    retrieval_match_from_proto,
    retrieval_match_to_proto,
    retrieval_query_from_proto,
    retrieval_query_to_proto,
    retrieval_result_from_proto,
    retrieval_result_to_proto,
)
from fp_common.models import (
    RetrievalMatch,
    RetrievalQuery,
    RetrievalResult,
)
from fp_proto.ai_model.v1 import ai_model_pb2


class TestRetrievalMatchFromProto:
    """Tests for retrieval_match_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = ai_model_pb2.RetrievalMatch(
            chunk_id="disease-guide-v1-chunk-0",
            content="Blister blight is a fungal disease...",
            score=0.92,
            document_id="disease-guide",
            title="Blister Blight Treatment Guide",
            domain="plant_diseases",
            metadata_json='{"region": "Kenya", "tags": ["fungal", "treatment"]}',
        )

        result = retrieval_match_from_proto(proto)

        assert isinstance(result, RetrievalMatch)
        assert result.chunk_id == "disease-guide-v1-chunk-0"
        assert result.content == "Blister blight is a fungal disease..."
        assert result.score == pytest.approx(0.92, rel=1e-5)
        assert result.document_id == "disease-guide"
        assert result.title == "Blister Blight Treatment Guide"
        assert result.domain == "plant_diseases"
        assert result.metadata["region"] == "Kenya"
        assert result.metadata["tags"] == ["fungal", "treatment"]

    def test_empty_metadata_json(self):
        """Empty metadata_json returns empty dict."""
        proto = ai_model_pb2.RetrievalMatch(
            chunk_id="chunk-1",
            content="Some content",
            score=0.5,
            document_id="doc-1",
            title="Test Doc",
            domain="tea_cultivation",
            metadata_json="",
        )

        result = retrieval_match_from_proto(proto)

        assert result.metadata == {}

    def test_invalid_metadata_json_returns_empty_dict(self):
        """Invalid JSON in metadata_json returns empty dict."""
        proto = ai_model_pb2.RetrievalMatch(
            chunk_id="chunk-1",
            content="Some content",
            score=0.5,
            document_id="doc-1",
            title="Test Doc",
            domain="tea_cultivation",
            metadata_json="not valid json",
        )

        result = retrieval_match_from_proto(proto)

        assert result.metadata == {}


class TestRetrievalMatchToProto:
    """Tests for retrieval_match_to_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        match = RetrievalMatch(
            chunk_id="disease-guide-v1-chunk-0",
            content="Blister blight is a fungal disease...",
            score=0.92,
            document_id="disease-guide",
            title="Blister Blight Treatment Guide",
            domain="plant_diseases",
            metadata={"region": "Kenya", "tags": ["fungal", "treatment"]},
        )

        result = retrieval_match_to_proto(match)

        assert isinstance(result, ai_model_pb2.RetrievalMatch)
        assert result.chunk_id == "disease-guide-v1-chunk-0"
        assert result.content == "Blister blight is a fungal disease..."
        assert result.score == pytest.approx(0.92, rel=1e-5)
        assert result.document_id == "disease-guide"
        assert result.title == "Blister Blight Treatment Guide"
        assert result.domain == "plant_diseases"

        metadata = json.loads(result.metadata_json)
        assert metadata["region"] == "Kenya"
        assert metadata["tags"] == ["fungal", "treatment"]

    def test_empty_metadata(self):
        """Empty metadata produces empty JSON string."""
        match = RetrievalMatch(
            chunk_id="chunk-1",
            content="Some content",
            score=0.5,
            document_id="doc-1",
            title="Test Doc",
            domain="tea_cultivation",
            metadata={},
        )

        result = retrieval_match_to_proto(match)

        assert result.metadata_json == ""


class TestRetrievalResultFromProto:
    """Tests for retrieval_result_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = ai_model_pb2.QueryKnowledgeResponse(
            query="What causes blister blight?",
            namespace="knowledge-v1",
            total_matches=10,
        )
        proto.matches.append(
            ai_model_pb2.RetrievalMatch(
                chunk_id="chunk-1",
                content="Blister blight is caused by...",
                score=0.95,
                document_id="disease-guide",
                title="Disease Guide",
                domain="plant_diseases",
                metadata_json="{}",
            )
        )
        proto.matches.append(
            ai_model_pb2.RetrievalMatch(
                chunk_id="chunk-2",
                content="Treatment options include...",
                score=0.85,
                document_id="disease-guide",
                title="Disease Guide",
                domain="plant_diseases",
                metadata_json="{}",
            )
        )

        result = retrieval_result_from_proto(proto)

        assert isinstance(result, RetrievalResult)
        assert result.query == "What causes blister blight?"
        assert result.namespace == "knowledge-v1"
        assert result.total_matches == 10
        assert len(result.matches) == 2
        assert result.matches[0].chunk_id == "chunk-1"
        assert result.matches[0].score == pytest.approx(0.95, rel=1e-5)
        assert result.matches[1].chunk_id == "chunk-2"
        assert result.matches[1].score == pytest.approx(0.85, rel=1e-5)

    def test_empty_matches(self):
        """Empty matches list is handled."""
        proto = ai_model_pb2.QueryKnowledgeResponse(
            query="Unknown topic",
            namespace="knowledge-v1",
            total_matches=0,
        )

        result = retrieval_result_from_proto(proto)

        assert result.matches == []
        assert result.total_matches == 0
        assert result.count == 0

    def test_empty_namespace(self):
        """Empty namespace is converted to None."""
        proto = ai_model_pb2.QueryKnowledgeResponse(
            query="Test query",
            namespace="",
            total_matches=0,
        )

        result = retrieval_result_from_proto(proto)

        assert result.namespace is None


class TestRetrievalResultToProto:
    """Tests for retrieval_result_to_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        result = RetrievalResult(
            query="What causes blister blight?",
            namespace="knowledge-v1",
            total_matches=10,
            matches=[
                RetrievalMatch(
                    chunk_id="chunk-1",
                    content="Blister blight is caused by...",
                    score=0.95,
                    document_id="disease-guide",
                    title="Disease Guide",
                    domain="plant_diseases",
                    metadata={},
                ),
                RetrievalMatch(
                    chunk_id="chunk-2",
                    content="Treatment options include...",
                    score=0.85,
                    document_id="disease-guide",
                    title="Disease Guide",
                    domain="plant_diseases",
                    metadata={},
                ),
            ],
        )

        proto = retrieval_result_to_proto(result)

        assert isinstance(proto, ai_model_pb2.QueryKnowledgeResponse)
        assert proto.query == "What causes blister blight?"
        assert proto.namespace == "knowledge-v1"
        assert proto.total_matches == 10
        assert len(proto.matches) == 2
        assert proto.matches[0].chunk_id == "chunk-1"
        assert proto.matches[0].score == pytest.approx(0.95, rel=1e-5)

    def test_none_namespace(self):
        """None namespace is converted to empty string."""
        result = RetrievalResult(
            query="Test query",
            namespace=None,
            total_matches=0,
            matches=[],
        )

        proto = retrieval_result_to_proto(result)

        assert proto.namespace == ""


class TestRetrievalQueryFromProto:
    """Tests for retrieval_query_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = ai_model_pb2.QueryKnowledgeRequest(
            query="How to treat blister blight?",
            top_k=10,
            confidence_threshold=0.7,
            namespace="knowledge-v1",
        )
        proto.domains.append("plant_diseases")
        proto.domains.append("tea_cultivation")

        result = retrieval_query_from_proto(proto)

        assert isinstance(result, RetrievalQuery)
        assert result.query == "How to treat blister blight?"
        assert result.domains == ["plant_diseases", "tea_cultivation"]
        assert result.top_k == 10
        assert result.confidence_threshold == pytest.approx(0.7, rel=1e-5)
        assert result.namespace == "knowledge-v1"

    def test_default_top_k(self):
        """Zero top_k defaults to 5."""
        proto = ai_model_pb2.QueryKnowledgeRequest(
            query="Test query",
            top_k=0,
            confidence_threshold=0.0,
            namespace="",
        )

        result = retrieval_query_from_proto(proto)

        assert result.top_k == 5

    def test_empty_namespace(self):
        """Empty namespace is converted to None."""
        proto = ai_model_pb2.QueryKnowledgeRequest(
            query="Test query",
            top_k=5,
            confidence_threshold=0.0,
            namespace="",
        )

        result = retrieval_query_from_proto(proto)

        assert result.namespace is None

    def test_empty_domains(self):
        """Empty domains list is handled."""
        proto = ai_model_pb2.QueryKnowledgeRequest(
            query="Test query",
            top_k=5,
            confidence_threshold=0.0,
            namespace="",
        )

        result = retrieval_query_from_proto(proto)

        assert result.domains == []


class TestRetrievalQueryToProto:
    """Tests for retrieval_query_to_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        query = RetrievalQuery(
            query="How to treat blister blight?",
            domains=["plant_diseases", "tea_cultivation"],
            top_k=10,
            confidence_threshold=0.7,
            namespace="knowledge-v1",
        )

        proto = retrieval_query_to_proto(query)

        assert isinstance(proto, ai_model_pb2.QueryKnowledgeRequest)
        assert proto.query == "How to treat blister blight?"
        assert list(proto.domains) == ["plant_diseases", "tea_cultivation"]
        assert proto.top_k == 10
        assert proto.confidence_threshold == pytest.approx(0.7, rel=1e-5)
        assert proto.namespace == "knowledge-v1"

    def test_none_namespace(self):
        """None namespace is converted to empty string."""
        query = RetrievalQuery(
            query="Test query",
            domains=[],
            top_k=5,
            confidence_threshold=0.0,
            namespace=None,
        )

        proto = retrieval_query_to_proto(query)

        assert proto.namespace == ""


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_retrieval_match_round_trip(self):
        """Pydantic -> Proto -> Pydantic produces equivalent object."""
        original = RetrievalMatch(
            chunk_id="disease-guide-v1-chunk-0",
            content="Blister blight is a fungal disease...",
            score=0.92,
            document_id="disease-guide",
            title="Blister Blight Treatment Guide",
            domain="plant_diseases",
            metadata={"region": "Kenya", "tags": ["fungal", "treatment"]},
        )

        proto = retrieval_match_to_proto(original)
        result = retrieval_match_from_proto(proto)

        assert result.chunk_id == original.chunk_id
        assert result.content == original.content
        assert result.score == pytest.approx(original.score, rel=1e-5)
        assert result.document_id == original.document_id
        assert result.title == original.title
        assert result.domain == original.domain
        assert result.metadata == original.metadata

    def test_retrieval_query_round_trip(self):
        """Pydantic -> Proto -> Pydantic produces equivalent object."""
        original = RetrievalQuery(
            query="How to treat blister blight?",
            domains=["plant_diseases", "tea_cultivation"],
            top_k=10,
            confidence_threshold=0.7,
            namespace="knowledge-v1",
        )

        proto = retrieval_query_to_proto(original)
        result = retrieval_query_from_proto(proto)

        assert result.query == original.query
        assert result.domains == original.domains
        assert result.top_k == original.top_k
        assert result.confidence_threshold == pytest.approx(original.confidence_threshold, rel=1e-5)
        assert result.namespace == original.namespace

    def test_retrieval_result_round_trip(self):
        """Pydantic -> Proto -> Pydantic produces equivalent object."""
        original = RetrievalResult(
            query="What causes blister blight?",
            namespace="knowledge-v1",
            total_matches=10,
            matches=[
                RetrievalMatch(
                    chunk_id="chunk-1",
                    content="Blister blight is caused by...",
                    score=0.95,
                    document_id="disease-guide",
                    title="Disease Guide",
                    domain="plant_diseases",
                    metadata={"region": "Kenya"},
                ),
            ],
        )

        proto = retrieval_result_to_proto(original)
        result = retrieval_result_from_proto(proto)

        assert result.query == original.query
        assert result.namespace == original.namespace
        assert result.total_matches == original.total_matches
        assert len(result.matches) == len(original.matches)
        assert result.matches[0].chunk_id == original.matches[0].chunk_id
        assert result.matches[0].metadata == original.matches[0].metadata
