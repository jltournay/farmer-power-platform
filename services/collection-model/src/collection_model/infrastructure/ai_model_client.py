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

gRPC Client Retry Pattern (ADR-005):
------------------------------------
All gRPC clients MUST implement retry logic with singleton channel pattern.
This ensures auto-recovery from transient failures without pod restart.

- Singleton channel: created once, reused across calls
- Tenacity retry: 3 attempts with exponential backoff (1-10s)
- Channel reset on UNAVAILABLE error forces reconnection
"""

import json
from typing import Any

import grpc
import structlog
from bson import ObjectId
from collection_model.config import settings
from collection_model.domain.exceptions import ExtractionError
from fp_common.models.source_config import SourceConfig
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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
        source_config: Typed SourceConfig model for extraction hints.
        content_type: MIME type of the content.
    """

    model_config = {"arbitrary_types_allowed": True}

    raw_content: str
    ai_agent_id: str
    source_config: SourceConfig
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


class ServiceUnavailableError(Exception):
    """Raised when the AI Model service is unavailable after retries.

    Attributes:
        app_id: The DAPR app ID of the service.
        method_name: The gRPC method that failed.
        attempt_count: Number of retry attempts made.
    """

    def __init__(
        self,
        message: str,
        app_id: str,
        method_name: str,
        attempt_count: int = 3,
    ) -> None:
        self.app_id = app_id
        self.method_name = method_name
        self.attempt_count = attempt_count
        super().__init__(f"{message} (app_id={app_id}, method={method_name}, attempts={attempt_count})")


class AiModelClient:
    """DAPR gRPC Service Invocation client for AI Model.

    All LLM calls go through AI Model - Collection Model never calls LLM directly.
    Uses DAPR gRPC Service Invocation for inter-service communication.

    Architecture: All inter-model calls use gRPC via DAPR (infrastructure-decisions.md).

    Retry Pattern (ADR-005):
    - Singleton channel pattern: channel created once and reused
    - Tenacity retry on all RPC methods: 3 attempts, exponential backoff 1-10s
    - Channel reset on UNAVAILABLE error forces reconnection on next attempt
    """

    def __init__(
        self,
        ai_model_app_id: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the AI Model client.

        Args:
            ai_model_app_id: AI Model app ID (defaults to settings.ai_model_app_id).
            channel: Optional pre-configured gRPC channel (for testing).
        """
        self._ai_model_app_id = ai_model_app_id or settings.ai_model_app_id
        self._channel: grpc.aio.Channel | None = channel
        self._stub: ai_model_pb2_grpc.AiModelServiceStub | None = None

    async def _get_stub(self) -> ai_model_pb2_grpc.AiModelServiceStub:
        """Get or create the gRPC stub (singleton pattern).

        Creates the channel lazily on first use and reuses it for subsequent calls.
        This is the recommended pattern per ADR-005.

        Returns:
            The gRPC stub for AI Model service.
        """
        if self._stub is None:
            if self._channel is None:
                target = f"localhost:{DAPR_GRPC_PORT}"
                logger.debug(
                    "Creating gRPC channel to DAPR sidecar",
                    target=target,
                    app_id=self._ai_model_app_id,
                )
                self._channel = grpc.aio.insecure_channel(
                    target,
                    options=[
                        ("grpc.keepalive_time_ms", 30000),
                        ("grpc.keepalive_timeout_ms", 10000),
                    ],
                )
            self._stub = ai_model_pb2_grpc.AiModelServiceStub(self._channel)
        return self._stub

    def _get_metadata(self) -> list[tuple[str, str]]:
        """Get gRPC call metadata for DAPR service invocation.

        Returns:
            List of metadata tuples including dapr-app-id.
        """
        return [("dapr-app-id", self._ai_model_app_id)]

    def _reset_channel(self) -> None:
        """Reset channel and stub on connection error.

        Forces reconnection on the next call. This is called when an
        UNAVAILABLE error is encountered to ensure fresh connection.
        """
        logger.warning(
            "Resetting gRPC channel after connection error",
            app_id=self._ai_model_app_id,
        )
        self._channel = None
        self._stub = None

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Call AI Model to extract structured data from raw content.

        Uses DAPR gRPC Service Invocation to call AI Model's Extract method.
        Includes retry logic per ADR-005: 3 attempts with exponential backoff.

        Args:
            request: Extraction request with raw content and agent ID.

        Returns:
            ExtractionResponse with extracted fields and confidence.

        Raises:
            ExtractionError: If extraction fails after all retries.
            ServiceUnavailableError: If service is unavailable after all retries.
        """
        try:
            return await self._extract_with_retry(request)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error(
                    "AI Model service unavailable after all retries",
                    app_id=self._ai_model_app_id,
                    method="Extract",
                    attempts=3,
                )
                raise ServiceUnavailableError(
                    message="AI Model service unavailable after retries",
                    app_id=self._ai_model_app_id,
                    method_name="Extract",
                    attempt_count=3,
                ) from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _extract_with_retry(self, request: ExtractionRequest) -> ExtractionResponse:
        """Internal extraction with retry logic (ADR-005).

        This method is wrapped by extract() which transforms the final error
        to ServiceUnavailableError with context per AC4.
        """
        logger.debug(
            "Calling AI Model for extraction via gRPC",
            ai_agent_id=request.ai_agent_id,
            content_type=request.content_type,
            content_length=len(request.raw_content),
        )

        # Build gRPC request protobuf message
        # Serialize SourceConfig Pydantic model to JSON for gRPC transport
        # Use MongoJSONEncoder to handle any remaining MongoDB ObjectId fields
        source_config_dict = request.source_config.model_dump(mode="json")
        grpc_request = ai_model_pb2.ExtractionRequest(
            raw_content=request.raw_content,
            ai_agent_id=request.ai_agent_id,
            source_config_json=json.dumps(source_config_dict, cls=MongoJSONEncoder),
            content_type=request.content_type,
        )

        try:
            stub = await self._get_stub()
            response = await stub.Extract(grpc_request, metadata=self._get_metadata())

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

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                # Reset channel to force reconnection on next attempt
                self._reset_channel()
                logger.warning(
                    "AI Model service unavailable, will retry",
                    app_id=self._ai_model_app_id,
                    error=str(e),
                )
            raise

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

        Includes retry logic per ADR-005: 3 attempts with exponential backoff.

        Returns:
            True if healthy, False otherwise.

        Raises:
            ServiceUnavailableError: If service is unavailable after all retries.
        """
        try:
            return await self._health_check_with_retry()
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error(
                    "AI Model service unavailable after all retries",
                    app_id=self._ai_model_app_id,
                    method="HealthCheck",
                    attempts=3,
                )
                raise ServiceUnavailableError(
                    message="AI Model service unavailable after retries",
                    app_id=self._ai_model_app_id,
                    method_name="HealthCheck",
                    attempt_count=3,
                ) from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _health_check_with_retry(self) -> bool:
        """Internal health check with retry logic (ADR-005)."""
        try:
            stub = await self._get_stub()
            grpc_request = ai_model_pb2.HealthCheckRequest()
            response = await stub.HealthCheck(grpc_request, metadata=self._get_metadata())
            return response.healthy

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                # Reset channel to force reconnection on next attempt
                self._reset_channel()
            logger.warning(
                "AI Model health check failed",
                app_id=self._ai_model_app_id,
                error=str(e),
            )
            raise

        except Exception as e:
            logger.warning("AI Model health check failed", error=str(e))
            return False

    async def close(self) -> None:
        """Clean up resources by closing the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
