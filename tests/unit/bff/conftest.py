"""BFF unit test fixtures.

Uses fixtures from root conftest.py. Do NOT override parent fixtures.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from fp_proto.collection.v1 import collection_pb2
from fp_proto.plantation.v1 import plantation_pb2
from google.protobuf.timestamp_pb2 import Timestamp
from jose import jwt

# =============================================================================
# JWT Mock Token Helpers (Story 0.5.3)
# =============================================================================

MOCK_JWT_SECRET = "test-secret-for-unit-tests"

MOCK_USERS = {
    "factory_manager": {
        "sub": "mock-manager-001",
        "email": "jane@kericho-factory.test",
        "name": "Jane Mwangi",
        "role": "factory_manager",
        "factory_id": "KEN-FAC-001",
        "factory_ids": ["KEN-FAC-001"],
        "collection_point_id": None,
        "region_ids": [],
        "permissions": ["farmers:read", "quality_events:read", "diagnoses:read", "action_plans:read"],
    },
    "factory_owner": {
        "sub": "mock-owner-001",
        "email": "john@owner.test",
        "name": "John Ochieng",
        "role": "factory_owner",
        "factory_id": "KEN-FAC-001",
        "factory_ids": ["KEN-FAC-001", "KEN-FAC-002"],
        "collection_point_id": None,
        "region_ids": [],
        "permissions": ["farmers:read", "quality_events:read", "payment_policies:write", "factory_settings:write"],
    },
    "platform_admin": {
        "sub": "mock-admin-001",
        "email": "admin@farmerpower.test",
        "name": "Admin User",
        "role": "platform_admin",
        "factory_id": None,
        "factory_ids": [],
        "collection_point_id": None,
        "region_ids": [],
        "permissions": ["*"],
    },
    "regulator": {
        "sub": "mock-regulator-001",
        "email": "inspector@tbk.go.ke.test",
        "name": "TBK Inspector",
        "role": "regulator",
        "factory_id": None,
        "factory_ids": [],
        "collection_point_id": None,
        "region_ids": ["nandi", "kericho"],
        "permissions": ["national_stats:read", "regional_stats:read"],
    },
    "registration_clerk": {
        "sub": "mock-clerk-001",
        "email": "mary@cp.test",
        "name": "Mary Wanjiku",
        "role": "registration_clerk",
        "factory_id": "KEN-FAC-001",
        "factory_ids": ["KEN-FAC-001"],
        "collection_point_id": "KEN-CP-001",
        "region_ids": [],
        "permissions": ["farmers:create"],
    },
}


def create_mock_jwt_token(
    user_data: dict,
    secret: str = MOCK_JWT_SECRET,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a mock JWT token for testing.

    Args:
        user_data: User claims to include in the token.
        secret: JWT secret for HS256 signing.
        expires_delta: Token expiration time delta. Default is 1 hour.

    Returns:
        Signed JWT token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    now = datetime.now(UTC)
    payload = {
        **user_data,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def mock_manager_token() -> str:
    """JWT token for factory_manager user."""
    return create_mock_jwt_token(MOCK_USERS["factory_manager"])


@pytest.fixture
def mock_owner_token() -> str:
    """JWT token for factory_owner user."""
    return create_mock_jwt_token(MOCK_USERS["factory_owner"])


@pytest.fixture
def mock_admin_token() -> str:
    """JWT token for platform_admin user."""
    return create_mock_jwt_token(MOCK_USERS["platform_admin"])


@pytest.fixture
def mock_regulator_token() -> str:
    """JWT token for regulator user."""
    return create_mock_jwt_token(MOCK_USERS["regulator"])


@pytest.fixture
def mock_clerk_token() -> str:
    """JWT token for registration_clerk user."""
    return create_mock_jwt_token(MOCK_USERS["registration_clerk"])


@pytest.fixture
def expired_token() -> str:
    """Expired JWT token for testing expiry handling."""
    return create_mock_jwt_token(
        MOCK_USERS["factory_manager"],
        expires_delta=timedelta(hours=-1),  # Already expired
    )


@pytest.fixture
def invalid_token() -> str:
    """Invalid JWT token (wrong secret)."""
    return create_mock_jwt_token(
        MOCK_USERS["factory_manager"],
        secret="wrong-secret",
    )


def auth_headers(token: str) -> dict[str, str]:
    """Create Authorization headers for a token.

    Args:
        token: JWT token string.

    Returns:
        Headers dict with Authorization Bearer token.
    """
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bff_client(monkeypatch) -> TestClient:
    """Create a test client for the BFF application.

    This fixture is shared across all BFF test files.
    Configures the mock JWT secret for authentication.

    Returns:
        TestClient instance for the BFF FastAPI application.
    """
    # Set the environment variable for mock JWT secret
    monkeypatch.setenv("MOCK_JWT_SECRET", MOCK_JWT_SECRET)

    # Clear cached settings so new env var is picked up
    from bff.config import get_settings

    get_settings.cache_clear()

    from bff.main import create_app

    app = create_app()
    return TestClient(app)


def create_mock_channel() -> MagicMock:
    """Create a mock gRPC channel."""
    channel = MagicMock()
    channel.close = AsyncMock()
    return channel


def create_farmer_proto(
    farmer_id: str = "WM-0001",
    first_name: str = "Wanjiku",
    last_name: str = "Kamau",
    phone: str = "+254712345678",
    region_id: str = "nyeri-highland",
    collection_point_id: str = "nyeri-highland-cp-001",
    farm_size_hectares: float = 1.5,
    national_id: str = "12345678",
    is_active: bool = True,
) -> plantation_pb2.Farmer:
    """Create a Farmer proto message for testing."""
    farmer = plantation_pb2.Farmer(
        id=farmer_id,
        first_name=first_name,
        last_name=last_name,
        region_id=region_id,
        collection_point_id=collection_point_id,
        farm_location=plantation_pb2.GeoLocation(
            latitude=-0.4197,
            longitude=36.9553,
            altitude_meters=1950.0,
        ),
        contact=plantation_pb2.ContactInfo(
            phone=phone,
            email="",
            address="",
        ),
        farm_size_hectares=farm_size_hectares,
        farm_scale=plantation_pb2.FarmScale.FARM_SCALE_MEDIUM,
        national_id=national_id,
        is_active=is_active,
        notification_channel=plantation_pb2.NotificationChannel.NOTIFICATION_CHANNEL_SMS,
        interaction_pref=plantation_pb2.InteractionPreference.INTERACTION_PREFERENCE_TEXT,
        pref_lang=plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_SW,
    )
    return farmer


def create_factory_proto(
    factory_id: str = "KEN-FAC-001",
    name: str = "Nyeri Tea Factory",
    code: str = "NTF",
    region_id: str = "nyeri-highland",
    processing_capacity_kg: int = 50000,
    is_active: bool = True,
) -> plantation_pb2.Factory:
    """Create a Factory proto message for testing."""
    factory = plantation_pb2.Factory(
        id=factory_id,
        name=name,
        code=code,
        region_id=region_id,
        location=plantation_pb2.GeoLocation(
            latitude=-0.4232,
            longitude=36.9587,
            altitude_meters=1950.0,
        ),
        contact=plantation_pb2.ContactInfo(
            phone="+254712345678",
            email="factory@ntf.co.ke",
            address="P.O. Box 123, Nyeri",
        ),
        processing_capacity_kg=processing_capacity_kg,
        quality_thresholds=plantation_pb2.QualityThresholds(
            tier_1=85.0,
            tier_2=70.0,
            tier_3=50.0,
        ),
        payment_policy=plantation_pb2.PaymentPolicy(
            policy_type=plantation_pb2.PaymentPolicyType.PAYMENT_POLICY_TYPE_FEEDBACK_ONLY,
        ),
        is_active=is_active,
    )
    return factory


def create_collection_point_proto(
    cp_id: str = "nyeri-highland-cp-001",
    name: str = "Kamakwa Collection Point",
    factory_id: str = "KEN-FAC-001",
    region_id: str = "nyeri-highland",
    status: str = "active",
) -> plantation_pb2.CollectionPoint:
    """Create a CollectionPoint proto message for testing."""
    cp = plantation_pb2.CollectionPoint(
        id=cp_id,
        name=name,
        factory_id=factory_id,
        location=plantation_pb2.GeoLocation(
            latitude=-0.4150,
            longitude=36.9500,
            altitude_meters=1850.0,
        ),
        region_id=region_id,
        clerk_id="CLK-001",
        clerk_phone="+254712345679",
        operating_hours=plantation_pb2.OperatingHours(
            weekdays="06:00-10:00",
            weekends="07:00-09:00",
        ),
        collection_days=["mon", "wed", "fri", "sat"],
        capacity=plantation_pb2.CollectionPointCapacity(
            max_daily_kg=5000,
            storage_type="covered_shed",
            has_weighing_scale=True,
            has_qc_device=False,
        ),
        status=status,
    )
    return cp


def create_region_proto(
    region_id: str = "nyeri-highland",
    name: str = "Nyeri Highland",
    county: str = "Nyeri",
    country: str = "Kenya",
    is_active: bool = True,
) -> plantation_pb2.Region:
    """Create a Region proto message for testing."""
    region = plantation_pb2.Region(
        region_id=region_id,
        name=name,
        county=county,
        country=country,
        geography=plantation_pb2.Geography(
            center_gps=plantation_pb2.GPS(lat=-0.4197, lng=36.9553),
            radius_km=25,
            altitude_band=plantation_pb2.AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=plantation_pb2.AltitudeBandLabel.ALTITUDE_BAND_HIGHLAND,
            ),
        ),
        flush_calendar=plantation_pb2.FlushCalendar(
            first_flush=plantation_pb2.FlushPeriod(
                start="03-15",
                end="05-15",
                characteristics="Highest quality, delicate flavor",
            ),
            monsoon_flush=plantation_pb2.FlushPeriod(
                start="06-15",
                end="09-30",
                characteristics="High volume, robust flavor",
            ),
            autumn_flush=plantation_pb2.FlushPeriod(
                start="10-15",
                end="12-15",
                characteristics="Balanced quality",
            ),
            dormant=plantation_pb2.FlushPeriod(
                start="12-16",
                end="03-14",
                characteristics="Minimal growth",
            ),
        ),
        agronomic=plantation_pb2.Agronomic(
            soil_type="volcanic_red",
            typical_diseases=["blister_blight", "grey_blight"],
            harvest_peak_hours="06:00-10:00",
            frost_risk=True,
        ),
        weather_config=plantation_pb2.WeatherConfig(
            api_location=plantation_pb2.GPS(lat=-0.4197, lng=36.9553),
            altitude_for_api=1950,
            collection_time="06:00",
        ),
        is_active=is_active,
    )
    return region


def create_regional_weather_proto(
    region_id: str = "nyeri-highland",
    date: str = "2025-12-28",
    temp_min: float = 12.5,
    temp_max: float = 24.8,
    precipitation_mm: float = 2.3,
    humidity_avg: float = 78.5,
) -> plantation_pb2.RegionalWeather:
    """Create a RegionalWeather proto message for testing."""
    return plantation_pb2.RegionalWeather(
        region_id=region_id,
        date=date,
        temp_min=temp_min,
        temp_max=temp_max,
        precipitation_mm=precipitation_mm,
        humidity_avg=humidity_avg,
        source="open-meteo",
    )


def create_current_flush_response(
    region_id: str = "nyeri-highland",
    flush_name: str = "first_flush",
    start_date: str = "03-15",
    end_date: str = "05-15",
    characteristics: str = "Highest quality, delicate flavor",
    days_remaining: int = 45,
) -> plantation_pb2.GetCurrentFlushResponse:
    """Create a GetCurrentFlushResponse proto message for testing."""
    return plantation_pb2.GetCurrentFlushResponse(
        region_id=region_id,
        current_flush=plantation_pb2.CurrentFlush(
            flush_name=flush_name,
            start_date=start_date,
            end_date=end_date,
            characteristics=characteristics,
            days_remaining=days_remaining,
        ),
    )


def create_farmer_summary_proto(
    farmer_id: str = "WM-0001",
    first_name: str = "Wanjiku",
    last_name: str = "Kamau",
    farm_size_hectares: float = 1.5,
) -> plantation_pb2.FarmerSummary:
    """Create a FarmerSummary proto message for testing."""
    summary = plantation_pb2.FarmerSummary(
        farmer_id=farmer_id,
        first_name=first_name,
        last_name=last_name,
        phone="+254712345678",
        collection_point_id="nyeri-highland-cp-001",
        farm_size_hectares=farm_size_hectares,
        farm_scale=plantation_pb2.FarmScale.FARM_SCALE_MEDIUM,
        grading_model_id="tbk_kenya_tea_v1",
        grading_model_version="1.0.0",
        trend_direction=plantation_pb2.TrendDirection.TREND_DIRECTION_IMPROVING,
        notification_channel=plantation_pb2.NotificationChannel.NOTIFICATION_CHANNEL_SMS,
        interaction_pref=plantation_pb2.InteractionPreference.INTERACTION_PREFERENCE_TEXT,
        pref_lang=plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_SW,
    )
    # Add historical metrics
    summary.historical.primary_percentage_30d = 80.0
    summary.historical.primary_percentage_90d = 75.0
    summary.historical.primary_percentage_year = 78.0
    summary.historical.total_kg_30d = 450.0
    summary.historical.total_kg_90d = 1200.0
    summary.historical.total_kg_year = 5000.0
    summary.historical.improvement_trend = plantation_pb2.TrendDirection.TREND_DIRECTION_IMPROVING

    # Add today metrics
    summary.today.deliveries = 2
    summary.today.total_kg = 45.0
    summary.today.metrics_date = "2025-12-28"
    summary.today.grade_counts["Primary"] = 2

    return summary


@pytest.fixture
def mock_grpc_channel() -> MagicMock:
    """Create a mock gRPC channel."""
    return create_mock_channel()


@pytest.fixture
def sample_farmer_proto() -> plantation_pb2.Farmer:
    """Sample Farmer proto for testing."""
    return create_farmer_proto()


@pytest.fixture
def sample_factory_proto() -> plantation_pb2.Factory:
    """Sample Factory proto for testing."""
    return create_factory_proto()


@pytest.fixture
def sample_collection_point_proto() -> plantation_pb2.CollectionPoint:
    """Sample CollectionPoint proto for testing."""
    return create_collection_point_proto()


@pytest.fixture
def sample_region_proto() -> plantation_pb2.Region:
    """Sample Region proto for testing."""
    return create_region_proto()


# =============================================================================
# Collection Model Proto Helpers
# =============================================================================


def _datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to proto Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def create_document_proto(
    document_id: str = "doc-12345",
    blob_container: str = "quality-data",
    blob_path: str = "factory-001/2025-12-28/batch-001.json",
    content_hash: str = "sha256:abc123def456",
    size_bytes: int = 1024,
    ai_agent_id: str = "qc-extractor-v1",
    confidence: float = 0.95,
    validation_passed: bool = True,
    ingestion_id: str = "ing-001",
    source_id: str = "qc-analyzer-result",
    farmer_id: str = "WM-0001",
) -> collection_pb2.Document:
    """Create a Document proto message for testing.

    Args:
        document_id: Unique document identifier.
        blob_container: Azure Blob Storage container name.
        blob_path: Path to the blob within container.
        content_hash: SHA-256 hash of the content.
        size_bytes: Size of the content in bytes.
        ai_agent_id: AI Model agent ID used for extraction.
        confidence: Confidence score of the extraction.
        validation_passed: Whether extraction passed validation.
        ingestion_id: ID of the ingestion job.
        source_id: ID of the source configuration.
        farmer_id: Farmer ID for linkage fields.

    Returns:
        A Document proto message.
    """
    now = datetime.now(UTC)

    doc = collection_pb2.Document(
        document_id=document_id,
        raw_document=collection_pb2.RawDocumentRef(
            blob_container=blob_container,
            blob_path=blob_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            stored_at=_datetime_to_timestamp(now),
        ),
        extraction=collection_pb2.ExtractionMetadata(
            ai_agent_id=ai_agent_id,
            extraction_timestamp=_datetime_to_timestamp(now),
            confidence=confidence,
            validation_passed=validation_passed,
            validation_warnings=[],
        ),
        ingestion=collection_pb2.IngestionMetadata(
            ingestion_id=ingestion_id,
            source_id=source_id,
            received_at=_datetime_to_timestamp(now),
            processed_at=_datetime_to_timestamp(now),
        ),
        created_at=_datetime_to_timestamp(now),
    )

    # Add extracted fields
    doc.extracted_fields["farmer_id"] = farmer_id
    doc.extracted_fields["grade"] = "Primary"
    doc.extracted_fields["weight_kg"] = "25.5"

    # Add linkage fields
    doc.linkage_fields["farmer_id"] = farmer_id

    return doc
