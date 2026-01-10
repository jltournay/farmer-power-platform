"""E2E Test Checkpoint Helpers.

Story 0.6.16: AC3 - Checkpoint Test Helpers

Provides checkpoint functions that:
1. Have specific names (e.g., 1-DOCUMENTS_CREATED)
2. Have appropriate timeouts (short for fast ops, long for LLM)
3. Raise CheckpointFailure with diagnostic context on timeout
4. Identify which layer failed (Collection, AI Model, Plantation)

Usage:
    from tests.e2e.helpers.checkpoints import (
        checkpoint_documents_created,
        checkpoint_event_published,
        checkpoint_extraction_complete,
        CheckpointFailure,
    )

    # In your test:
    documents = await checkpoint_documents_created(
        mongodb_direct,
        source_id="e2e-weather-api",
        min_count=1,
    )
"""

import asyncio
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from tests.e2e.helpers.mongodb_direct import MongoDBDirectClient


@dataclass
class CheckpointDiagnostics:
    """Diagnostic information collected when a checkpoint fails."""

    checkpoint_name: str
    layer: str  # "Collection Model", "AI Model", "Plantation Model", "Infrastructure"
    timeout_seconds: float
    elapsed_seconds: float
    last_observed_value: Any
    expected_condition: str
    mongodb_state: dict[str, Any] = field(default_factory=dict)
    service_health: dict[str, str] = field(default_factory=dict)
    recent_errors: list[str] = field(default_factory=list)
    likely_issue: str = ""
    suggested_check: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/display."""
        return {
            "checkpoint": self.checkpoint_name,
            "layer": self.layer,
            "timeout_seconds": self.timeout_seconds,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "last_observed": self.last_observed_value,
            "expected": self.expected_condition,
            "mongodb_state": self.mongodb_state,
            "service_health": self.service_health,
            "recent_errors": self.recent_errors,
            "likely_issue": self.likely_issue,
            "suggested_check": self.suggested_check,
        }


class CheckpointFailure(Exception):
    """Exception raised when a checkpoint times out.

    Contains diagnostic information to help identify the root cause.
    """

    def __init__(self, message: str, diagnostics: CheckpointDiagnostics):
        self.diagnostics = diagnostics
        super().__init__(f"{message}\nDiagnostics: {diagnostics.to_dict()}")


async def _get_collection_count(
    mongodb_direct: MongoDBDirectClient,
    collection: str,
    query: dict[str, Any],
) -> int:
    """Get document count for a collection with query."""
    documents = await mongodb_direct.find_documents(
        collection=collection,
        query=query,
    )
    return len(documents)


async def _get_service_health() -> dict[str, str]:
    """Get health status of all services (non-blocking)."""
    health = {}
    services = [
        ("Collection Model", "http://localhost:8002/health"),
        ("AI Model", "http://localhost:8091/health"),
        ("Plantation Model", "http://localhost:8001/health"),
    ]

    for name, url in services:
        try:
            # Use subprocess to avoid blocking
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                capture_output=True,
                text=True,
                timeout=2,
            )
            status_code = result.stdout.strip()
            health[name] = "healthy" if status_code == "200" else f"HTTP {status_code}"
        except (subprocess.TimeoutExpired, Exception):
            health[name] = "unreachable"

    return health


async def _get_recent_errors(container: str, lines: int = 5) -> list[str]:
    """Get recent errors from container logs (non-blocking)."""
    try:
        result = subprocess.run(
            ["docker", "logs", container, "--tail", str(lines * 10)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        logs = result.stderr + result.stdout
        error_lines = [
            line[:200]
            for line in logs.split("\n")
            if any(kw in line.lower() for kw in ["error", "exception", "failed", "traceback"])
        ]
        return error_lines[-lines:]
    except (subprocess.TimeoutExpired, Exception):
        return ["Could not fetch logs"]


# =============================================================================
# Checkpoint 1: Documents Created
# =============================================================================


async def checkpoint_documents_created(
    mongodb_direct: MongoDBDirectClient,
    source_id: str,
    collection: str = "weather_documents",
    min_count: int = 1,
    timeout: float = 15.0,
    poll_interval: float = 1.0,
) -> list[dict[str, Any]]:
    """Checkpoint 1: Wait for documents to be created in MongoDB.

    This checkpoint verifies that the Collection Model has successfully
    ingested and stored documents. Fast timeout because document creation
    should be near-instant after data fetch.

    Args:
        mongodb_direct: MongoDB direct client fixture.
        source_id: Source ID to filter documents.
        collection: MongoDB collection name.
        min_count: Minimum number of documents expected.
        timeout: Maximum wait time in seconds (default 15s for fast ops).
        poll_interval: Time between polls in seconds.

    Returns:
        List of created documents.

    Raises:
        CheckpointFailure: If min_count not reached within timeout.
    """
    checkpoint_name = f"1-DOCUMENTS_CREATED ({collection})"
    layer = "Collection Model"
    start = time.time()
    last_count = 0

    while time.time() - start < timeout:
        documents = await mongodb_direct.find_documents(
            collection=collection,
            query={"ingestion.source_id": source_id},
        )
        last_count = len(documents)

        if last_count >= min_count:
            return documents

        await asyncio.sleep(poll_interval)

    # Timeout - collect diagnostics
    elapsed = time.time() - start

    # Get MongoDB state
    source_configs_count = await _get_collection_count(mongodb_direct, "source_configs", {})
    weather_docs_count = await _get_collection_count(mongodb_direct, "weather_documents", {})

    # Determine likely issue
    if source_configs_count == 0:
        likely_issue = "No source configs found - seed data may not be loaded"
        suggested_check = "Verify mongo-init.js ran and source_configs has data"
    elif last_count == 0:
        likely_issue = "Pull job not creating documents"
        suggested_check = "Check Collection Model logs for pull job errors"
    else:
        likely_issue = f"Found {last_count} documents but expected {min_count}"
        suggested_check = "Check iteration resolver returns enough items"

    diagnostics = CheckpointDiagnostics(
        checkpoint_name=checkpoint_name,
        layer=layer,
        timeout_seconds=timeout,
        elapsed_seconds=elapsed,
        last_observed_value=last_count,
        expected_condition=f">= {min_count} documents",
        mongodb_state={
            "source_configs_count": source_configs_count,
            "weather_documents_count": weather_docs_count,
        },
        service_health=await _get_service_health(),
        recent_errors=await _get_recent_errors("e2e-collection-model"),
        likely_issue=likely_issue,
        suggested_check=suggested_check,
    )

    raise CheckpointFailure(
        f"CHECKPOINT {checkpoint_name} FAILED: Expected {min_count} documents in {collection}, found {last_count}",
        diagnostics,
    )


# =============================================================================
# Checkpoint 2: Event Published
# =============================================================================


async def checkpoint_event_published(
    mongodb_direct: MongoDBDirectClient,
    event_type: str = "AgentRequestEvent",
    source_id: str | None = None,
    timeout: float = 10.0,
    poll_interval: float = 1.0,
) -> dict[str, Any]:
    """Checkpoint 2: Wait for an event to be published via DAPR.

    This checkpoint verifies that Collection Model published an event
    that AI Model received. Uses workflow_checkpoints collection as
    evidence of event receipt.

    Args:
        mongodb_direct: MongoDB direct client fixture.
        event_type: Type of event to look for.
        source_id: Optional source_id filter.
        timeout: Maximum wait time in seconds (default 10s).
        poll_interval: Time between polls in seconds.

    Returns:
        First matching event/checkpoint document.

    Raises:
        CheckpointFailure: If event not found within timeout.
    """
    checkpoint_name = f"2-EVENT_PUBLISHED ({event_type})"
    layer = "AI Model"
    start = time.time()
    last_count = 0

    while time.time() - start < timeout:
        # Check workflow_checkpoints for evidence of received events
        checkpoints = await mongodb_direct.ai_model_db.workflow_checkpoints.find({}).to_list(100)
        last_count = len(checkpoints)

        if last_count > 0:
            return checkpoints[0]

        await asyncio.sleep(poll_interval)

    # Timeout - collect diagnostics
    elapsed = time.time() - start

    # Check if documents exist in Collection Model
    weather_docs = await mongodb_direct.find_documents(
        collection="weather_documents",
        query={"ingestion.source_id": source_id} if source_id else {},
    )

    if len(weather_docs) == 0:
        likely_issue = "No documents exist - Collection Model didn't create any"
        suggested_check = "Run Checkpoint 1 first, then this checkpoint"
    else:
        # Documents exist but no checkpoints - event not published or received
        doc = weather_docs[0]
        extraction_status = doc.get("extraction", {}).get("status", "unknown")
        if extraction_status == "pending":
            likely_issue = "Documents exist with extraction.status=pending but no workflow checkpoint"
            suggested_check = "Check DAPR pub/sub - event may not have been published or received"
        else:
            likely_issue = f"Documents exist with extraction.status={extraction_status}"
            suggested_check = "Check AI Model logs for event handling errors"

    diagnostics = CheckpointDiagnostics(
        checkpoint_name=checkpoint_name,
        layer=layer,
        timeout_seconds=timeout,
        elapsed_seconds=elapsed,
        last_observed_value=last_count,
        expected_condition=f">= 1 {event_type}",
        mongodb_state={
            "workflow_checkpoints_count": last_count,
            "weather_documents_count": len(weather_docs),
        },
        service_health=await _get_service_health(),
        recent_errors=await _get_recent_errors("e2e-ai-model"),
        likely_issue=likely_issue,
        suggested_check=suggested_check,
    )

    raise CheckpointFailure(
        f"CHECKPOINT {checkpoint_name} FAILED: No workflow checkpoints found (expected event receipt)",
        diagnostics,
    )


# =============================================================================
# Checkpoint 3: Extraction Complete
# =============================================================================


async def checkpoint_extraction_complete(
    mongodb_direct: MongoDBDirectClient,
    source_id: str,
    collection: str = "weather_documents",
    timeout: float = 90.0,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Checkpoint 3: Wait for AI extraction to complete.

    This checkpoint verifies that AI Model has processed the document
    and updated extraction.status to 'complete'. Long timeout because
    LLM calls can take significant time.

    Args:
        mongodb_direct: MongoDB direct client fixture.
        source_id: Source ID to filter documents.
        collection: MongoDB collection name.
        timeout: Maximum wait time in seconds (default 90s for LLM).
        poll_interval: Time between polls in seconds.

    Returns:
        Document with completed extraction.

    Raises:
        CheckpointFailure: If extraction doesn't complete within timeout.
    """
    checkpoint_name = f"3-EXTRACTION_COMPLETE ({collection})"
    layer = "AI Model"
    start = time.time()
    last_status = "unknown"
    last_error: str | None = None

    while time.time() - start < timeout:
        documents = await mongodb_direct.find_documents(
            collection=collection,
            query={"ingestion.source_id": source_id},
        )

        for doc in documents:
            extraction = doc.get("extraction", {})
            status = extraction.get("status", "unknown")
            last_status = status

            if status == "complete":
                return doc
            elif status == "failed":
                last_error = extraction.get("error_message", "Unknown error")
                # Failed immediately - don't wait for timeout
                break

        # If we found a failed status, break out of the loop
        if last_error:
            break

        await asyncio.sleep(poll_interval)

    # Timeout or failure - collect diagnostics
    elapsed = time.time() - start

    # Get document state
    documents = await mongodb_direct.find_documents(
        collection=collection,
        query={"ingestion.source_id": source_id},
    )

    # Determine likely issue based on status
    if len(documents) == 0:
        likely_issue = "No documents found - Collection Model issue"
        suggested_check = "Run Checkpoint 1 first"
    elif last_error:
        likely_issue = f"Extraction failed with error: {last_error}"
        suggested_check = "Check AI Model logs for detailed error"
    elif last_status == "pending":
        likely_issue = "Extraction stuck in 'pending' - AI Model may not have received event"
        suggested_check = "Check OPENROUTER_API_KEY is set inside AI Model container"
    elif last_status == "processing":
        likely_issue = "Extraction stuck in 'processing' - LLM call may be hanging"
        suggested_check = "Check AI Model logs for LLM timeout or API errors"
    else:
        likely_issue = f"Unexpected extraction status: {last_status}"
        suggested_check = "Check AI Model logs for workflow errors"

    # Check for common env var issue
    if not os.environ.get("OPENROUTER_API_KEY"):
        likely_issue += " (OPENROUTER_API_KEY not set in shell)"
        suggested_check = "Set OPENROUTER_API_KEY and rebuild: bash scripts/e2e-up.sh --build"

    diagnostics = CheckpointDiagnostics(
        checkpoint_name=checkpoint_name,
        layer=layer,
        timeout_seconds=timeout,
        elapsed_seconds=elapsed,
        last_observed_value=last_status,
        expected_condition="extraction.status == 'complete'",
        mongodb_state={
            "documents_count": len(documents),
            "last_extraction_status": last_status,
            "last_error": last_error,
        },
        service_health=await _get_service_health(),
        recent_errors=await _get_recent_errors("e2e-ai-model"),
        likely_issue=likely_issue,
        suggested_check=suggested_check,
    )

    raise CheckpointFailure(
        f"CHECKPOINT {checkpoint_name} FAILED: Extraction did not complete (last status: {last_status})",
        diagnostics,
    )


