"""
Mock AI Model gRPC Server.

Implements AiModelService for E2E testing with deterministic extraction.
Used to mock AI-based extraction for weather data ingestion tests.

The mock parses Open-Meteo API responses and returns structured weather data.
"""

import json
import logging
from concurrent import futures
from datetime import UTC, datetime

import grpc

# Import generated proto classes
# Note: In Docker, fp_proto is installed from libs/fp-proto
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockAiModelServicer(ai_model_pb2_grpc.AiModelServiceServicer):
    """Mock implementation of AiModelService for E2E testing.

    Provides deterministic extraction for:
    - Weather data from Open-Meteo API (ai_agent_id: mock-weather-extractor)
    - QC data (ai_agent_id: qc_event_extractor) - returns input as-is
    """

    def Extract(self, request, context):
        """Extract structured data from raw content.

        Args:
            request: ExtractionRequest with raw_content, ai_agent_id, etc.
            context: gRPC context.

        Returns:
            ExtractionResponse with extracted fields as JSON.
        """
        logger.info(
            "Extract called",
            extra={
                "ai_agent_id": request.ai_agent_id,
                "content_type": request.content_type,
                "content_length": len(request.raw_content),
            },
        )

        try:
            # Route to appropriate extractor based on agent ID
            if request.ai_agent_id == "mock-weather-extractor":
                extracted = self._extract_weather(request.raw_content)
            elif request.ai_agent_id == "qc_event_extractor":
                extracted = self._extract_qc_event(request.raw_content)
            else:
                # Default: pass through the raw content as extracted fields
                extracted = self._extract_passthrough(request.raw_content)

            return ai_model_pb2.ExtractionResponse(
                success=True,
                extracted_fields_json=json.dumps(extracted),
                confidence=0.95,
                validation_passed=True,
                validation_warnings=[],
                error_message="",
            )

        except Exception as e:
            logger.exception("Extraction failed", extra={"error": str(e)})
            return ai_model_pb2.ExtractionResponse(
                success=False,
                extracted_fields_json="{}",
                confidence=0.0,
                validation_passed=False,
                validation_warnings=[],
                error_message=str(e),
            )

    def HealthCheck(self, request, context):
        """Health check for service readiness.

        Returns:
            HealthCheckResponse indicating service is healthy.
        """
        logger.debug("HealthCheck called")
        return ai_model_pb2.HealthCheckResponse(
            healthy=True,
            version="mock-1.0.0",
        )

    def _extract_weather(self, raw_content: str) -> dict:
        """Extract weather data from Open-Meteo API response.

        Open-Meteo response format:
        {
          "daily": {
            "time": ["2025-01-15", "2025-01-16"],
            "temperature_2m_max": [27.1, 26.5],
            "temperature_2m_min": [18.3, 17.8],
            "precipitation_sum": [5.2, 0.0],
            "relative_humidity_2m_mean": [65, 70]
          }
        }

        Returns deterministic extraction with today's first data point.
        """
        try:
            data = json.loads(raw_content)
            daily = data.get("daily", {})

            # Get first day's data (today's forecast)
            times = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])
            humidity = daily.get("relative_humidity_2m_mean", [])

            # Use first day's values or defaults
            observation_date = times[0] if times else datetime.now(UTC).strftime("%Y-%m-%d")
            temperature_max = temp_max[0] if temp_max else 25.0
            temperature_min = temp_min[0] if temp_min else 15.0
            precipitation = precip[0] if precip else 0.0
            humidity_pct = humidity[0] if humidity else 60

            # Calculate average temperature
            temperature_avg = (temperature_max + temperature_min) / 2

            return {
                "observation_date": observation_date,
                "temperature_c": round(temperature_avg, 1),
                "temperature_min_c": round(temperature_min, 1),
                "temperature_max_c": round(temperature_max, 1),
                "precipitation_mm": round(precipitation, 1),
                "humidity_percent": int(humidity_pct),
                "extracted_at": datetime.now(UTC).isoformat(),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse weather JSON: {e}")
            # Return default values on parse error
            return {
                "observation_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                "temperature_c": 22.0,
                "temperature_min_c": 18.0,
                "temperature_max_c": 26.0,
                "precipitation_mm": 0.0,
                "humidity_percent": 65,
                "extracted_at": datetime.now(UTC).isoformat(),
            }

    def _extract_qc_event(self, raw_content: str) -> dict:
        """Extract QC event data - returns parsed JSON as-is.

        For QC events, the raw content is already structured JSON
        from the QC analyzer, so we just parse and return it.
        """
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            return {}

    def _extract_passthrough(self, raw_content: str) -> dict:
        """Default passthrough extractor - parse JSON and return as-is."""
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            return {"raw": raw_content}


def serve(port: int = 50051):
    """Start the gRPC server.

    Args:
        port: Port to listen on (default 50051).
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ai_model_pb2_grpc.add_AiModelServiceServicer_to_server(MockAiModelServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info(f"Mock AI Model gRPC server started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    import os

    port = int(os.environ.get("MOCK_AI_MODEL_PORT", "50051"))
    serve(port)
