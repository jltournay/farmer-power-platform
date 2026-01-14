"""Proto-to-Pydantic converters for RAG retrieval operations.

Provides converters for:
- Proto -> Pydantic (for gRPC clients like AiModelClient in BFF)
- Pydantic -> Proto (for gRPC service implementations)

Story 0.75.23: RAG Query Service with BFF Integration

Usage:
    from fp_common.converters import (
        retrieval_match_from_proto,
        retrieval_result_from_proto,
        retrieval_query_to_proto,
    )

    # Convert gRPC response to Pydantic model
    result = retrieval_result_from_proto(grpc_response)

    # Convert Pydantic to gRPC request
    request = retrieval_query_to_proto(query)

Reference:
- Pydantic models: fp_common/models/rag.py
- Proto definition: proto/ai_model/v1/ai_model.proto (QueryKnowledge messages)
"""

import json
from typing import Any

from fp_proto.ai_model.v1 import ai_model_pb2

from fp_common.models import RetrievalMatch, RetrievalQuery, RetrievalResult


def retrieval_match_from_proto(proto: ai_model_pb2.RetrievalMatch) -> RetrievalMatch:
    """Convert proto RetrievalMatch to Pydantic RetrievalMatch model.

    Args:
        proto: Proto RetrievalMatch message from ai-model gRPC.

    Returns:
        RetrievalMatch Pydantic model.

    Note:
        Proto metadata_json is parsed to Python dict.
        Empty metadata_json returns empty dict.
    """
    # Parse metadata JSON if present
    metadata: dict[str, Any] = {}
    if proto.metadata_json:
        try:
            metadata = json.loads(proto.metadata_json)
        except json.JSONDecodeError:
            # Log warning but don't fail - use empty dict
            metadata = {}

    return RetrievalMatch(
        chunk_id=proto.chunk_id,
        content=proto.content,
        score=proto.score,
        document_id=proto.document_id,
        title=proto.title,
        domain=proto.domain,
        metadata=metadata,
    )


def retrieval_result_from_proto(proto: ai_model_pb2.QueryKnowledgeResponse) -> RetrievalResult:
    """Convert proto QueryKnowledgeResponse to Pydantic RetrievalResult model.

    Args:
        proto: Proto QueryKnowledgeResponse message from ai-model gRPC.

    Returns:
        RetrievalResult Pydantic model.
    """
    matches = [retrieval_match_from_proto(m) for m in proto.matches]

    return RetrievalResult(
        matches=matches,
        query=proto.query,
        namespace=proto.namespace if proto.namespace else None,
        total_matches=proto.total_matches,
    )


def retrieval_match_to_proto(match: RetrievalMatch) -> ai_model_pb2.RetrievalMatch:
    """Convert Pydantic RetrievalMatch to proto RetrievalMatch message.

    Args:
        match: RetrievalMatch Pydantic model.

    Returns:
        Proto RetrievalMatch message.

    Note:
        Python dict metadata is serialized to JSON string.
    """
    # Serialize metadata to JSON
    metadata_json = ""
    if match.metadata:
        metadata_json = json.dumps(match.metadata)

    return ai_model_pb2.RetrievalMatch(
        chunk_id=match.chunk_id,
        content=match.content,
        score=match.score,
        document_id=match.document_id,
        title=match.title,
        domain=match.domain,
        metadata_json=metadata_json,
    )


def retrieval_result_to_proto(result: RetrievalResult) -> ai_model_pb2.QueryKnowledgeResponse:
    """Convert Pydantic RetrievalResult to proto QueryKnowledgeResponse message.

    Args:
        result: RetrievalResult Pydantic model.

    Returns:
        Proto QueryKnowledgeResponse message.
    """
    proto_matches = [retrieval_match_to_proto(m) for m in result.matches]

    return ai_model_pb2.QueryKnowledgeResponse(
        matches=proto_matches,
        query=result.query,
        namespace=result.namespace or "",
        total_matches=result.total_matches,
    )


def retrieval_query_to_proto(query: RetrievalQuery) -> ai_model_pb2.QueryKnowledgeRequest:
    """Convert Pydantic RetrievalQuery to proto QueryKnowledgeRequest message.

    Args:
        query: RetrievalQuery Pydantic model.

    Returns:
        Proto QueryKnowledgeRequest message.
    """
    return ai_model_pb2.QueryKnowledgeRequest(
        query=query.query,
        domains=list(query.domains),
        top_k=query.top_k,
        confidence_threshold=query.confidence_threshold,
        namespace=query.namespace or "",
    )


def retrieval_query_from_proto(proto: ai_model_pb2.QueryKnowledgeRequest) -> RetrievalQuery:
    """Convert proto QueryKnowledgeRequest to Pydantic RetrievalQuery model.

    Args:
        proto: Proto QueryKnowledgeRequest message.

    Returns:
        RetrievalQuery Pydantic model.
    """
    return RetrievalQuery(
        query=proto.query,
        domains=list(proto.domains),
        top_k=proto.top_k if proto.top_k > 0 else 5,  # Default to 5 if not set
        confidence_threshold=proto.confidence_threshold,
        namespace=proto.namespace if proto.namespace else None,
    )
