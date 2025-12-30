"""Job Registration Service for scheduled pull sources (Story 2.7).

This module provides the JobRegistrationService class which manages
DAPR Jobs for scheduled_pull ingestion sources. It synchronizes jobs
on startup and handles dynamic job registration when source configs
are created/updated/deleted.
"""

from typing import Any

import structlog
from collection_model.infrastructure.dapr_jobs_client import DaprJobsClient
from collection_model.services.source_config_service import SourceConfigService

logger = structlog.get_logger(__name__)


class JobRegistrationService:
    """Manages DAPR Jobs for scheduled_pull ingestion sources.

    Responsibilities:
    - Sync all jobs on service startup
    - Register jobs when new pull sources are created
    - Update jobs when pull sources are modified
    - Remove jobs when pull sources are deleted

    Attributes:
        dapr_jobs_client: Client for DAPR Jobs API.
        source_config_service: Service for loading source configurations.
    """

    def __init__(
        self,
        dapr_jobs_client: DaprJobsClient,
        source_config_service: SourceConfigService,
    ) -> None:
        """Initialize the Job Registration Service.

        Args:
            dapr_jobs_client: Client for DAPR Jobs API.
            source_config_service: Service for loading source configurations.
        """
        self._dapr_jobs = dapr_jobs_client
        self._source_config = source_config_service

    async def sync_all_jobs(self) -> dict[str, int]:
        """Synchronize DAPR Jobs for all scheduled_pull sources.

        Called on service startup to ensure all scheduled_pull sources
        have their corresponding DAPR Jobs registered.

        Returns:
            Dictionary with counts: registered, skipped, failed.
        """
        logger.info("Syncing DAPR Jobs for all scheduled_pull sources")

        registered = 0
        skipped = 0
        failed = 0

        try:
            configs = await self._source_config.get_all_configs()

            for config in configs:
                source_id = config.get("source_id", "unknown")
                ingestion = config.get("ingestion", {})
                mode = ingestion.get("mode", "")

                if mode != "scheduled_pull":
                    logger.debug(
                        "Skipping non-pull source",
                        source_id=source_id,
                        mode=mode,
                    )
                    skipped += 1
                    continue

                success = await self.register_job_for_source(config)
                if success:
                    registered += 1
                else:
                    failed += 1

        except Exception as e:
            logger.error("Failed to sync DAPR Jobs", error=str(e))

        result = {
            "registered": registered,
            "skipped": skipped,
            "failed": failed,
        }

        logger.info(
            "DAPR Jobs sync complete",
            registered=registered,
            skipped=skipped,
            failed=failed,
        )

        return result

    async def register_job_for_source(
        self,
        source_config: dict[str, Any],
    ) -> bool:
        """Register a DAPR Job for a single source configuration.

        Only registers jobs for scheduled_pull mode sources.
        Other modes are skipped and return False.

        Args:
            source_config: Full source configuration dictionary.

        Returns:
            True if job was registered, False otherwise.
        """
        source_id = source_config.get("source_id", "")
        ingestion = source_config.get("ingestion", {})
        mode = ingestion.get("mode", "")

        if mode != "scheduled_pull":
            logger.debug(
                "Skipping non-pull source for job registration",
                source_id=source_id,
                mode=mode,
            )
            return False

        schedule = ingestion.get("schedule", "")
        if not schedule:
            logger.warning(
                "No schedule defined for scheduled_pull source",
                source_id=source_id,
            )
            return False

        success = await self._dapr_jobs.register_job(
            source_id=source_id,
            schedule=schedule,
        )

        if success:
            logger.info(
                "Registered DAPR Job for source",
                source_id=source_id,
                schedule=schedule,
            )
        else:
            logger.error(
                "Failed to register DAPR Job for source",
                source_id=source_id,
                schedule=schedule,
            )

        return success

    async def unregister_job_for_source(self, source_id: str) -> bool:
        """Unregister a DAPR Job for a source.

        Idempotent: succeeds even if job doesn't exist.

        Args:
            source_id: Source identifier.

        Returns:
            True if job was deleted or didn't exist, False on error.
        """
        success = await self._dapr_jobs.delete_job(source_id=source_id)

        if success:
            logger.info(
                "Unregistered DAPR Job for source",
                source_id=source_id,
            )
        else:
            logger.error(
                "Failed to unregister DAPR Job for source",
                source_id=source_id,
            )

        return success
