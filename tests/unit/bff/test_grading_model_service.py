"""Tests for AdminGradingModelService (Story 9.6a).

Tests service orchestration, factory name resolution, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bff.api.schemas import PaginationMeta
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.admin.grading_model_service import AdminGradingModelService
from bff.transformers.admin.grading_model_transformer import GradingModelTransformer
from fp_common.models import Factory, GeoLocation
from fp_common.models.grading_model import (
    ConditionalReject,
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)


@pytest.fixture
def mock_plantation_client() -> MagicMock:
    """Create a mock PlantationClient."""
    client = MagicMock(spec=PlantationClient)
    client.list_grading_models = AsyncMock()
    client.get_grading_model = AsyncMock()
    client.assign_grading_model_to_factory = AsyncMock()
    client.get_factory = AsyncMock()
    return client


@pytest.fixture
def grading_model_service(mock_plantation_client: MagicMock) -> AdminGradingModelService:
    """Create AdminGradingModelService with mock client."""
    return AdminGradingModelService(
        plantation_client=mock_plantation_client,
        transformer=GradingModelTransformer(),
    )


@pytest.fixture
def sample_grading_model() -> GradingModel:
    """Create a sample GradingModel domain model."""
    return GradingModel(
        model_id="tbk_kenya_tea_v1",
        model_version="2024.1",
        regulatory_authority="KTDA",
        crops_name="Tea",
        market_name="Kenya_TBK",
        grading_type=GradingType.BINARY,
        attributes={
            "leaf_appearance": GradingAttribute(num_classes=3, classes=["Fine", "Medium", "Coarse"]),
            "insect_damage": GradingAttribute(num_classes=2, classes=["None", "Present"]),
        },
        grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        grade_rules=GradeRules(
            reject_conditions={"insect_damage": ["Present"]},
            conditional_reject=[
                ConditionalReject(
                    if_attribute="leaf_appearance",
                    if_value="Coarse",
                    then_attribute="insect_damage",
                    reject_values=["Light"],
                )
            ],
        ),
        active_at_factory=["KEN-FAC-001", "KEN-FAC-002"],
    )


@pytest.fixture
def sample_factory_1() -> Factory:
    """Create a sample Factory domain model."""
    return Factory(
        id="KEN-FAC-001",
        name="Nyeri Tea Factory",
        code="NTF",
        region_id="nyeri-highland",
        location=GeoLocation(latitude=-0.4232, longitude=36.9587, altitude_meters=1950.0),
        is_active=True,
    )


@pytest.fixture
def sample_factory_2() -> Factory:
    """Create second sample Factory domain model."""
    return Factory(
        id="KEN-FAC-002",
        name="Kiambu Tea Factory",
        code="KTF",
        region_id="kiambu-region",
        location=GeoLocation(latitude=-1.1714, longitude=36.8370, altitude_meters=1800.0),
        is_active=True,
    )


class TestListGradingModels:
    """Tests for list_grading_models method."""

    @pytest.mark.asyncio
    async def test_list_grading_models_success(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
        sample_grading_model: GradingModel,
    ):
        """Test successful listing of grading models."""
        # Setup mock response
        response = MagicMock()
        response.data = [sample_grading_model]
        response.pagination = PaginationMeta(
            page=1,
            page_size=50,
            total_count=1,
            has_next=False,
            has_prev=False,
        )
        mock_plantation_client.list_grading_models.return_value = response

        # Execute
        result = await grading_model_service.list_grading_models(page_size=50)

        # Verify
        assert len(result.data) == 1
        assert result.data[0].model_id == "tbk_kenya_tea_v1"
        assert result.data[0].market_name == "Kenya_TBK"
        assert result.data[0].crops_name == "Tea"
        assert result.data[0].grading_type == "binary"
        assert result.data[0].factory_count == 2
        assert result.pagination.total_count == 1

    @pytest.mark.asyncio
    async def test_list_grading_models_with_filters(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
        sample_grading_model: GradingModel,
    ):
        """Test listing grading models with filters."""
        response = MagicMock()
        response.data = [sample_grading_model]
        response.pagination = PaginationMeta(page=1, page_size=50, total_count=1)
        mock_plantation_client.list_grading_models.return_value = response

        # Execute with filters
        await grading_model_service.list_grading_models(
            market_name="Kenya_TBK",
            crops_name="Tea",
            grading_type="binary",
            page_size=25,
            page_token="cursor-xyz",
        )

        # Verify filters passed to client
        mock_plantation_client.list_grading_models.assert_called_once_with(
            market_name="Kenya_TBK",
            crops_name="Tea",
            grading_type="binary",
            page_size=25,
            page_token="cursor-xyz",
        )

    @pytest.mark.asyncio
    async def test_list_grading_models_empty(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test listing when no grading models exist."""
        response = MagicMock()
        response.data = []
        response.pagination = PaginationMeta(page=1, page_size=50, total_count=0)
        mock_plantation_client.list_grading_models.return_value = response

        result = await grading_model_service.list_grading_models()

        assert len(result.data) == 0
        assert result.pagination.total_count == 0

    @pytest.mark.asyncio
    async def test_list_grading_models_service_unavailable(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test service unavailable error propagation."""
        mock_plantation_client.list_grading_models.side_effect = ServiceUnavailableError("Plantation Model unavailable")

        with pytest.raises(ServiceUnavailableError, match="Plantation Model unavailable"):
            await grading_model_service.list_grading_models()


class TestGetGradingModel:
    """Tests for get_grading_model method."""

    @pytest.mark.asyncio
    async def test_get_grading_model_success(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
        sample_grading_model: GradingModel,
        sample_factory_1: Factory,
        sample_factory_2: Factory,
    ):
        """Test successful retrieval of grading model detail."""
        mock_plantation_client.get_grading_model.return_value = sample_grading_model
        mock_plantation_client.get_factory.side_effect = [sample_factory_1, sample_factory_2]

        result = await grading_model_service.get_grading_model("tbk_kenya_tea_v1")

        # Verify basic fields
        assert result.model_id == "tbk_kenya_tea_v1"
        assert result.model_version == "2024.1"
        assert result.regulatory_authority == "KTDA"
        assert result.crops_name == "Tea"
        assert result.market_name == "Kenya_TBK"
        assert result.grading_type == "binary"

        # Verify attributes
        assert len(result.attributes) == 2
        assert result.attributes["leaf_appearance"].num_classes == 3

        # Verify grade rules
        assert result.grade_rules.reject_conditions == {"insect_damage": ["Present"]}
        assert len(result.grade_rules.conditional_reject) == 1

        # Verify factory references with resolved names
        assert len(result.active_at_factories) == 2
        factory_names = {f.name for f in result.active_at_factories}
        assert "Nyeri Tea Factory" in factory_names
        assert "Kiambu Tea Factory" in factory_names

    @pytest.mark.asyncio
    async def test_get_grading_model_not_found(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test grading model not found error."""
        mock_plantation_client.get_grading_model.side_effect = NotFoundError("Grading model not_exists not found")

        with pytest.raises(NotFoundError, match="Grading model not_exists not found"):
            await grading_model_service.get_grading_model("not_exists")

    @pytest.mark.asyncio
    async def test_get_grading_model_no_factories(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test grading model with no factory assignments."""
        model = GradingModel(
            model_id="new_model",
            model_version="1.0",
            crops_name="Coffee",
            market_name="Ethiopia",
            grading_type=GradingType.TERNARY,
            attributes={"quality": GradingAttribute(num_classes=3, classes=["A", "B", "C"])},
            grade_labels={"A": "Grade A", "B": "Grade B", "C": "Grade C"},
            active_at_factory=[],  # No factories assigned
        )
        mock_plantation_client.get_grading_model.return_value = model

        result = await grading_model_service.get_grading_model("new_model")

        assert result.model_id == "new_model"
        assert len(result.active_at_factories) == 0

    @pytest.mark.asyncio
    async def test_get_grading_model_factory_resolution_partial_failure(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
        sample_grading_model: GradingModel,
        sample_factory_1: Factory,
    ):
        """Test factory name resolution when some factories fail to resolve."""
        mock_plantation_client.get_grading_model.return_value = sample_grading_model
        # First factory succeeds, second fails
        mock_plantation_client.get_factory.side_effect = [
            sample_factory_1,
            NotFoundError("Factory KEN-FAC-002 not found"),
        ]

        result = await grading_model_service.get_grading_model("tbk_kenya_tea_v1")

        # Both factories should be in the list, but only the first has a resolved name
        assert len(result.active_at_factories) == 2
        # Find the factory with the resolved name
        factory_1 = next(f for f in result.active_at_factories if f.factory_id == "KEN-FAC-001")
        factory_2 = next(f for f in result.active_at_factories if f.factory_id == "KEN-FAC-002")
        assert factory_1.name == "Nyeri Tea Factory"
        assert factory_2.name is None  # Failed to resolve


class TestAssignToFactory:
    """Tests for assign_to_factory method."""

    @pytest.mark.asyncio
    async def test_assign_to_factory_success(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
        sample_grading_model: GradingModel,
        sample_factory_1: Factory,
        sample_factory_2: Factory,
    ):
        """Test successful assignment of grading model to factory."""
        # After assignment, model has both factories
        mock_plantation_client.assign_grading_model_to_factory.return_value = sample_grading_model
        mock_plantation_client.get_factory.side_effect = [sample_factory_1, sample_factory_2]

        result = await grading_model_service.assign_to_factory(
            model_id="tbk_kenya_tea_v1",
            factory_id="KEN-FAC-002",
        )

        # Verify client was called correctly
        mock_plantation_client.assign_grading_model_to_factory.assert_called_once_with(
            model_id="tbk_kenya_tea_v1",
            factory_id="KEN-FAC-002",
        )

        # Verify returned detail
        assert result.model_id == "tbk_kenya_tea_v1"
        assert len(result.active_at_factories) == 2

    @pytest.mark.asyncio
    async def test_assign_to_factory_model_not_found(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test assignment when grading model not found."""
        mock_plantation_client.assign_grading_model_to_factory.side_effect = NotFoundError(
            "Grading model not_exists not found"
        )

        with pytest.raises(NotFoundError, match="Grading model not_exists not found"):
            await grading_model_service.assign_to_factory(
                model_id="not_exists",
                factory_id="KEN-FAC-001",
            )

    @pytest.mark.asyncio
    async def test_assign_to_factory_factory_not_found(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test assignment when factory not found."""
        mock_plantation_client.assign_grading_model_to_factory.side_effect = NotFoundError(
            "Factory invalid_factory not found"
        )

        with pytest.raises(NotFoundError, match="Factory invalid_factory not found"):
            await grading_model_service.assign_to_factory(
                model_id="tbk_kenya_tea_v1",
                factory_id="invalid_factory",
            )

    @pytest.mark.asyncio
    async def test_assign_to_factory_service_unavailable(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test assignment when service unavailable."""
        mock_plantation_client.assign_grading_model_to_factory.side_effect = ServiceUnavailableError(
            "Plantation Model unavailable"
        )

        with pytest.raises(ServiceUnavailableError, match="Plantation Model unavailable"):
            await grading_model_service.assign_to_factory(
                model_id="tbk_kenya_tea_v1",
                factory_id="KEN-FAC-001",
            )


class TestResolveFactoryNames:
    """Tests for _resolve_factory_names internal method."""

    @pytest.mark.asyncio
    async def test_resolve_empty_list(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
    ):
        """Test resolving an empty factory list."""
        result = await grading_model_service._resolve_factory_names([])

        assert result == {}
        mock_plantation_client.get_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_multiple_factories_parallel(
        self,
        grading_model_service: AdminGradingModelService,
        mock_plantation_client: MagicMock,
        sample_factory_1: Factory,
        sample_factory_2: Factory,
    ):
        """Test resolving multiple factories in parallel."""
        mock_plantation_client.get_factory.side_effect = [sample_factory_1, sample_factory_2]

        result = await grading_model_service._resolve_factory_names(["KEN-FAC-001", "KEN-FAC-002"])

        assert result == {
            "KEN-FAC-001": "Nyeri Tea Factory",
            "KEN-FAC-002": "Kiambu Tea Factory",
        }
        assert mock_plantation_client.get_factory.call_count == 2
