"""Integration tests for Farmer Auto-Assignment (Story 1.11).

These tests validate the auto-assignment logic with real MongoDB,
testing the full flow of:
1. Quality event processing with collection_point_id
2. Automatic farmer assignment to collection point
3. Idempotent assignment (no duplicates)
4. Cross-factory assignment (N:M relationship)

Usage:
    PYTHONPATH="${PYTHONPATH}:libs/fp-common/src:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src" \
        pytest tests/integration/test_farmer_auto_assignment.py -v -m mongodb
"""

import datetime as dt
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase

from tests.conftest_integration import plantation_test_db  # noqa: F401


def create_sample_document(
    document_id: str = "doc-123",
    farmer_id: str = "FRM-INT-001",
    grading_model_id: str = "tbk_kenya_tea_v1",
    factory_id: str = "FAC-INT-001",
    collection_point_id: str | None = "CP-INT-001",
) -> dict:
    """Create a sample quality document with optional collection_point_id."""
    now = datetime.now(UTC).isoformat()
    extracted_fields = {
        "grading_model_id": grading_model_id,
        "grading_model_version": "1.0.0",
        "factory_id": factory_id,
        "bag_summary": {
            "total_weight_kg": 25.0,
            "primary_percentage": 80.0,
            "secondary_percentage": 20.0,
        },
    }
    linkage_fields = {
        "farmer_id": farmer_id,
        "factory_id": factory_id,
    }

    if collection_point_id:
        extracted_fields["collection_point_id"] = collection_point_id
        linkage_fields["collection_point_id"] = collection_point_id

    return {
        "document_id": document_id,
        "raw_document": {
            "blob_container": "quality-data",
            "blob_path": "factory/batch.json",
            "content_hash": "sha256:test",
            "size_bytes": 1024,
            "stored_at": now,
        },
        "extraction": {
            "ai_agent_id": "extractor-v1",
            "extraction_timestamp": now,
            "confidence": 0.95,
            "validation_passed": True,
            "validation_warnings": [],
        },
        "ingestion": {
            "ingestion_id": "ing-001",
            "source_id": "qc-analyzer-result",
            "received_at": now,
            "processed_at": now,
        },
        "extracted_fields": extracted_fields,
        "linkage_fields": linkage_fields,
        "created_at": now,
    }


