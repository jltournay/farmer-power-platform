"""DAPR Jobs client for scheduled pull ingestion (Story 2.7).

This module provides the DaprJobsClient class for managing DAPR Jobs
via the DAPR HTTP API. Jobs are used to trigger scheduled data pulls
from external APIs (e.g., weather data, market prices).

DAPR Jobs API (v1.15+):
- POST /v1.0/jobs/{job_name} - Register/update a job
- DELETE /v1.0/jobs/{job_name} - Delete a job
- GET /v1.0/jobs - List all jobs (optional)
"""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class DaprJobsClient:
    """Client for DAPR Jobs HTTP API.

    Manages scheduled jobs for pull-mode data ingestion sources.
    Each job triggers a callback to the Collection Model service
    at the configured schedule.

    Attributes:
        dapr_host: DAPR sidecar host (default: localhost).
        dapr_port: DAPR sidecar HTTP port (default: 3500).
        app_port: Application port for job callbacks (default: 8080).
    """

    def __init__(
        self,
        dapr_host: str = "localhost",
        dapr_port: int = 3500,
        app_port: int = 8080,
    ) -> None:
        """Initialize the DAPR Jobs client.

        Args:
            dapr_host: DAPR sidecar host.
            dapr_port: DAPR sidecar HTTP port.
            app_port: Application port for job callbacks.
        """
        self._dapr_host = dapr_host
        self._dapr_port = dapr_port
        self._app_port = app_port
        self._base_url = f"http://{dapr_host}:{dapr_port}"

    async def register_job(
        self,
        source_id: str,
        schedule: str,
    ) -> bool:
        """Register a DAPR Job for a pull-mode source.

        Creates or updates a DAPR Job that will trigger at the specified
        schedule. The job callback will be sent to:
        POST /api/v1/triggers/job/{source_id}

        Args:
            source_id: Unique identifier for the data source.
            schedule: Cron expression or DAPR schedule string.
                     Examples: "0 6 * * *" (daily at 6 AM),
                              "@every 6h" (every 6 hours).

        Returns:
            True if job was registered successfully, False otherwise.
        """
        job_name = self._sanitize_job_name(source_id)
        url = f"{self._base_url}/v1.0/jobs/{job_name}"

        # DAPR Jobs payload
        payload = {
            "schedule": schedule,
            "repeats": 0,  # 0 = indefinite (run until deleted)
            "data": {
                "source_id": source_id,
            },
            "callback": {
                "method": "POST",
                "path": f"/api/v1/triggers/job/{source_id}",
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()

            logger.info(
                "Registered DAPR Job",
                job_name=job_name,
                source_id=source_id,
                schedule=schedule,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to register DAPR Job",
                job_name=job_name,
                source_id=source_id,
                schedule=schedule,
                error=str(e),
            )
            return False

    async def delete_job(self, source_id: str) -> bool:
        """Delete a DAPR Job for a pull-mode source.

        Idempotent: returns True even if job doesn't exist.

        Args:
            source_id: Unique identifier for the data source.

        Returns:
            True if job was deleted or didn't exist, False on error.
        """
        job_name = self._sanitize_job_name(source_id)
        url = f"{self._base_url}/v1.0/jobs/{job_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, timeout=10.0)
                # 204 = deleted, 404 = didn't exist (both OK)
                if response.status_code in (204, 404):
                    logger.info(
                        "Deleted DAPR Job",
                        job_name=job_name,
                        source_id=source_id,
                        status_code=response.status_code,
                    )
                    return True
                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(
                "Failed to delete DAPR Job",
                job_name=job_name,
                source_id=source_id,
                error=str(e),
            )
            return False

    async def list_jobs(self) -> list[dict[str, Any]]:
        """List all registered DAPR Jobs.

        Optional debugging feature - lists all jobs registered
        with the DAPR sidecar.

        Returns:
            List of job dictionaries with name, schedule, etc.
            Empty list on error or no jobs.
        """
        url = f"{self._base_url}/v1.0/jobs"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("jobs", [])

        except Exception as e:
            logger.warning(
                "Failed to list DAPR Jobs",
                error=str(e),
            )
            return []

    def _sanitize_job_name(self, source_id: str) -> str:
        """Sanitize source_id to valid DAPR job name.

        DAPR job names should be alphanumeric with hyphens.
        We keep the source_id as-is since our naming convention
        already uses valid characters (alphanumeric, hyphens, underscores).

        Args:
            source_id: Original source identifier.

        Returns:
            Sanitized job name.
        """
        # Keep source_id as job name - our naming convention is compatible
        # with DAPR (alphanumeric, hyphens, underscores)
        return source_id
