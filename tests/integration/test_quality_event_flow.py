"""Integration tests for Quality Event Flow (Story 1.7).

These tests validate the complete quality event processing pipeline:
1. CloudEvent arrives from Collection Model via DAPR Pub/Sub
2. Handler parses and delegates to QualityEventProcessor
3. Processor fetches document, loads grading model, updates performance
4. Domain events are emitted

This test uses mock Collection client and DAPR to avoid external dependencies.

Usage:
    PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src" \
        pytest tests/integration/test_quality_event_flow.py -v
"""

import datetime as dt
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from plantation_model.domain.models import (
    FarmerPerformance,
    FarmScale,
    GradeRules,
    GradingModel,
    GradingType,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)


def create_cloud_event_payload(
    document_id: str = "doc-123",
    plantation_id: str = "WM-0001",
    batch_timestamp: str | None = None,
) -> dict:
    """Create a CloudEvent payload for testing."""
    return {
        "id": "evt-12345",
        "source": "collection-model",
        "type": "collection.quality_result.received",
        "specversion": "1.0",
        "datacontenttype": "application/json",
        "time": datetime.now(UTC).isoformat(),
        "data": {
            "payload": {
                "document_id": document_id,
                "plantation_id": plantation_id,
                "batch_timestamp": batch_timestamp or datetime.now(UTC).isoformat(),
            }
        },
    }


def create_sample_document(
    document_id: str = "doc-123",
    farmer_id: str = "WM-0001",
    grading_model_id: str = "tbk_kenya_tea_v1",
) -> dict:
    """Create a sample quality document from Collection Model."""
    return {
        "document_id": document_id,
        "source_id": "qc-analyzer-result",
        "farmer_id": farmer_id,
        "attributes": {
            "grading_model_id": grading_model_id,
            "grading_model_version": "1.0.0",
            "factory_id": "factory-001",
            "bag_summary": {
                "total_weight_kg": 25.0,
                "primary_percentage": 80.0,
                "secondary_percentage": 20.0,
                "overall_grade": "A",
                "leaf_type_distribution": {
                    "bud": 5,
                    "two_leaves_bud": 15,
                    "coarse_leaf": 3,
                },
            },
        },
    }


def create_sample_grading_model() -> GradingModel:
    """Create a sample grading model for testing."""
    return GradingModel(
        model_id="tbk_kenya_tea_v1",
        model_version="1.0.0",
        regulatory_authority="Tea Board of Kenya",
        crops_name="Tea",
        market_name="Kenya_TBK",
        grading_type=GradingType.BINARY,
        attributes={},
        grade_rules=GradeRules(),
        grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        active_at_factory=["factory-001"],
    )


def create_sample_farmer_performance(farmer_id: str = "WM-0001") -> FarmerPerformance:
    """Create a sample farmer performance for testing."""
    return FarmerPerformance(
        farmer_id=farmer_id,
        grading_model_id="tbk_kenya_tea_v1",
        grading_model_version="1.0.0",
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        historical=HistoricalMetrics(
            primary_percentage_30d=75.0,
            primary_percentage_90d=70.0,
            improvement_trend=TrendDirection.IMPROVING,
        ),
        today=TodayMetrics(
            deliveries=2,
            total_kg=45.0,
            grade_counts={"Primary": 2},
            metrics_date=dt.date.today(),
        ),
    )


