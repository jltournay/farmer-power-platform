"""Unit tests for Factory gRPC service methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from fp_proto.plantation.v1 import plantation_pb2
from plantation_model.api.plantation_service import PlantationServiceServicer
from plantation_model.domain.models import (
    ContactInfo,
    Factory,
    GeoLocation,
    PaymentPolicy,
    PaymentPolicyType,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.dapr_client import DaprPubSubClient
from plantation_model.infrastructure.google_elevation import GoogleElevationClient
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)


class TestFactoryGrpcService:
    """Tests for Factory gRPC service methods."""

    @pytest.fixture
    def mock_factory_repo(self) -> MagicMock:
        """Create a mock factory repository."""
        return MagicMock(spec=FactoryRepository)

    @pytest.fixture
    def mock_cp_repo(self) -> MagicMock:
        """Create a mock collection point repository."""
        return MagicMock(spec=CollectionPointRepository)

    @pytest.fixture
    def mock_id_generator(self) -> MagicMock:
        """Create a mock ID generator."""
        return MagicMock(spec=IDGenerator)

    @pytest.fixture
    def mock_elevation_client(self) -> MagicMock:
        """Create a mock elevation client."""
        return MagicMock(spec=GoogleElevationClient)

    @pytest.fixture
    def mock_farmer_repo(self) -> MagicMock:
        """Create a mock farmer repository."""
        return MagicMock(spec=FarmerRepository)

    @pytest.fixture
    def mock_dapr_client(self) -> MagicMock:
        """Create a mock Dapr pub/sub client."""
        return MagicMock(spec=DaprPubSubClient)

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock(spec=grpc.aio.ServicerContext)
        # Make abort raise an exception to stop execution (like real gRPC behavior)
        context.abort = AsyncMock(side_effect=grpc.RpcError())
        return context

    @pytest.fixture
    def servicer(
        self,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_dapr_client: MagicMock,
    ) -> PlantationServiceServicer:
        """Create a servicer with mock dependencies."""
        return PlantationServiceServicer(
            factory_repo=mock_factory_repo,
            collection_point_repo=mock_cp_repo,
            farmer_repo=mock_farmer_repo,
            id_generator=mock_id_generator,
            elevation_client=mock_elevation_client,
            dapr_client=mock_dapr_client,
        )

    @pytest.fixture
    def sample_factory(self) -> Factory:
        """Create a sample factory for testing."""
        return Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test-region",
            location=GeoLocation(
                latitude=-0.5,
                longitude=36.5,
                altitude_meters=1500.0,
            ),
            contact=ContactInfo(
                phone="+254700000000",
                email="test@factory.co.ke",
                address="Test Address",
            ),
            processing_capacity_kg=50000,
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType.SPLIT_PAYMENT,
                tier_1_adjustment=0.15,
                tier_2_adjustment=0.0,
                tier_3_adjustment=-0.05,
                below_tier_3_adjustment=-0.10,
            ),
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_get_factory_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test GetFactory returns factory when found."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=sample_factory)

        request = plantation_pb2.GetFactoryRequest(id="KEN-FAC-001")
        result = await servicer.GetFactory(request, mock_context)

        assert result.id == "KEN-FAC-001"
        assert result.name == "Test Factory"
        assert result.code == "TF"
        mock_factory_repo.get_by_id.assert_called_once_with("KEN-FAC-001")

    @pytest.mark.asyncio
    async def test_get_factory_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test GetFactory aborts with NOT_FOUND when factory doesn't exist."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.GetFactoryRequest(id="KEN-FAC-999")

        with pytest.raises(grpc.RpcError):
            await servicer.GetFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_factory_success(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateFactory creates factory with generated ID."""
        mock_factory_repo.get_by_code = AsyncMock(return_value=None)
        mock_factory_repo.create = AsyncMock()
        mock_id_generator.generate_factory_id = AsyncMock(return_value="KEN-FAC-001")
        mock_elevation_client.get_altitude = AsyncMock(return_value=1500.0)

        request = plantation_pb2.CreateFactoryRequest(
            name="New Factory",
            code="NF",
            region_id="test-region",
            location=plantation_pb2.GeoLocation(latitude=-0.5, longitude=36.5),
            contact=plantation_pb2.ContactInfo(
                phone="+254700000000",
                email="new@factory.co.ke",
            ),
            processing_capacity_kg=30000,
        )
        result = await servicer.CreateFactory(request, mock_context)

        assert result.id == "KEN-FAC-001"
        assert result.name == "New Factory"
        assert result.location.altitude_meters == 1500.0
        mock_factory_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_factory_duplicate_code(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test CreateFactory aborts with ALREADY_EXISTS for duplicate code."""
        mock_factory_repo.get_by_code = AsyncMock(return_value=sample_factory)

        request = plantation_pb2.CreateFactoryRequest(
            name="Another Factory",
            code="TF",  # Same code as sample_factory
            region_id="test-region",
            location=plantation_pb2.GeoLocation(latitude=-0.5, longitude=36.5),
        )

        with pytest.raises(grpc.RpcError):
            await servicer.CreateFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_update_factory_success(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test UpdateFactory updates factory fields."""
        updated_factory = Factory(
            id=sample_factory.id,
            name="Updated Factory",
            code=sample_factory.code,
            region_id=sample_factory.region_id,
            location=sample_factory.location,
            contact=sample_factory.contact,
            processing_capacity_kg=75000,
            is_active=True,
            created_at=sample_factory.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_factory_repo.update = AsyncMock(return_value=updated_factory)
        mock_factory_repo.get_by_code = AsyncMock(return_value=None)

        request = plantation_pb2.UpdateFactoryRequest(
            id="KEN-FAC-001",
            name="Updated Factory",
            processing_capacity_kg=75000,
        )
        result = await servicer.UpdateFactory(request, mock_context)

        assert result.name == "Updated Factory"
        assert result.processing_capacity_kg == 75000

    @pytest.mark.asyncio
    async def test_update_factory_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test UpdateFactory aborts with NOT_FOUND when factory doesn't exist."""
        mock_factory_repo.update = AsyncMock(return_value=None)
        mock_factory_repo.get_by_code = AsyncMock(return_value=None)

        request = plantation_pb2.UpdateFactoryRequest(
            id="KEN-FAC-999",
            name="Updated Name",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_factories_success(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test ListFactories returns list of factories."""
        mock_factory_repo.list = AsyncMock(return_value=([sample_factory], None, 1))

        request = plantation_pb2.ListFactoriesRequest(page_size=10)
        result = await servicer.ListFactories(request, mock_context)

        assert len(result.factories) == 1
        assert result.factories[0].id == "KEN-FAC-001"
        assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_list_factories_with_region_filter(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test ListFactories filters by region."""
        mock_factory_repo.list = AsyncMock(return_value=([sample_factory], None, 1))

        request = plantation_pb2.ListFactoriesRequest(
            region_id="test-region",
            active_only=True,
        )
        await servicer.ListFactories(request, mock_context)

        call_args = mock_factory_repo.list.call_args
        filters = call_args[1]["filters"]
        assert filters["region_id"] == "test-region"
        assert filters["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_factory_elevation_fallback(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateFactory uses 0.0 altitude when elevation API fails."""
        mock_factory_repo.get_by_code = AsyncMock(return_value=None)
        mock_factory_repo.create = AsyncMock()
        mock_id_generator.generate_factory_id = AsyncMock(return_value="KEN-FAC-001")
        mock_elevation_client.get_altitude = AsyncMock(return_value=None)

        request = plantation_pb2.CreateFactoryRequest(
            name="New Factory",
            code="NF",
            region_id="test-region",
            location=plantation_pb2.GeoLocation(latitude=-0.5, longitude=36.5),
        )
        result = await servicer.CreateFactory(request, mock_context)

        assert result.location.altitude_meters == 0.0

    @pytest.mark.asyncio
    async def test_delete_factory_success(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test DeleteFactory deletes factory successfully."""
        mock_cp_repo.list = AsyncMock(return_value=([], None, 0))  # No collection points
        mock_factory_repo.delete = AsyncMock(return_value=True)

        request = plantation_pb2.DeleteFactoryRequest(id="KEN-FAC-001")
        result = await servicer.DeleteFactory(request, mock_context)

        assert result.success is True
        mock_factory_repo.delete.assert_called_once_with("KEN-FAC-001")

    @pytest.mark.asyncio
    async def test_delete_factory_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test DeleteFactory aborts with NOT_FOUND when factory doesn't exist."""
        mock_cp_repo.list = AsyncMock(return_value=([], None, 0))
        mock_factory_repo.delete = AsyncMock(return_value=False)

        request = plantation_pb2.DeleteFactoryRequest(id="KEN-FAC-999")

        with pytest.raises(grpc.RpcError):
            await servicer.DeleteFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_factory_with_collection_points(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test DeleteFactory aborts with FAILED_PRECONDITION when factory has collection points."""
        # Factory has 2 collection points
        mock_cp_repo.list = AsyncMock(return_value=([], None, 2))

        request = plantation_pb2.DeleteFactoryRequest(id="KEN-FAC-001")

        with pytest.raises(grpc.RpcError):
            await servicer.DeleteFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.FAILED_PRECONDITION
        assert "collection point(s) still exist" in call_args[0][1]

    # =========================================================================
    # Payment Policy Tests (Story 1.9)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_factory_returns_payment_policy(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test GetFactory returns factory with payment_policy."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=sample_factory)

        request = plantation_pb2.GetFactoryRequest(id="KEN-FAC-001")
        result = await servicer.GetFactory(request, mock_context)

        assert result.payment_policy.policy_type == plantation_pb2.PAYMENT_POLICY_TYPE_SPLIT_PAYMENT
        assert result.payment_policy.tier_1_adjustment == 0.15
        assert result.payment_policy.tier_2_adjustment == 0.0
        assert result.payment_policy.tier_3_adjustment == -0.05
        assert result.payment_policy.below_tier_3_adjustment == -0.10

    @pytest.mark.asyncio
    async def test_create_factory_with_payment_policy(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateFactory with payment_policy in request."""
        mock_factory_repo.get_by_code = AsyncMock(return_value=None)
        mock_factory_repo.create = AsyncMock()
        mock_id_generator.generate_factory_id = AsyncMock(return_value="KEN-FAC-002")
        mock_elevation_client.get_altitude = AsyncMock(return_value=1600.0)

        request = plantation_pb2.CreateFactoryRequest(
            name="Factory With Policy",
            code="FWP",
            region_id="test-region",
            location=plantation_pb2.GeoLocation(latitude=-0.6, longitude=36.6),
            payment_policy=plantation_pb2.PaymentPolicy(
                policy_type=plantation_pb2.PAYMENT_POLICY_TYPE_WEEKLY_BONUS,
                tier_1_adjustment=0.20,
                tier_2_adjustment=0.05,
                tier_3_adjustment=0.0,
                below_tier_3_adjustment=-0.15,
            ),
        )
        result = await servicer.CreateFactory(request, mock_context)

        assert result.id == "KEN-FAC-002"
        assert result.payment_policy.policy_type == plantation_pb2.PAYMENT_POLICY_TYPE_WEEKLY_BONUS
        assert result.payment_policy.tier_1_adjustment == 0.20
        assert result.payment_policy.below_tier_3_adjustment == -0.15

        # Verify factory was created with correct payment_policy
        create_call = mock_factory_repo.create.call_args[0][0]
        assert create_call.payment_policy.policy_type == PaymentPolicyType.WEEKLY_BONUS
        assert create_call.payment_policy.tier_1_adjustment == 0.20

    @pytest.mark.asyncio
    async def test_create_factory_default_payment_policy(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateFactory uses default payment_policy when not provided."""
        mock_factory_repo.get_by_code = AsyncMock(return_value=None)
        mock_factory_repo.create = AsyncMock()
        mock_id_generator.generate_factory_id = AsyncMock(return_value="KEN-FAC-003")
        mock_elevation_client.get_altitude = AsyncMock(return_value=1500.0)

        request = plantation_pb2.CreateFactoryRequest(
            name="Factory No Policy",
            code="FNP",
            region_id="test-region",
            location=plantation_pb2.GeoLocation(latitude=-0.5, longitude=36.5),
            # No payment_policy provided
        )
        result = await servicer.CreateFactory(request, mock_context)

        # Should use default FEEDBACK_ONLY with all adjustments = 0.0
        assert result.payment_policy.policy_type == plantation_pb2.PAYMENT_POLICY_TYPE_FEEDBACK_ONLY
        assert result.payment_policy.tier_1_adjustment == 0.0
        assert result.payment_policy.tier_2_adjustment == 0.0
        assert result.payment_policy.tier_3_adjustment == 0.0
        assert result.payment_policy.below_tier_3_adjustment == 0.0

    @pytest.mark.asyncio
    async def test_update_factory_payment_policy(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test UpdateFactory can update payment_policy."""
        # Return updated factory with new payment policy
        updated_factory = Factory(
            id=sample_factory.id,
            name=sample_factory.name,
            code=sample_factory.code,
            region_id=sample_factory.region_id,
            location=sample_factory.location,
            contact=sample_factory.contact,
            processing_capacity_kg=sample_factory.processing_capacity_kg,
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType.DELAYED_PAYMENT,
                tier_1_adjustment=0.25,
                tier_2_adjustment=0.10,
                tier_3_adjustment=-0.10,
                below_tier_3_adjustment=-0.20,
            ),
            is_active=sample_factory.is_active,
            created_at=sample_factory.created_at,
            updated_at=sample_factory.updated_at,
        )
        mock_factory_repo.update = AsyncMock(return_value=updated_factory)

        request = plantation_pb2.UpdateFactoryRequest(
            id="KEN-FAC-001",
            payment_policy=plantation_pb2.PaymentPolicy(
                policy_type=plantation_pb2.PAYMENT_POLICY_TYPE_DELAYED_PAYMENT,
                tier_1_adjustment=0.25,
                tier_2_adjustment=0.10,
                tier_3_adjustment=-0.10,
                below_tier_3_adjustment=-0.20,
            ),
        )
        result = await servicer.UpdateFactory(request, mock_context)

        assert result.payment_policy.policy_type == plantation_pb2.PAYMENT_POLICY_TYPE_DELAYED_PAYMENT
        assert result.payment_policy.tier_1_adjustment == 0.25
        assert result.payment_policy.below_tier_3_adjustment == -0.20

        # Verify update was called with payment_policy
        update_call = mock_factory_repo.update.call_args
        assert "payment_policy" in update_call[0][1]
