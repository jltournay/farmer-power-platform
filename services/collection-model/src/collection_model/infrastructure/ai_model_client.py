"""AI Model DAPR client for LLM extraction via gRPC Service Invocation.

This module provides the AiModelClient class for calling the AI Model service
via DAPR gRPC Service Invocation. Collection Model NEVER calls LLM directly -
all LLM operations go through AI Model.

Architecture Decision: All inter-service communication uses gRPC via DAPR
(see infrastructure-decisions.md).

DAPR gRPC Proxying Pattern (Story 0.4.6 fix):
--------------------------------------------
To invoke gRPC services (like AI Model) via DAPR, we use native gRPC
with the `dapr-app-id` metadata header. This is the recommended approach
for gRPC-to-gRPC communication in DAPR (see DAPR docs: howto-invoke-services-grpc).

Pattern:
1. Connect to DAPR sidecar's gRPC port (default 50001)
2. Use native proto stubs (AiModelServiceStub)
3. Add metadata: [("dapr-app-id", ai_model_app_id)]
4. DAPR routes the call to the target service
"""

import json
from typing import Any

import grpc
import structlog
from bson import ObjectId
from collection_model.config import settings
from collection_model.domain.exceptions import ExtractionError
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# DAPR sidecar gRPC port (used for gRPC proxying to other services)
DAPR_GRPC_PORT = 50001


class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles MongoDB ObjectId."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)


class ExtractionRequest(BaseModel):
    """Request to AI Model for structured extraction.

    Attributes:
        raw_content: The raw content to extract from.
        ai_agent_id: AI Model agent ID (from transformation.ai_agent_id).
        source_config: Extraction hints from source configuration.
        content_type: MIME type of the content.
    """

    raw_content: str
    ai_agent_id: str
    source_config: dict[str, Any]
    content_type: str = "application/json"


class ExtractionResponse(BaseModel):
    """Response from AI Model extraction.

    Attributes:
        extracted_fields: Structured data extracted by LLM.
        confidence: Confidence score of the extraction (0.0-1.0).
        validation_passed: Whether extraction passed validation.
        validation_warnings: List of validation warnings.
    """

    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    validation_passed: bool = True
    validation_warnings: list[str] = Field(default_factory=list)


class AiModelClient:
    """DAPR gRPC Service Invocation client for AI Model.

    All LLM calls go through AI Model - Collection Model never calls LLM directly.
    Uses DAPR gRPC Service Invocation for inter-service communication.

    Architecture: All inter-model calls use gRPC via DAPR (infrastructure-decisions.md).
    """

    def __init__(
        self,
        ai_model_app_id: str | None = None,
    ) -> None:
        """Initialize the AI Model client.

        Args:
            ai_model_app_id: AI Model app ID (defaults to settings.ai_model_app_id).
        """
        self._ai_model_app_id = ai_model_app_id or settings.ai_model_app_id

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Call AI Model to extract structured data from raw content.

        Uses DAPR gRPC Service Invocation to call AI Model's Extract method.

        Args:
            request: Extraction request with raw content and agent ID.

        Returns:
            ExtractionResponse with extracted fields and confidence.

        Raises:
            ExtractionError: If extraction fails.
        """
        logger.debug(
            "Calling AI Model for extraction via gRPC",
            ai_agent_id=request.ai_agent_id,
            content_type=request.content_type,
            content_length=len(request.raw_content),
        )

        # Build gRPC request protobuf message
        # Use MongoJSONEncoder to handle ObjectId from MongoDB source_config
        grpc_request = ai_model_pb2.ExtractionRequest(
            raw_content=request.raw_content,
            ai_agent_id=request.ai_agent_id,
            source_config_json=json.dumps(request.source_config, cls=MongoJSONEncoder),
            content_type=request.content_type,
        )

        try:
            # Call AI Model service via DAPR gRPC proxying
            # Connect to DAPR sidecar's gRPC port and use dapr-app-id metadata
            target = f"localhost:{DAPR_GRPC_PORT}"
            async with grpc.aio.insecure_channel(target) as channel:
                stub = ai_model_pb2_grpc.AiModelServiceStub(channel)
                # DAPR routes the call to AI Model via dapr-app-id metadata
                metadata = [("dapr-app-id", self._ai_model_app_id)]
                response = await stub.Extract(grpc_request, metadata=metadata)

            if not response.success:
                error_msg = response.error_message or "Unknown extraction error"
                raise ExtractionError(f"AI Model extraction failed: {error_msg}")

            # Parse extracted fields from JSON response
            extracted_fields_json = response.extracted_fields_json or "{}"
            extracted_fields = json.loads(extracted_fields_json)

            result = ExtractionResponse(
                extracted_fields=extracted_fields,
                confidence=response.confidence,
                validation_passed=response.validation_passed,
                validation_warnings=list(response.validation_warnings),
            )

            logger.info(
                "AI Model extraction completed via gRPC",
                ai_agent_id=request.ai_agent_id,
                confidence=result.confidence,
                validation_passed=result.validation_passed,
                field_count=len(result.extracted_fields),
            )

            return result

        except ExtractionError:
            raise

        except Exception as e:
            logger.exception(
                "Failed to invoke AI Model via gRPC",
                ai_agent_id=request.ai_agent_id,
                error=str(e),
            )
            raise ExtractionError(f"AI Model invocation failed: {e}") from e

    async def health_check(self) -> bool:
        """Check if AI Model service is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            # Call AI Model health check via DAPR gRPC proxying
            target = f"localhost:{DAPR_GRPC_PORT}"
            async with grpc.aio.insecure_channel(target) as channel:
                stub = ai_model_pb2_grpc.AiModelServiceStub(channel)
                metadata = [("dapr-app-id", self._ai_model_app_id)]
                grpc_request = ai_model_pb2.HealthCheckRequest()
                response = await stub.HealthCheck(grpc_request, metadata=metadata)
                return response.healthy

        except Exception as e:
            logger.warning("AI Model health check failed", error=str(e))
            return False