@pytest.mark.integration
class TestQualityEventFlow:
    """Integration tests for the quality event processing flow (Story 1.7)."""

    @pytest.fixture
    def mock_collection_client(self) -> AsyncMock:
        """Create mock collection client."""
        client = AsyncMock()
        client.get_document = AsyncMock(return_value=create_sample_document())
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def mock_grading_model_repo(self) -> AsyncMock:
        """Create mock grading model repository."""
        repo = AsyncMock()
        repo.get_by_id_and_version = AsyncMock(return_value=create_sample_grading_model())
        repo.get_by_id = AsyncMock(return_value=create_sample_grading_model())
        return repo

    @pytest.fixture
    def mock_farmer_performance_repo(self) -> AsyncMock:
        """Create mock farmer performance repository."""
        repo = AsyncMock()
        repo.get_by_farmer_id = AsyncMock(return_value=create_sample_farmer_performance())
        repo.increment_today_delivery = AsyncMock(return_value=create_sample_farmer_performance())
        repo.reset_today = AsyncMock(return_value=create_sample_farmer_performance())
        return repo

    @pytest.fixture
    def mock_event_publisher(self) -> AsyncMock:
        """Create mock DAPR event publisher."""
        publisher = AsyncMock()
        publisher.publish_event = AsyncMock(return_value=True)
        return publisher

    @pytest.fixture
    def client(
        self,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_event_publisher: AsyncMock,
    ) -> TestClient:
        """Create test client with mocked dependencies."""
        # Build the QualityEventProcessor with mocks
        from plantation_model.domain.services.quality_event_processor import QualityEventProcessor

        quality_processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            event_publisher=mock_event_publisher,
        )

        mock_mongodb_client = MagicMock()
        mock_mongodb_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_mongodb_client.close = MagicMock()

        with (
            patch(
                "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
                return_value=mock_mongodb_client,
            ),
            patch(
                "plantation_model.infrastructure.mongodb.get_database",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "plantation_model.infrastructure.tracing.setup_tracing",
                return_value=None,
            ),
            patch(
                "plantation_model.infrastructure.tracing.instrument_fastapi",
                return_value=None,
            ),
            patch(
                "plantation_model.infrastructure.tracing.shutdown_tracing",
                return_value=None,
            ),
            patch(
                "plantation_model.api.grpc_server.start_grpc_server",
                new_callable=AsyncMock,
            ),
            patch(
                "plantation_model.api.grpc_server.stop_grpc_server",
                new_callable=AsyncMock,
            ),
            patch(
                "plantation_model.main.CollectionClient",
                return_value=mock_collection_client,
            ),
            patch(
                "plantation_model.main.GradingModelRepository",
                return_value=mock_grading_model_repo,
            ),
            patch(
                "plantation_model.main.FarmerPerformanceRepository",
                return_value=mock_farmer_performance_repo,
            ),
            patch(
                "plantation_model.main.DaprPubSubClient",
                return_value=mock_event_publisher,
            ),
            patch(
                "plantation_model.main.QualityEventProcessor",
                return_value=quality_processor,
            ),
        ):
            from plantation_model.main import app

            with TestClient(app) as test_client:
                yield test_client

    def test_dapr_subscriptions_endpoint(self, client: TestClient) -> None:
        """Test DAPR subscription discovery endpoint.

        Task 8.1: Verify DAPR can discover our subscription.
        """
        response = client.get("/api/v1/events/subscriptions")

        assert response.status_code == 200
        subscriptions = response.json()
        assert len(subscriptions) >= 1

        # Verify our quality result subscription
        quality_sub = next(
            (s for s in subscriptions if s["topic"] == "collection.quality_result.received"),
            None,
        )
        assert quality_sub is not None
        assert quality_sub["pubsubname"] == "pubsub"
        assert quality_sub["route"] == "/api/v1/events/quality-result"

    def test_quality_result_event_processing_success(
        self,
        client: TestClient,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_event_publisher: AsyncMock,
    ) -> None:
        """Test successful quality result event processing.

        Task 8.1-8.4: Full event flow from CloudEvent to MongoDB update and event emission.
        """
        # Send CloudEvent to handler
        cloud_event = create_cloud_event_payload()
        response = client.post(
            "/api/v1/events/quality-result",
            json=cloud_event,
        )

        # Verify handler response
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"

        # Task 8.2: Verify Collection client was called
        mock_collection_client.get_document.assert_called_once_with("doc-123")

        # Task 8.3: Verify MongoDB updates (via repository calls)
        mock_farmer_performance_repo.get_by_farmer_id.assert_called()
        mock_farmer_performance_repo.increment_today_delivery.assert_called()

        # Task 8.4: Verify domain events were published
        assert mock_event_publisher.publish_event.call_count == 2

        # Check plantation.quality.graded event
        calls = mock_event_publisher.publish_event.call_args_list
        quality_graded_call = next(
            (c for c in calls if c.kwargs.get("topic") == "plantation.quality.graded"),
            None,
        )
        assert quality_graded_call is not None

        # Check plantation.performance_updated event
        perf_updated_call = next(
            (c for c in calls if c.kwargs.get("topic") == "plantation.performance_updated"),
            None,
        )
        assert perf_updated_call is not None

        # Verify NO current_category in performance event (Engagement Model owns this)
        perf_payload = perf_updated_call.kwargs.get("data", {})
        assert "current_category" not in perf_payload

    def test_quality_result_invalid_cloud_event_format(self, client: TestClient) -> None:
        """Test handling of invalid CloudEvent format.

        Should return DROP status to avoid retries.
        """
        response = client.post(
            "/api/v1/events/quality-result",
            json={"invalid": "data"},  # Missing required CloudEvent fields
        )

        assert response.status_code == 400
        assert response.json()["status"] == "DROP"

    def test_quality_result_missing_payload(self, client: TestClient) -> None:
        """Test handling of CloudEvent with missing payload data."""
        cloud_event = {
            "id": "evt-123",
            "source": "test",
            "type": "collection.quality_result.received",
            "specversion": "1.0",
            "datacontenttype": "application/json",
            "data": {},  # Missing payload
        }

        response = client.post(
            "/api/v1/events/quality-result",
            json=cloud_event,
        )

        # Should drop invalid events
        assert response.status_code == 400

    def test_quality_result_document_not_found(
        self,
        client: TestClient,
        mock_collection_client: AsyncMock,
    ) -> None:
        """Test handling when document not found in Collection Model.

        Should return RETRY for transient failures.
        """
        from plantation_model.infrastructure.collection_client import DocumentNotFoundError

        mock_collection_client.get_document.side_effect = DocumentNotFoundError("doc-missing")

        cloud_event = create_cloud_event_payload(document_id="doc-missing")
        response = client.post(
            "/api/v1/events/quality-result",
            json=cloud_event,
        )

        assert response.status_code == 500
        assert response.json()["status"] == "RETRY"

    def test_quality_result_grading_model_not_found(
        self,
        client: TestClient,
        mock_grading_model_repo: AsyncMock,
    ) -> None:
        """Test handling when grading model not found."""
        mock_grading_model_repo.get_by_id_and_version.return_value = None

        cloud_event = create_cloud_event_payload()
        response = client.post(
            "/api/v1/events/quality-result",
            json=cloud_event,
        )

        assert response.status_code == 500
        assert response.json()["status"] == "RETRY"

    def test_quality_result_farmer_not_found_skips_update(
        self,
        client: TestClient,
        mock_farmer_performance_repo: AsyncMock,
        mock_event_publisher: AsyncMock,
    ) -> None:
        """Test processing continues but skips update when farmer not found."""
        mock_farmer_performance_repo.get_by_farmer_id.return_value = None

        cloud_event = create_cloud_event_payload()
        response = client.post(
            "/api/v1/events/quality-result",
            json=cloud_event,
        )

        # Should succeed but skip updates
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"

        # Events should NOT be published when farmer not found
        mock_event_publisher.publish_event.assert_not_called()