# =============================================================================
# Convenience function: Run diagnostics
# =============================================================================


async def run_diagnostics(
    mongodb_direct: MongoDBDirectClient,
    focus: str = "weather",
) -> dict[str, Any]:
    """Run programmatic diagnostics for debugging.

    This is a Python equivalent of the bash e2e-diagnose.sh script.

    Args:
        mongodb_direct: MongoDB direct client fixture.
        focus: Focus area ('weather', 'quality', 'all').

    Returns:
        Diagnostic report as a dictionary.
    """
    report: dict[str, Any] = {
        "focus": focus,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "service_health": await _get_service_health(),
        "mongodb_state": {},
        "recent_errors": {},
    }

    # MongoDB state
    if focus in ("weather", "all"):
        report["mongodb_state"]["weather_documents"] = await _get_collection_count(
            mongodb_direct, "weather_documents", {}
        )

    if focus in ("quality", "all"):
        report["mongodb_state"]["quality_documents"] = await _get_collection_count(
            mongodb_direct, "quality_documents", {}
        )

    report["mongodb_state"]["source_configs"] = await _get_collection_count(mongodb_direct, "source_configs", {})
    report["mongodb_state"]["agent_configs"] = len(await mongodb_direct.ai_model_db.agent_configs.find({}).to_list(100))
    report["mongodb_state"]["workflow_checkpoints"] = len(
        await mongodb_direct.ai_model_db.workflow_checkpoints.find({}).to_list(100)
    )

    # Recent errors
    for container in ["e2e-collection-model", "e2e-ai-model", "e2e-plantation-model"]:
        report["recent_errors"][container] = await _get_recent_errors(container)

    return report
