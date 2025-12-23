"""Unit tests for CollectionPoint gRPC service methods."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

from plantation_model.api.plantation_service import PlantationServiceServicer
from plantation_model.domain.models.collection_point import CollectionPoint
from plantation_model.domain.models.factory import Factory
from plantation_model.domain.models.value_objects import (
    CollectionPointCapacity,
    ContactInfo,
    GeoLocation,
    OperatingHours,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.google_elevation import GoogleElevationClient
from fp_proto.plantation.v1 import plantation_pb2


class TestCollectionPointGrpcService:
    """Tests for CollectionPoint gRPC service methods."""

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
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
    ) -> PlantationServiceServicer:
        """Create a servicer with mock dependencies."""
        return PlantationServiceServicer(
            factory_repo=mock_factory_repo,
            collection_point_repo=mock_cp_repo,
            id_generator=mock_id_generator,
            elevation_client=mock_elevation_client,
        )

    @pytest.fixture
    def sample_factory(self) -> Factory:
        """Create a sample factory for testing."""
        return Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test-region",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
            contact=ContactInfo(),
        )

    @pytest.fixture
    def sample_cp(self) -> CollectionPoint:
        """Create a sample collection point for testing."""
        return CollectionPoint(
            id="test-region-cp-001",
            name="Test Collection Point",
            factory_id="KEN-FAC-001",
            location=GeoLocation(
                latitude=-0.45,
                longitude=36.55,
                altitude_meters=1600.0,
            ),
            region_id="test-region",
            clerk_id="CLK-001",
            clerk_phone="+254700111222",
            operating_hours=OperatingHours(
                weekdays="06:00-10:00",
                weekends="07:00-09:00",
            ),
            collection_days=["mon", "wed", "fri"],
            capacity=CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="covered_shed",
                has_weighing_scale=True,
                has_qc_device=False,
            ),
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_get_collection_point_found(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test GetCollectionPoint returns CP when found."""
        mock_cp_repo.get_by_id = AsyncMock(return_value=sample_cp)

        request = plantation_pb2.GetCollectionPointRequest(id="test-region-cp-001")
        result = await servicer.GetCollectionPoint(request, mock_context)

        assert result.id == "test-region-cp-001"
        assert result.name == "Test Collection Point"
        assert result.factory_id == "KEN-FAC-001"
        mock_cp_repo.get_by_id.assert_called_once_with("test-region-cp-001")

    @pytest.mark.asyncio
    async def test_get_collection_point_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test GetCollectionPoint aborts with NOT_FOUND when CP doesn't exist."""
        mock_cp_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.GetCollectionPointRequest(id="nonexistent-cp-001")

        with pytest.raises(grpc.RpcError):
            await servicer.GetCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_collection_point_success(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test CreateCollectionPoint creates CP with generated ID."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=sample_factory)
        mock_cp_repo.create = AsyncMock()
        mock_id_generator.generate_collection_point_id = AsyncMock(
            return_value="test-region-cp-001"
        )
        mock_elevation_client.get_altitude = AsyncMock(return_value=1600.0)

        request = plantation_pb2.CreateCollectionPointRequest(
            name="New Collection Point",
            factory_id="KEN-FAC-001",
            location=plantation_pb2.GeoLocation(latitude=-0.45, longitude=36.55),
            region_id="test-region",
            clerk_id="CLK-001",
            clerk_phone="+254700111222",
            operating_hours=plantation_pb2.OperatingHours(
                weekdays="06:00-10:00",
                weekends="07:00-09:00",
            ),
            collection_days=["mon", "wed", "fri"],
            capacity=plantation_pb2.CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="covered_shed",
                has_weighing_scale=True,
            ),
        )
        result = await servicer.CreateCollectionPoint(request, mock_context)

        assert result.id == "test-region-cp-001"
        assert result.name == "New Collection Point"
        assert result.location.altitude_meters == 1600.0
        mock_cp_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_collection_point_factory_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateCollectionPoint aborts when factory doesn't exist."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.CreateCollectionPointRequest(
            name="New Collection Point",
            factory_id="KEN-FAC-999",
            location=plantation_pb2.GeoLocation(latitude=-0.45, longitude=36.55),
            region_id="test-region",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.CreateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_collection_point_success(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test UpdateCollectionPoint updates CP fields."""
        updated_cp = CollectionPoint(
            id=sample_cp.id,
            name=sample_cp.name,
            factory_id=sample_cp.factory_id,
            location=sample_cp.location,
            region_id=sample_cp.region_id,
            clerk_id="CLK-002",
            clerk_phone="+254700222333",
            operating_hours=sample_cp.operating_hours,
            collection_days=sample_cp.collection_days,
            capacity=sample_cp.capacity,
            status="inactive",
            created_at=sample_cp.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        mock_cp_repo.update = AsyncMock(return_value=updated_cp)

        request = plantation_pb2.UpdateCollectionPointRequest(
            id="test-region-cp-001",
            clerk_id="CLK-002",
            clerk_phone="+254700222333",
            status="inactive",
        )
        result = await servicer.UpdateCollectionPoint(request, mock_context)

        assert result.clerk_id == "CLK-002"
        assert result.status == "inactive"

    @pytest.mark.asyncio
    async def test_update_collection_point_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test UpdateCollectionPoint aborts with NOT_FOUND when CP doesn't exist."""
        mock_cp_repo.update = AsyncMock(return_value=None)

        request = plantation_pb2.UpdateCollectionPointRequest(
            id="nonexistent-cp-001",
            clerk_id="CLK-002",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_collection_points_success(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test ListCollectionPoints returns list of CPs."""
        mock_cp_repo.list = AsyncMock(return_value=([sample_cp], None, 1))

        request = plantation_pb2.ListCollectionPointsRequest(page_size=10)
        result = await servicer.ListCollectionPoints(request, mock_context)

        assert len(result.collection_points) == 1
        assert result.collection_points[0].id == "test-region-cp-001"
        assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_list_collection_points_with_factory_filter(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test ListCollectionPoints filters by factory_id."""
        mock_cp_repo.list = AsyncMock(return_value=([sample_cp], None, 1))

        request = plantation_pb2.ListCollectionPointsRequest(
            factory_id="KEN-FAC-001",
        )
        await servicer.ListCollectionPoints(request, mock_context)

        call_args = mock_cp_repo.list.call_args
        filters = call_args[1]["filters"]
        assert filters["factory_id"] == "KEN-FAC-001"

    @pytest.mark.asyncio
    async def test_list_collection_points_with_status_filter(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test ListCollectionPoints filters by status."""
        mock_cp_repo.list = AsyncMock(return_value=([sample_cp], None, 1))

        request = plantation_pb2.ListCollectionPointsRequest(
            active_only=True,
        )
        await servicer.ListCollectionPoints(request, mock_context)

        call_args = mock_cp_repo.list.call_args
        filters = call_args[1]["filters"]
        assert filters["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_collection_point_with_defaults(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test CreateCollectionPoint uses defaults for optional fields."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=sample_factory)
        mock_cp_repo.create = AsyncMock()
        mock_id_generator.generate_collection_point_id = AsyncMock(
            return_value="test-region-cp-001"
        )
        mock_elevation_client.get_altitude = AsyncMock(return_value=None)

        request = plantation_pb2.CreateCollectionPointRequest(
            name="Minimal Collection Point",
            factory_id="KEN-FAC-001",
            location=plantation_pb2.GeoLocation(latitude=-0.45, longitude=36.55),
            region_id="test-region",
        )
        result = await servicer.CreateCollectionPoint(request, mock_context)

        # Check defaults are applied
        assert result.status == "active"
        assert result.location.altitude_meters == 0.0  # Fallback when elevation API fails
        # Default collection days
        assert len(result.collection_days) == 4
        assert "mon" in result.collection_days

    @pytest.mark.asyncio
    async def test_update_operating_hours(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test UpdateCollectionPoint updates operating hours."""
        updated_cp = CollectionPoint(
            id=sample_cp.id,
            name=sample_cp.name,
            factory_id=sample_cp.factory_id,
            location=sample_cp.location,
            region_id=sample_cp.region_id,
            clerk_id=sample_cp.clerk_id,
            clerk_phone=sample_cp.clerk_phone,
            operating_hours=OperatingHours(
                weekdays="05:00-11:00",
                weekends="06:00-10:00",
            ),
            collection_days=sample_cp.collection_days,
            capacity=sample_cp.capacity,
            status=sample_cp.status,
            created_at=sample_cp.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        mock_cp_repo.update = AsyncMock(return_value=updated_cp)

        request = plantation_pb2.UpdateCollectionPointRequest(
            id="test-region-cp-001",
            operating_hours=plantation_pb2.OperatingHours(
                weekdays="05:00-11:00",
                weekends="06:00-10:00",
            ),
        )
        result = await servicer.UpdateCollectionPoint(request, mock_context)

        assert result.operating_hours.weekdays == "05:00-11:00"
        assert result.operating_hours.weekends == "06:00-10:00"

    @pytest.mark.asyncio
    async def test_delete_collection_point_success(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test DeleteCollectionPoint deletes CP successfully."""
        mock_cp_repo.delete = AsyncMock(return_value=True)

        request = plantation_pb2.DeleteCollectionPointRequest(id="test-region-cp-001")
        result = await servicer.DeleteCollectionPoint(request, mock_context)

        assert result.success is True
        mock_cp_repo.delete.assert_called_once_with("test-region-cp-001")

    @pytest.mark.asyncio
    async def test_delete_collection_point_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test DeleteCollectionPoint aborts with NOT_FOUND when CP doesn't exist."""
        mock_cp_repo.delete = AsyncMock(return_value=False)

        request = plantation_pb2.DeleteCollectionPointRequest(id="nonexistent-cp-001")

        with pytest.raises(grpc.RpcError):
            await servicer.DeleteCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    # =========================================================================
    # Input Validation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_collection_point_invalid_status(
        self,
        servicer: PlantationServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateCollectionPoint rejects invalid status."""
        request = plantation_pb2.CreateCollectionPointRequest(
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=plantation_pb2.GeoLocation(latitude=-0.45, longitude=36.55),
            region_id="test-region",
            status="invalid_status",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.CreateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid status" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_collection_point_invalid_storage_type(
        self,
        servicer: PlantationServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateCollectionPoint rejects invalid storage_type."""
        request = plantation_pb2.CreateCollectionPointRequest(
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=plantation_pb2.GeoLocation(latitude=-0.45, longitude=36.55),
            region_id="test-region",
            capacity=plantation_pb2.CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="invalid_storage",
            ),
        )

        with pytest.raises(grpc.RpcError):
            await servicer.CreateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid storage_type" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_collection_point_invalid_collection_days(
        self,
        servicer: PlantationServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateCollectionPoint rejects invalid collection_days."""
        request = plantation_pb2.CreateCollectionPointRequest(
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=plantation_pb2.GeoLocation(latitude=-0.45, longitude=36.55),
            region_id="test-region",
            collection_days=["mon", "invalid_day", "fri"],
        )

        with pytest.raises(grpc.RpcError):
            await servicer.CreateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid collection_days" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_update_collection_point_invalid_status(
        self,
        servicer: PlantationServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Test UpdateCollectionPoint rejects invalid status."""
        request = plantation_pb2.UpdateCollectionPointRequest(
            id="test-region-cp-001",
            status="invalid_status",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid status" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_update_collection_point_invalid_storage_type(
        self,
        servicer: PlantationServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Test UpdateCollectionPoint rejects invalid storage_type."""
        request = plantation_pb2.UpdateCollectionPointRequest(
            id="test-region-cp-001",
            capacity=plantation_pb2.CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="invalid_storage",
            ),
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid storage_type" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_update_collection_point_invalid_collection_days(
        self,
        servicer: PlantationServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Test UpdateCollectionPoint rejects invalid collection_days."""
        request = plantation_pb2.UpdateCollectionPointRequest(
            id="test-region-cp-001",
            collection_days=["tue", "badday"],
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCollectionPoint(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid collection_days" in call_args[0][1]
