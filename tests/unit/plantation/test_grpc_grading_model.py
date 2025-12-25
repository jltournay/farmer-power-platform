"""Unit tests for GradingModel gRPC service methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from fp_proto.plantation.v1 import plantation_pb2
from plantation_model.api.plantation_service import PlantationServiceServicer
from plantation_model.domain.models.factory import Factory
from plantation_model.domain.models.grading_model import (
    ConditionalReject,
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
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
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)


class TestGradingModelGrpcService:
    """Tests for GradingModel gRPC service methods."""

    @pytest.fixture
    def mock_factory_repo(self) -> MagicMock:
        """Create a mock factory repository."""
        return MagicMock(spec=FactoryRepository)

    @pytest.fixture
    def mock_cp_repo(self) -> MagicMock:
        """Create a mock collection point repository."""
        return MagicMock(spec=CollectionPointRepository)

    @pytest.fixture
    def mock_farmer_repo(self) -> MagicMock:
        """Create a mock farmer repository."""
        return MagicMock(spec=FarmerRepository)

    @pytest.fixture
    def mock_grading_model_repo(self) -> MagicMock:
        """Create a mock grading model repository."""
        return MagicMock(spec=GradingModelRepository)

    @pytest.fixture
    def mock_id_generator(self) -> MagicMock:
        """Create a mock ID generator."""
        return MagicMock(spec=IDGenerator)

    @pytest.fixture
    def mock_elevation_client(self) -> MagicMock:
        """Create a mock elevation client."""
        return MagicMock(spec=GoogleElevationClient)

    @pytest.fixture
    def mock_dapr_client(self) -> MagicMock:
        """Create a mock Dapr pub/sub client."""
        return MagicMock(spec=DaprPubSubClient)

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock(spec=grpc.aio.ServicerContext)
        context.abort = AsyncMock(side_effect=grpc.RpcError())
        return context

    @pytest.fixture
    def servicer(
        self,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
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
            grading_model_repo=mock_grading_model_repo,
        )

    @pytest.fixture
    def sample_grading_model(self) -> GradingModel:
        """Create a sample grading model for testing."""
        return GradingModel(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            regulatory_authority="Tea Board of Kenya (TBK)",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=GradingType.BINARY,
            attributes={
                "leaf_type": GradingAttribute(
                    num_classes=7,
                    classes=[
                        "bud",
                        "one_leaf_bud",
                        "two_leaves_bud",
                        "three_plus_leaves_bud",
                        "single_soft_leaf",
                        "coarse_leaf",
                        "banji",
                    ],
                ),
                "banji_hardness": GradingAttribute(
                    num_classes=2,
                    classes=["soft", "hard"],
                ),
            },
            grade_rules=GradeRules(
                reject_conditions={
                    "leaf_type": ["three_plus_leaves_bud", "coarse_leaf"],
                },
                conditional_reject=[
                    ConditionalReject(
                        if_attribute="leaf_type",
                        if_value="banji",
                        then_attribute="banji_hardness",
                        reject_values=["hard"],
                    ),
                ],
            ),
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
            active_at_factory=["KEN-FAC-001"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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

    # =========================================================================
    # CreateGradingModel Tests (Task 8.5)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_grading_model_success(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateGradingModel creates model successfully."""
        mock_grading_model_repo.get_by_id = AsyncMock(return_value=None)
        mock_grading_model_repo.create = AsyncMock()

        request = plantation_pb2.CreateGradingModelRequest(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            regulatory_authority="Tea Board of Kenya",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=plantation_pb2.GRADING_TYPE_BINARY,
            attributes={
                "leaf_type": plantation_pb2.GradingAttribute(
                    num_classes=3,
                    classes=["bud", "one_leaf_bud", "coarse_leaf"],
                ),
            },
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
            active_at_factory=["KEN-FAC-001"],
        )

        result = await servicer.CreateGradingModel(request, mock_context)

        assert result.model_id == "tbk_kenya_tea_v1"
        assert result.model_version == "1.0.0"
        assert result.crops_name == "Tea"
        assert result.grading_type == plantation_pb2.GRADING_TYPE_BINARY
        mock_grading_model_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_grading_model_duplicate(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test CreateGradingModel rejects duplicate model_id."""
        mock_grading_model_repo.get_by_id = AsyncMock(return_value=sample_grading_model)

        request = plantation_pb2.CreateGradingModelRequest(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=plantation_pb2.GRADING_TYPE_BINARY,
            attributes={},
            grade_labels={},
        )

        with pytest.raises(grpc.RpcError):
            await servicer.CreateGradingModel(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_create_grading_model_with_grade_rules(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test CreateGradingModel with reject conditions and conditional rules."""
        mock_grading_model_repo.get_by_id = AsyncMock(return_value=None)
        mock_grading_model_repo.create = AsyncMock()

        request = plantation_pb2.CreateGradingModelRequest(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=plantation_pb2.GRADING_TYPE_BINARY,
            attributes={
                "leaf_type": plantation_pb2.GradingAttribute(
                    num_classes=2,
                    classes=["good", "bad"],
                ),
            },
            grade_rules=plantation_pb2.GradeRules(
                reject_conditions={
                    "leaf_type": plantation_pb2.StringList(values=["bad"]),
                },
                conditional_reject=[
                    plantation_pb2.ConditionalReject(
                        if_attribute="leaf_type",
                        if_value="test",
                        then_attribute="hardness",
                        reject_values=["hard"],
                    ),
                ],
            ),
            grade_labels={"ACCEPT": "Good", "REJECT": "Bad"},
        )

        result = await servicer.CreateGradingModel(request, mock_context)

        assert result.model_id == "test_model"
        mock_grading_model_repo.create.assert_called_once()

    # =========================================================================
    # GetGradingModel Tests (Task 8.5)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_grading_model_found(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test GetGradingModel returns model when found."""
        mock_grading_model_repo.get_by_id = AsyncMock(return_value=sample_grading_model)

        request = plantation_pb2.GetGradingModelRequest(model_id="tbk_kenya_tea_v1")
        result = await servicer.GetGradingModel(request, mock_context)

        assert result.model_id == "tbk_kenya_tea_v1"
        assert result.model_version == "1.0.0"
        assert result.crops_name == "Tea"
        mock_grading_model_repo.get_by_id.assert_called_once_with("tbk_kenya_tea_v1")

    @pytest.mark.asyncio
    async def test_get_grading_model_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test GetGradingModel aborts with NOT_FOUND when model doesn't exist."""
        mock_grading_model_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.GetGradingModelRequest(model_id="nonexistent")

        with pytest.raises(grpc.RpcError):
            await servicer.GetGradingModel(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    # =========================================================================
    # GetFactoryGradingModel Tests (Task 8.6)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_factory_grading_model_found(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test GetFactoryGradingModel returns model assigned to factory."""
        mock_grading_model_repo.get_by_factory = AsyncMock(
            return_value=sample_grading_model
        )

        request = plantation_pb2.GetFactoryGradingModelRequest(factory_id="KEN-FAC-001")
        result = await servicer.GetFactoryGradingModel(request, mock_context)

        assert result.model_id == "tbk_kenya_tea_v1"
        assert "KEN-FAC-001" in result.active_at_factory
        mock_grading_model_repo.get_by_factory.assert_called_once_with("KEN-FAC-001")

    @pytest.mark.asyncio
    async def test_get_factory_grading_model_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test GetFactoryGradingModel aborts when factory has no model assigned."""
        mock_grading_model_repo.get_by_factory = AsyncMock(return_value=None)

        request = plantation_pb2.GetFactoryGradingModelRequest(factory_id="KEN-FAC-999")

        with pytest.raises(grpc.RpcError):
            await servicer.GetFactoryGradingModel(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    # =========================================================================
    # AssignGradingModelToFactory Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_assign_grading_model_to_factory_success(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test AssignGradingModelToFactory assigns model successfully."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=sample_factory)
        mock_grading_model_repo.add_factory_assignment = AsyncMock(
            return_value=sample_grading_model
        )

        request = plantation_pb2.AssignGradingModelToFactoryRequest(
            model_id="tbk_kenya_tea_v1",
            factory_id="KEN-FAC-001",
        )
        result = await servicer.AssignGradingModelToFactory(request, mock_context)

        assert result.model_id == "tbk_kenya_tea_v1"
        mock_grading_model_repo.add_factory_assignment.assert_called_once_with(
            "tbk_kenya_tea_v1", "KEN-FAC-001"
        )

    @pytest.mark.asyncio
    async def test_assign_grading_model_factory_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test AssignGradingModelToFactory aborts when factory doesn't exist."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.AssignGradingModelToFactoryRequest(
            model_id="tbk_kenya_tea_v1",
            factory_id="KEN-FAC-999",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.AssignGradingModelToFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_assign_grading_model_model_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_factory_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
        sample_factory: Factory,
    ) -> None:
        """Test AssignGradingModelToFactory aborts when model doesn't exist."""
        mock_factory_repo.get_by_id = AsyncMock(return_value=sample_factory)
        mock_grading_model_repo.add_factory_assignment = AsyncMock(return_value=None)

        request = plantation_pb2.AssignGradingModelToFactoryRequest(
            model_id="nonexistent_model",
            factory_id="KEN-FAC-001",
        )

        with pytest.raises(grpc.RpcError):
            await servicer.AssignGradingModelToFactory(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND
