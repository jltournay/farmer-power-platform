"""Quality document factory for generating demo documents with scenario patterns.

This module provides DocumentFactory for generating valid Document instances
with quality patterns that align with farmer scenarios.

Story 0.8.4: Profile-Based Data Generation
AC #2: Generated data passes Pydantic validation
AC #5: Scenario-based quality generation
"""

from __future__ import annotations

import hashlib
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

# Set up paths at module load time
_project_root = Path(__file__).parent.parent.parent.parent
_fp_common_path = _project_root / "libs" / "fp-common"
if str(_fp_common_path) not in sys.path:
    sys.path.insert(0, str(_fp_common_path))

_demo_scripts_path = _project_root / "scripts" / "demo"
if str(_demo_scripts_path) not in sys.path:
    sys.path.insert(0, str(_demo_scripts_path))

from fp_common.models.document import (  # noqa: E402
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
)

from .base import BaseModelFactory  # noqa: E402
from .scenarios import FarmerScenario, QualityTier  # noqa: E402


class DocumentFactory(BaseModelFactory[Document]):
    """Factory for generating valid Document instances with quality patterns.

    Generates quality documents that:
    - Reference valid farmer_id, factory_id, grading_model_id from FK registry
    - Follow scenario-based quality patterns when assigned
    - Use realistic quality metrics aligned with grading model tiers

    FK Dependencies:
    - farmer_id -> farmers
    - factory_id -> factories
    - grading_model_id -> grading_models (from E2E seed)
    - source_id -> source_configs (from E2E seed)
    """

    __model__ = Document
    _id_prefix: ClassVar[str] = "DOC-GEN-"
    _entity_type: ClassVar[str] = "documents"
    _id_counter: ClassVar[int] = 0

    # Default source config (must exist in E2E seed)
    DEFAULT_SOURCE_ID: ClassVar[str] = "e2e-qc-analyzer-json"
    DEFAULT_GRADING_MODEL_ID: ClassVar[str] = "tbk_kenya_tea_v1"
    DEFAULT_GRADING_MODEL_VERSION: ClassVar[str] = "1.0"
    DEFAULT_BLOB_CONTAINER: ClassVar[str] = "quality-events-demo"

    @classmethod
    def document_id(cls) -> str:
        """Generate document ID."""
        return cls._next_id()

    @classmethod
    def raw_document(cls) -> dict:
        """Generate raw document reference."""
        farmer_id = cls.get_random_fk("farmers")
        factory_id = cls.get_random_fk("factories")
        batch_num = random.randint(1, 999)

        blob_path = f"results/{factory_id}/{farmer_id}/batch-{batch_num:03d}.json"
        content = f"{blob_path}-{datetime.now(UTC).isoformat()}"
        content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:12]}"

        stored_at = datetime.now(UTC) - timedelta(hours=random.randint(1, 168))

        return {
            "blob_container": cls.DEFAULT_BLOB_CONTAINER,
            "blob_path": blob_path,
            "content_hash": content_hash,
            "size_bytes": random.randint(800, 2000),
            "stored_at": stored_at.isoformat(),
        }

    @classmethod
    def extraction(cls) -> dict:
        """Generate extraction metadata."""
        base_time = datetime.now(UTC) - timedelta(hours=random.randint(1, 168))
        extraction_time = base_time + timedelta(seconds=random.randint(30, 120))

        return {
            "ai_agent_id": "qc_event_extractor",
            "extraction_timestamp": extraction_time.isoformat(),
            "confidence": round(random.uniform(0.85, 0.98), 2),
            "validation_passed": True,
            "validation_warnings": [],
        }

    @classmethod
    def ingestion(cls) -> dict:
        """Generate ingestion metadata."""
        base_time = datetime.now(UTC) - timedelta(hours=random.randint(1, 168))
        process_time = base_time + timedelta(seconds=random.randint(60, 180))

        return {
            "ingestion_id": f"ING-GEN-{random.randint(1000, 9999)}",
            "source_id": cls.DEFAULT_SOURCE_ID,
            "received_at": base_time.isoformat(),
            "processed_at": process_time.isoformat(),
        }

    @classmethod
    def extracted_fields(cls) -> dict:
        """Generate extracted fields with quality metrics.

        Default implementation generates random quality.
        Use generate_with_tier() for scenario-based quality.
        """
        farmer_id = cls.get_random_fk("farmers")
        factory_id = cls.get_random_fk("factories")

        # Random quality tier for default generation
        tier = random.choices(
            [QualityTier.TIER_1, QualityTier.TIER_2, QualityTier.TIER_3, QualityTier.REJECT],
            weights=[30, 40, 25, 5],
        )[0]

        return cls._build_extracted_fields(farmer_id, factory_id, tier)

    @classmethod
    def linkage_fields(cls) -> dict:
        """Generate linkage fields for indexing."""
        farmer_id = cls.get_random_fk("farmers")
        factory_id = cls.get_random_fk("factories")

        return {
            "farmer_id": farmer_id,
            "factory_id": factory_id,
            "grading_model_id": cls.DEFAULT_GRADING_MODEL_ID,
        }

    @classmethod
    def created_at(cls) -> datetime:
        """Generate created_at timestamp."""
        return datetime.now(UTC) - timedelta(hours=random.randint(1, 168))

    @classmethod
    def _build_extracted_fields(
        cls,
        farmer_id: str,
        factory_id: str,
        tier: QualityTier,
    ) -> dict:
        """Build extracted_fields dict for a given quality tier.

        Args:
            farmer_id: Farmer ID for this document.
            factory_id: Factory ID for this document.
            tier: Quality tier determining primary percentage.

        Returns:
            Dict with bag_summary and grading model info.
        """
        min_pct, max_pct = tier.get_primary_percentage_range()
        primary_pct = round(random.uniform(min_pct, max_pct), 1)
        secondary_pct = round(100.0 - primary_pct, 1)

        return {
            "farmer_id": farmer_id,
            "factory_id": factory_id,
            "grading_model_id": cls.DEFAULT_GRADING_MODEL_ID,
            "grading_model_version": cls.DEFAULT_GRADING_MODEL_VERSION,
            "bag_summary": {
                "total_weight_kg": round(random.uniform(20.0, 60.0), 1),
                "primary_percentage": primary_pct,
                "secondary_percentage": secondary_pct,
                "grade": tier.get_grade(),
            },
        }

    @classmethod
    def generate_with_tier(
        cls,
        farmer_id: str,
        factory_id: str,
        tier: QualityTier,
        document_date: datetime | None = None,
    ) -> Document:
        """Generate a document with specific quality tier for a farmer.

        Used by scenario-based generation to create documents that follow
        predefined quality patterns.

        Args:
            farmer_id: Farmer ID for this document.
            factory_id: Factory ID for this document.
            tier: Quality tier for this document.
            document_date: Optional specific date for the document.

        Returns:
            Document instance with specified quality tier.
        """
        doc_date = document_date or (datetime.now(UTC) - timedelta(days=random.randint(0, 90)))

        batch_num = random.randint(1, 999)
        blob_path = f"results/{factory_id}/{farmer_id}/batch-{batch_num:03d}.json"
        content = f"{blob_path}-{doc_date.isoformat()}"
        content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:12]}"

        extracted = cls._build_extracted_fields(farmer_id, factory_id, tier)
        linkage = {
            "farmer_id": farmer_id,
            "factory_id": factory_id,
            "grading_model_id": cls.DEFAULT_GRADING_MODEL_ID,
        }

        return Document(
            document_id=cls._next_id(),
            raw_document=RawDocumentRef(
                blob_container=cls.DEFAULT_BLOB_CONTAINER,
                blob_path=blob_path,
                content_hash=content_hash,
                size_bytes=random.randint(800, 2000),
                stored_at=doc_date,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="qc_event_extractor",
                extraction_timestamp=doc_date + timedelta(seconds=random.randint(30, 120)),
                confidence=round(random.uniform(0.85, 0.98), 2),
                validation_passed=True,
                validation_warnings=[],
            ),
            ingestion=IngestionMetadata(
                ingestion_id=f"ING-GEN-{random.randint(1000, 9999)}",
                source_id=cls.DEFAULT_SOURCE_ID,
                received_at=doc_date,
                processed_at=doc_date + timedelta(seconds=random.randint(60, 180)),
            ),
            extracted_fields=extracted,
            linkage_fields=linkage,
            created_at=doc_date + timedelta(seconds=random.randint(60, 180)),
        )

    @classmethod
    def generate_for_scenario(
        cls,
        farmer_id: str,
        factory_id: str,
        scenario: FarmerScenario,
        days_span: int = 90,
    ) -> list[Document]:
        """Generate documents following a farmer's quality scenario pattern.

        Creates documents spread across the time span, with quality tiers
        matching the scenario's quality_pattern.

        Args:
            farmer_id: Farmer ID for documents.
            factory_id: Factory ID for documents.
            scenario: Farmer scenario with quality pattern.
            days_span: Number of days to spread documents across.

        Returns:
            List of Document instances following the scenario pattern.
        """
        if not scenario.quality_pattern:
            return []  # Inactive farmer - no documents

        documents = []
        pattern_length = len(scenario.quality_pattern)

        # Spread documents evenly across the time span
        days_per_tier = days_span // pattern_length

        for i, tier in enumerate(scenario.quality_pattern):
            # Calculate date range for this tier
            start_day = i * days_per_tier
            end_day = (i + 1) * days_per_tier

            # Generate 1-3 documents per tier period
            docs_in_period = random.randint(1, 3)

            for _ in range(docs_in_period):
                days_ago = random.randint(start_day, end_day)
                doc_date = datetime.now(UTC) - timedelta(days=days_ago)

                doc = cls.generate_with_tier(
                    farmer_id=farmer_id,
                    factory_id=factory_id,
                    tier=tier,
                    document_date=doc_date,
                )
                documents.append(doc)

        return documents

    @classmethod
    def generate_random_for_farmer(
        cls,
        farmer_id: str,
        factory_id: str,
        count: int,
        days_span: int = 90,
    ) -> list[Document]:
        """Generate random quality documents for a farmer without a scenario.

        Args:
            farmer_id: Farmer ID for documents.
            factory_id: Factory ID for documents.
            count: Number of documents to generate.
            days_span: Number of days to spread documents across.

        Returns:
            List of Document instances with random quality.
        """
        documents = []

        for _ in range(count):
            # Random tier with realistic distribution
            tier = random.choices(
                [QualityTier.TIER_1, QualityTier.TIER_2, QualityTier.TIER_3, QualityTier.REJECT],
                weights=[30, 40, 25, 5],
            )[0]

            days_ago = random.randint(0, days_span)
            doc_date = datetime.now(UTC) - timedelta(days=days_ago)

            doc = cls.generate_with_tier(
                farmer_id=farmer_id,
                factory_id=factory_id,
                tier=tier,
                document_date=doc_date,
            )
            documents.append(doc)

        return documents
