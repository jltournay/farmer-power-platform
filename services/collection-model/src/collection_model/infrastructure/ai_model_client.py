"""AI Model DAPR client for LLM extraction via Service Invocation.

This module provides the AiModelClient class for calling the AI Model service
via DAPR Service Invocation. Collection Model NEVER calls LLM directly - all
LLM operations go through AI Model.
"""

from typing import Any

import httpx
import structlog
from collection_model.config import settings
from collection_model.domain.exceptions import ExtractionError
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
    """DAPR Service Invocation client for AI Model.

    All LLM calls go through AI Model - Collection Model never calls LLM directly.
    Uses DAPR Service Invocation for inter-service communication.
    """

    def __init__(
        self,
        dapr_http_port: int | None = None,
        ai_model_app_id: str | None = None,
    ) -> None:
        """Initialize the AI Model client.

        Args:
            dapr_http_port: DAPR HTTP port (defaults to settings.dapr_http_port).
            ai_model_app_id: AI Model app ID (defaults to settings.ai_model_app_id).
        """
        self._dapr_port = dapr_http_port or settings.dapr_http_port
        self._ai_model_app_id = ai_model_app_id or settings.ai_model_app_id
        self._base_url = f"http://localhost:{self._dapr_port}"

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Call AI Model to extract structured data from raw content.

        Uses DAPR Service Invocation:
        POST http://localhost:3500/v1.0/invoke/ai-model/method/extract

        Args:
            request: Extraction request with raw content and agent ID.

        Returns:
            ExtractionResponse with extracted fields and confidence.

        Raises:
            ExtractionError: If extraction fails.
        """
        url = f"{self._base_url}/v1.0/invoke/{self._ai_model_app_id}/method/extract"

        logger.debug(
            "Calling AI Model for extraction",
            ai_agent_id=request.ai_agent_id,
            content_type=request.content_type,
            content_length=len(request.raw_content),
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=request.model_dump(),
                    timeout=60.0,  # LLM calls can be slow
                    headers={
                        "Content-Type": "application/json",
                        "dapr-app-id": self._ai_model_app_id,
                    },
                )
                response.raise_for_status()

                result = ExtractionResponse.model_validate(response.json())
                logger.info(
                    "AI Model extraction completed",
                    ai_agent_id=request.ai_agent_id,
                    confidence=result.confidence,
                    validation_passed=result.validation_passed,
                    field_count=len(result.extracted_fields),
                )
                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "AI Model returned error status",
                ai_agent_id=request.ai_agent_id,
                status_code=e.response.status_code,
                response_text=e.response.text[:500],
            )
            raise ExtractionError(
                f"AI Model extraction failed with status {e.response.status_code}: {e.response.text[:200]}"
            ) from e

        except httpx.TimeoutException as e:
            logger.error(
                "AI Model request timed out",
                ai_agent_id=request.ai_agent_id,
            )
            raise ExtractionError("AI Model extraction timed out") from e

        except httpx.RequestError as e:
            logger.error(
                "Failed to connect to AI Model",
                ai_agent_id=request.ai_agent_id,
                error=str(e),
            )
            raise ExtractionError(f"Failed to connect to AI Model: {e}") from e

        except Exception as e:
            logger.exception(
                "Unexpected error during AI Model extraction",
                ai_agent_id=request.ai_agent_id,
                error=str(e),
            )
            raise ExtractionError(f"Unexpected extraction error: {e}") from e

    async def health_check(self) -> bool:
        """Check if AI Model service is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        url = f"{self._base_url}/v1.0/invoke/{self._ai_model_app_id}/method/health"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                return response.status_code == 200
        except Exception as e:
            logger.warning("AI Model health check failed", error=str(e))
            return False