@pytest.fixture
def sample_farmer() -> dict:
    """Create a sample farmer document for MongoDB."""
    return {
        "_id": "FRM-INT-001",
        "id": "FRM-INT-001",
        "grower_number": "GN-INT-001",
        "first_name": "Integration",
        "last_name": "Test",
        "region_id": "integration-highland",
        "farm_location": {
            "latitude": 0.29,
            "longitude": 35.29,
            "altitude_meters": 1800.0,
        },
        "contact": {
            "phone": "+254712999001",
            "email": "",
            "address": "Integration Village",
        },
        "farm_size_hectares": 2.0,
        "farm_scale": "medium",
        "national_id": "99999001",
        "registration_date": "2025-01-01T00:00:00Z",
        "is_active": True,
        "notification_channel": "sms",
        "interaction_pref": "text",
        "pref_lang": "en",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_region() -> dict:
    """Create a sample region document for MongoDB."""
    return {
        "_id": "integration-highland",
        "region_id": "integration-highland",
        "name": "Integration Highland",
        "county": "Integration",
        "country": "Kenya",
        "geography": {
            "center_gps": {"lat": 0.29, "lng": 35.29},
            "radius_km": 25,
            "altitude_band": {
                "min_meters": 1800,
                "max_meters": 2200,
                "label": "highland",
            },
        },
        "flush_calendar": {
            "first_flush": {
                "start": "03-15",
                "end": "05-15",
                "characteristics": "Highest quality",
            },
            "monsoon_flush": {
                "start": "06-15",
                "end": "09-30",
                "characteristics": "High volume",
            },
            "autumn_flush": {
                "start": "10-15",
                "end": "12-15",
                "characteristics": "Balanced quality",
            },
            "dormant": {
                "start": "12-16",
                "end": "03-14",
                "characteristics": "Minimal growth",
            },
        },
        "agronomic": {
            "soil_type": "volcanic_red",
            "typical_diseases": ["blister_blight", "grey_blight"],
            "harvest_peak_hours": "06:00-10:00",
            "frost_risk": True,
        },
        "weather_config": {
            "api_location": {"lat": 0.29, "lng": 35.29},
            "altitude_for_api": 1900,
            "collection_time": "06:00",
        },
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_collection_point() -> dict:
    """Create a sample collection point for MongoDB."""
    return {
        "_id": "CP-INT-001",
        "id": "CP-INT-001",
        "name": "Integration CP 1",
        "factory_id": "FAC-INT-001",
        "location": {
            "latitude": 0.28,
            "longitude": 35.28,
            "altitude_meters": 1780.0,
        },
        "region_id": "integration-highland",
        "clerk_id": "CLK-INT-001",
        "clerk_phone": "+254712999101",
        "operating_hours": {
            "weekdays": "06:00-14:00",
            "weekends": "07:00-12:00",
        },
        "collection_days": ["mon", "tue", "wed", "thu", "fri", "sat"],
        "capacity": {
            "max_daily_kg": 5000,
            "storage_type": "covered_shed",
            "has_weighing_scale": True,
            "has_qc_device": True,
        },
        "farmer_ids": [],  # Empty - farmer not assigned yet
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_collection_point_2() -> dict:
    """Create a second collection point at different factory."""
    return {
        "_id": "CP-INT-002",
        "id": "CP-INT-002",
        "name": "Integration CP 2",
        "factory_id": "FAC-INT-002",  # Different factory!
        "location": {
            "latitude": 0.32,
            "longitude": 35.32,
            "altitude_meters": 1820.0,
        },
        "region_id": "integration-highland",
        "clerk_id": "CLK-INT-002",
        "clerk_phone": "+254712999102",
        "operating_hours": {
            "weekdays": "06:00-14:00",
            "weekends": "07:00-12:00",
        },
        "collection_days": ["mon", "wed", "fri"],
        "capacity": {
            "max_daily_kg": 3000,
            "storage_type": "covered_shed",
            "has_weighing_scale": True,
            "has_qc_device": False,
        },
        "farmer_ids": [],  # Empty - farmer not assigned yet
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_factory() -> dict:
    """Create a sample factory document."""
    return {
        "_id": "FAC-INT-001",
        "id": "FAC-INT-001",
        "code": "FAC-INT-001",
        "name": "Integration Factory",
        "region_id": "integration-highland",
        "location": {"latitude": 0.3, "longitude": 35.3, "altitude_meters": 1800.0},
        "contact": {"phone": "+254712999201", "email": "factory@test.com"},
        "grading_models": ["tbk_kenya_tea_v1"],
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_grading_model() -> dict:
    """Create a sample grading model document."""
    return {
        "_id": "tbk_kenya_tea_v1:1.0.0",
        "model_id": "tbk_kenya_tea_v1",
        "model_version": "1.0.0",
        "regulatory_authority": "Tea Board of Kenya",
        "crops_name": "Tea",
        "market_name": "Kenya_TBK",
        "grading_type": "binary",
        "attributes": {},
        "grade_rules": {},
        "grade_labels": {"ACCEPT": "Primary", "REJECT": "Secondary"},
        "active_at_factory": ["FAC-INT-001"],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_farmer_performance() -> dict:
    """Create a sample farmer performance document."""
    today = dt.date.today().isoformat()
    return {
        "_id": "FRM-INT-001",
        "farmer_id": "FRM-INT-001",
        "grading_model_id": "tbk_kenya_tea_v1",
        "grading_model_version": "1.0.0",
        "farm_size_hectares": 2.0,
        "farm_scale": "medium",
        "historical": {
            "primary_percentage_30d": 75.0,
            "primary_percentage_90d": 70.0,
            "improvement_trend": "improving",
            "total_deliveries_30d": 10,
            "total_deliveries_90d": 30,
            "total_kg_30d": 250.0,
            "total_kg_90d": 750.0,
            "grade_counts_30d": {},
            "grade_counts_90d": {},
            "attribute_distributions_30d": {},
        },
        "today": {
            "deliveries": 2,
            "total_kg": 45.0,
            "grade_counts": {"Primary": 2},
            "attribute_distributions": {},
            "metrics_date": today,
        },
    }


@pytest_asyncio.fixture
async def seeded_db(
    plantation_test_db: AsyncIOMotorDatabase,  # noqa: F811
    sample_farmer: dict,
    sample_region: dict,
    sample_collection_point: dict,
    sample_collection_point_2: dict,
    sample_factory: dict,
    sample_grading_model: dict,
    sample_farmer_performance: dict,
) -> AsyncIOMotorDatabase:
    """Seed the test database with required documents."""
    # Insert seed data
    await plantation_test_db.farmers.insert_one(sample_farmer)
    await plantation_test_db.regions.insert_one(sample_region)
    await plantation_test_db.collection_points.insert_many([sample_collection_point, sample_collection_point_2])
    await plantation_test_db.factories.insert_one(sample_factory)
    await plantation_test_db.grading_models.insert_one(sample_grading_model)
    await plantation_test_db.farmer_performance.insert_one(sample_farmer_performance)

    return plantation_test_db


@pytest.mark.integration
@pytest.mark.mongodb
class TestFarmerAutoAssignmentIntegration:
    """Integration tests for farmer auto-assignment with real MongoDB."""

    @pytest.mark.asyncio
    async def test_auto_assign_farmer_on_quality_event_e2e(
        self,
        seeded_db: AsyncIOMotorDatabase,
    ) -> None:
        """Test full auto-assignment flow: quality event → farmer assigned to CP.

        AC 1.11.1: Given a quality event with collection_point_id,
        farmer should be automatically assigned to that CP.
        """
        # Arrange: Create repositories with real MongoDB
        from fp_common.models import Document
        from plantation_model.domain.services.quality_event_processor import (
            QualityEventProcessor,
        )
        from plantation_model.infrastructure.repositories.collection_point_repository import (
            CollectionPointRepository,
        )
        from plantation_model.infrastructure.repositories.factory_repository import (
            FactoryRepository,
        )
        from plantation_model.infrastructure.repositories.farmer_performance_repository import (
            FarmerPerformanceRepository,
        )
        from plantation_model.infrastructure.repositories.farmer_repository import (
            FarmerRepository,
        )
        from plantation_model.infrastructure.repositories.grading_model_repository import (
            GradingModelRepository,
        )
        from plantation_model.infrastructure.repositories.region_repository import (
            RegionRepository,
        )

        farmer_repo = FarmerRepository(seeded_db)
        factory_repo = FactoryRepository(seeded_db)
        region_repo = RegionRepository(seeded_db)
        cp_repo = CollectionPointRepository(seeded_db)
        grading_model_repo = GradingModelRepository(seeded_db)
        farmer_perf_repo = FarmerPerformanceRepository(seeded_db)

        # Verify farmer is NOT in CP before processing
        cp_before = await cp_repo.get_by_id("CP-INT-001")
        assert cp_before is not None
        assert "FRM-INT-001" not in cp_before.farmer_ids

        # Create mock collection client that returns our test document
        mock_collection_client = AsyncMock()
        doc_data = create_sample_document(
            document_id="doc-int-001",
            farmer_id="FRM-INT-001",
            collection_point_id="CP-INT-001",
        )
        mock_collection_client.get_document.return_value = Document.model_validate(doc_data)

        # Create processor with all repos including cp_repo
        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=grading_model_repo,
            farmer_performance_repo=farmer_perf_repo,
            farmer_repo=farmer_repo,
            factory_repo=factory_repo,
            region_repo=region_repo,
            cp_repo=cp_repo,
        )

        # Act: Process quality event
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor.process(
                document_id="doc-int-001",
                farmer_id="FRM-INT-001",
            )

        # Assert: Processing succeeded
        assert result["status"] == "success"

        # Assert: Farmer is now assigned to CP
        cp_after = await cp_repo.get_by_id("CP-INT-001")
        assert cp_after is not None
        assert "FRM-INT-001" in cp_after.farmer_ids

    @pytest.mark.asyncio
    async def test_cross_factory_assignment_integration(
        self,
        seeded_db: AsyncIOMotorDatabase,
    ) -> None:
        """Test farmer can be assigned to CPs at different factories (N:M relationship).

        AC 1.11.3: Given farmer is assigned to CP-A at Factory-1,
        when quality result arrives at CP-B at Factory-2,
        farmer should be assigned to BOTH CPs.
        """
        # Arrange
        from fp_common.models import Document
        from plantation_model.domain.services.quality_event_processor import (
            QualityEventProcessor,
        )
        from plantation_model.infrastructure.repositories.collection_point_repository import (
            CollectionPointRepository,
        )
        from plantation_model.infrastructure.repositories.factory_repository import (
            FactoryRepository,
        )
        from plantation_model.infrastructure.repositories.farmer_performance_repository import (
            FarmerPerformanceRepository,
        )
        from plantation_model.infrastructure.repositories.farmer_repository import (
            FarmerRepository,
        )
        from plantation_model.infrastructure.repositories.grading_model_repository import (
            GradingModelRepository,
        )
        from plantation_model.infrastructure.repositories.region_repository import (
            RegionRepository,
        )

        farmer_repo = FarmerRepository(seeded_db)
        factory_repo = FactoryRepository(seeded_db)
        region_repo = RegionRepository(seeded_db)
        cp_repo = CollectionPointRepository(seeded_db)
        grading_model_repo = GradingModelRepository(seeded_db)
        farmer_perf_repo = FarmerPerformanceRepository(seeded_db)

        # First, assign farmer to CP-1 via first quality event
        mock_collection_client = AsyncMock()
        doc_data_1 = create_sample_document(
            document_id="doc-int-002",
            farmer_id="FRM-INT-001",
            factory_id="FAC-INT-001",
            collection_point_id="CP-INT-001",
        )
        mock_collection_client.get_document.return_value = Document.model_validate(doc_data_1)

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=grading_model_repo,
            farmer_performance_repo=farmer_perf_repo,
            farmer_repo=farmer_repo,
            factory_repo=factory_repo,
            region_repo=region_repo,
            cp_repo=cp_repo,
        )

        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await processor.process(
                document_id="doc-int-002",
                farmer_id="FRM-INT-001",
            )

        # Verify farmer is in CP-1
        cp1 = await cp_repo.get_by_id("CP-INT-001")
        assert "FRM-INT-001" in cp1.farmer_ids

        # Now process quality event at CP-2 (different factory)
        doc_data_2 = create_sample_document(
            document_id="doc-int-003",
            farmer_id="FRM-INT-001",
            factory_id="FAC-INT-002",  # Different factory
            collection_point_id="CP-INT-002",  # Different CP
        )
        mock_collection_client.get_document.return_value = Document.model_validate(doc_data_2)

        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor.process(
                document_id="doc-int-003",
                farmer_id="FRM-INT-001",
            )

        # Assert: Processing succeeded
        assert result["status"] == "success"

        # Assert: Farmer is now in BOTH CPs
        cp1_after = await cp_repo.get_by_id("CP-INT-001")
        cp2_after = await cp_repo.get_by_id("CP-INT-002")

        assert "FRM-INT-001" in cp1_after.farmer_ids, "Farmer should remain in CP-1"
        assert "FRM-INT-001" in cp2_after.farmer_ids, "Farmer should also be in CP-2"

        # Verify via list_by_farmer
        cps, _, count = await cp_repo.list_by_farmer("FRM-INT-001", page_size=100)
        assert count == 2, "Farmer should be assigned to exactly 2 CPs"
        cp_ids = [cp.id for cp in cps]
        assert "CP-INT-001" in cp_ids
        assert "CP-INT-002" in cp_ids