@pytest.mark.integration
class TestQualityEventFlowEdgeCases:
    """Edge case tests for quality event flow."""

    @pytest.fixture
    def mock_dependencies(self) -> dict:
        """Create all mock dependencies."""
        collection_client = AsyncMock()
        collection_client.get_document = AsyncMock(return_value=create_sample_document())
        collection_client.close = AsyncMock()

        grading_repo = AsyncMock()
        grading_repo.get_by_id_and_version = AsyncMock(return_value=create_sample_grading_model())

        perf_repo = AsyncMock()
        perf_repo.get_by_farmer_id = AsyncMock(return_value=create_sample_farmer_performance())
        perf_repo.increment_today_delivery = AsyncMock(return_value=create_sample_farmer_performance())
        perf_repo.reset_today = AsyncMock(return_value=create_sample_farmer_performance())

        event_pub = AsyncMock()
        event_pub.publish_event = AsyncMock(return_value=True)

        return {
            "collection_client": collection_client,
            "grading_repo": grading_repo,
            "perf_repo": perf_repo,
            "event_publisher": event_pub,
        }

    def test_date_rollover_resets_today_metrics(self, mock_dependencies: dict) -> None:
        """Test that date rollover triggers today metrics reset.

        When processing an event on a new day, today's metrics should reset first.
        """
        from plantation_model.domain.services.quality_event_processor import QualityEventProcessor

        # Create performance from yesterday
        yesterday_perf = create_sample_farmer_performance()
        yesterday_perf.today.metrics_date = dt.date.today() - dt.timedelta(days=1)

        mock_dependencies["perf_repo"].get_by_farmer_id.return_value = yesterday_perf

        processor = QualityEventProcessor(
            collection_client=mock_dependencies["collection_client"],
            grading_model_repo=mock_dependencies["grading_repo"],
            farmer_performance_repo=mock_dependencies["perf_repo"],
            event_publisher=mock_dependencies["event_publisher"],
        )

        # Run async test
        import asyncio

        async def run_test():
            await processor.process(
                document_id="doc-123",
                farmer_id="WM-0001",
                batch_timestamp=datetime.now(UTC),
            )

        asyncio.get_event_loop().run_until_complete(run_test())

        # Verify reset_today was called due to date rollover
        mock_dependencies["perf_repo"].reset_today.assert_called_once_with("WM-0001")

    def test_versioned_grading_model_lookup(self, mock_dependencies: dict) -> None:
        """Test that processor uses versioned grading model lookup.

        Task 2: Should use get_by_id_and_version for exact version match.
        """
        from plantation_model.domain.services.quality_event_processor import QualityEventProcessor

        processor = QualityEventProcessor(
            collection_client=mock_dependencies["collection_client"],
            grading_model_repo=mock_dependencies["grading_repo"],
            farmer_performance_repo=mock_dependencies["perf_repo"],
            event_publisher=mock_dependencies["event_publisher"],
        )

        import asyncio

        async def run_test():
            await processor.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        asyncio.get_event_loop().run_until_complete(run_test())

        # Verify versioned lookup was used
        mock_dependencies["grading_repo"].get_by_id_and_version.assert_called_once_with("tbk_kenya_tea_v1", "1.0.0")
