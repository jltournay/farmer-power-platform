"""AI Model DAPR client for LLM extraction via gRPC Service Invocation.

This module provides the AiModelClient class for calling the AI Model service
via DAPR gRPC Service Invocation. Collection Model NEVER calls LLM directly -
all LLM operations go through AI Model.

Architecture Decision: All inter-service communication uses gRPC via DAPR
(see infrastructure-decisions.md).
"""

import json
from typing import Any

import structlog
from collection_model.config import settings
from collection_model.domain.exceptions import ExtractionError
from dapr.clients import DaprClient
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


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

        # Prepare gRPC request payload as JSON (DAPR handles serialization)
        request_data = {
            "raw_content": request.raw_content,
            "ai_agent_id": request.ai_agent_id,
            "source_config_json": json.dumps(request.source_config),
            "content_type": request.content_type,
        }

        try:
            with DaprClient() as client:
                response = client.invoke_method(
                    app_id=self._ai_model_app_id,
                    method_name="Extract",
                    data=json.dumps(request_data),
                    content_type="application/json",
                )

                # Parse response
                response_data = json.loads(response.data.decode("utf-8"))

                if not response_data.get("success", True):
                    error_msg = response_data.get("error_message", "Unknown extraction error")
                    raise ExtractionError(f"AI Model extraction failed: {error_msg}")

                # Parse extracted fields from JSON
                extracted_fields_json = response_data.get("extracted_fields_json", "{}")
                extracted_fields = json.loads(extracted_fields_json)

                result = ExtractionResponse(
                    extracted_fields=extracted_fields,
                    confidence=response_data.get("confidence", 1.0),
                    validation_passed=response_data.get("validation_passed", True),
                    validation_warnings=response_data.get("validation_warnings", []),
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
            with DaprClient() as client:
                response = client.invoke_method(
                    app_id=self._ai_model_app_id,
                    method_name="HealthCheck",
                    data="{}",
                    content_type="application/json",
                )

                response_data = json.loads(response.data.decode("utf-8"))
                return response_data.get("healthy", False)

        except Exception as e:
            logger.warning("AI Model health check failed", error=str(e))
            return False
