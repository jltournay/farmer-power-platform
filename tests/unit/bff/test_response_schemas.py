"""Unit tests for BFF API response schemas.

Tests all response wrappers per ADR-012:
- ApiResponse[T]: Single entity wrapper
- PaginatedResponse[T]: Paginated list wrapper
- BoundedResponse[T]: Bounded list wrapper (no pagination cursor)
- ApiError: Structured error response
"""

from datetime import UTC, datetime
from uuid import UUID

from bff.api.schemas import (
    ApiError,
    ApiErrorCode,
    ApiResponse,
    BoundedResponse,
    ErrorDetail,
    PaginatedResponse,
    PaginationMeta,
    ResponseMeta,
)
from pydantic import BaseModel


class SampleEntity(BaseModel):
    """Sample entity for testing generic response wrappers."""

    id: str
    name: str


class TestResponseMeta:
    """Tests for ResponseMeta model."""

    def test_default_values(self) -> None:
        """Test default values are auto-generated."""
        meta = ResponseMeta()

        assert meta.request_id is not None
        assert UUID(meta.request_id)  # Valid UUID
        assert meta.timestamp is not None
        assert meta.version == "1.0"

    def test_custom_values(self) -> None:
        """Test custom values can be provided."""
        custom_id = "custom-request-id"
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        meta = ResponseMeta(
            request_id=custom_id,
            timestamp=custom_time,
            version="2.0",
        )

        assert meta.request_id == custom_id
        assert meta.timestamp == custom_time
        assert meta.version == "2.0"


class TestPaginationMeta:
    """Tests for PaginationMeta model."""

    def test_default_values(self) -> None:
        """Test default pagination values."""
        meta = PaginationMeta()

        assert meta.page == 1
        assert meta.page_size == 20
        assert meta.total_count == 0
        assert meta.total_pages == 0
        assert meta.has_next is False
        assert meta.has_prev is False
        assert meta.next_page_token is None

    def test_from_client_response_with_next_page(self) -> None:
        """Test factory method with next_page_token."""
        meta = PaginationMeta.from_client_response(
            total_count=150,
            page_size=20,
            next_page_token="cursor-abc",
            page=1,
        )

        assert meta.page == 1
        assert meta.page_size == 20
        assert meta.total_count == 150
        assert meta.total_pages == 8  # ceil(150/20)
        assert meta.has_next is True
        assert meta.has_prev is False
        assert meta.next_page_token == "cursor-abc"

    def test_from_client_response_no_next_page(self) -> None:
        """Test factory method without next_page_token."""
        meta = PaginationMeta.from_client_response(
            total_count=15,
            page_size=20,
            next_page_token=None,
            page=1,
        )

        assert meta.total_count == 15
        assert meta.total_pages == 1
        assert meta.has_next is False

    def test_from_client_response_middle_page(self) -> None:
        """Test factory method for a middle page."""
        meta = PaginationMeta.from_client_response(
            total_count=100,
            page_size=20,
            next_page_token="cursor-xyz",
            page=3,
        )

        assert meta.page == 3
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_from_client_response_zero_total(self) -> None:
        """Test factory method with zero total count."""
        meta = PaginationMeta.from_client_response(
            total_count=0,
            page_size=20,
            next_page_token=None,
        )

        assert meta.total_count == 0
        assert meta.total_pages == 0
        assert meta.has_next is False


class TestApiResponse:
    """Tests for ApiResponse[T] wrapper."""

    def test_simple_entity(self) -> None:
        """Test wrapping a simple entity."""
        entity = SampleEntity(id="1", name="Test")
        response = ApiResponse(data=entity)

        assert response.data.id == "1"
        assert response.data.name == "Test"
        assert response.meta is not None
        assert response.meta.request_id is not None

    def test_dict_serialization(self) -> None:
        """Test model serialization includes all fields."""
        entity = SampleEntity(id="1", name="Test")
        response = ApiResponse(data=entity)
        data = response.model_dump()

        assert "data" in data
        assert "meta" in data
        assert data["data"]["id"] == "1"
        assert "request_id" in data["meta"]
        assert "timestamp" in data["meta"]
        assert "version" in data["meta"]

    def test_custom_meta(self) -> None:
        """Test providing custom meta."""
        entity = SampleEntity(id="1", name="Test")
        custom_meta = ResponseMeta(request_id="custom-id", version="2.0")
        response = ApiResponse(data=entity, meta=custom_meta)

        assert response.meta.request_id == "custom-id"
        assert response.meta.version == "2.0"


class TestPaginatedResponse:
    """Tests for PaginatedResponse[T] wrapper."""

    def test_from_client_response(self) -> None:
        """Test factory method for converting client responses."""
        items = [
            SampleEntity(id="1", name="First"),
            SampleEntity(id="2", name="Second"),
        ]

        response = PaginatedResponse.from_client_response(
            items=items,
            total_count=100,
            page_size=20,
            next_page_token="cursor-abc",
        )

        assert len(response.data) == 2
        assert response.data[0].id == "1"
        assert response.pagination.total_count == 100
        assert response.pagination.page_size == 20
        assert response.pagination.has_next is True
        assert response.pagination.next_page_token == "cursor-abc"
        assert response.meta is not None

    def test_empty_list(self) -> None:
        """Test with empty list."""
        response = PaginatedResponse.from_client_response(
            items=[],
            total_count=0,
            page_size=20,
        )

        assert len(response.data) == 0
        assert response.pagination.total_count == 0
        assert response.pagination.has_next is False

    def test_last_page(self) -> None:
        """Test last page (no next_page_token)."""
        items = [SampleEntity(id="1", name="Last")]

        response = PaginatedResponse.from_client_response(
            items=items,
            total_count=21,
            page_size=20,
            next_page_token=None,
            page=2,
        )

        assert response.pagination.has_next is False
        assert response.pagination.has_prev is True
        assert response.pagination.next_page_token is None


class TestBoundedResponse:
    """Tests for BoundedResponse[T] wrapper."""

    def test_from_client_response(self) -> None:
        """Test factory method for bounded responses."""
        items = [
            SampleEntity(id="1", name="First"),
            SampleEntity(id="2", name="Second"),
        ]

        response = BoundedResponse.from_client_response(
            items=items,
            total_count=42,
        )

        assert len(response.data) == 2
        assert response.total_count == 42
        assert response.meta is not None

    def test_len_method(self) -> None:
        """Test __len__ returns data length."""
        items = [SampleEntity(id="1", name="Test")]

        response = BoundedResponse.from_client_response(
            items=items,
            total_count=10,  # total_count can be different from data length
        )

        assert len(response) == 1  # data length
        assert response.total_count == 10  # total matching

    def test_empty_response(self) -> None:
        """Test empty bounded response."""
        response = BoundedResponse.from_client_response(
            items=[],
            total_count=0,
        )

        assert len(response) == 0
        assert response.total_count == 0


class TestErrorDetail:
    """Tests for ErrorDetail model."""

    def test_basic_error(self) -> None:
        """Test basic error with field and message."""
        error = ErrorDetail(
            field="email",
            message="Invalid email format",
        )

        assert error.field == "email"
        assert error.message == "Invalid email format"
        assert error.code is None

    def test_error_with_code(self) -> None:
        """Test error with optional code."""
        error = ErrorDetail(
            field="phone",
            message="Phone is required",
            code="required",
        )

        assert error.field == "phone"
        assert error.message == "Phone is required"
        assert error.code == "required"


class TestApiError:
    """Tests for ApiError model."""

    def test_direct_creation(self) -> None:
        """Test direct error creation."""
        error = ApiError(
            code="custom_error",
            message="Something went wrong",
        )

        assert error.code == "custom_error"
        assert error.message == "Something went wrong"
        assert error.details is None

    def test_validation_error_factory(self) -> None:
        """Test validation_error factory method."""
        errors = [
            ErrorDetail(field="email", message="Invalid format", code="invalid_format"),
            ErrorDetail(field="phone", message="Required", code="required"),
        ]

        error = ApiError.validation_error(errors)

        assert error.code == "validation_error"
        assert error.message == "Request validation failed"
        assert error.details is not None
        assert len(error.details["fields"]) == 2
        assert error.details["fields"][0]["field"] == "email"

    def test_not_found_factory(self) -> None:
        """Test not_found factory method."""
        error = ApiError.not_found("Farmer", "WM-9999")

        assert error.code == "not_found"
        assert error.message == "Farmer with ID 'WM-9999' not found"

    def test_unauthorized_factory(self) -> None:
        """Test unauthorized factory method."""
        error = ApiError.unauthorized()

        assert error.code == "unauthorized"
        assert error.message == "Authentication required"

    def test_unauthorized_custom_message(self) -> None:
        """Test unauthorized with custom message."""
        error = ApiError.unauthorized("Token has expired")

        assert error.code == "unauthorized"
        assert error.message == "Token has expired"

    def test_forbidden_factory(self) -> None:
        """Test forbidden factory method."""
        error = ApiError.forbidden()

        assert error.code == "forbidden"
        assert error.message == "Access denied"

    def test_forbidden_custom_message(self) -> None:
        """Test forbidden with custom message."""
        error = ApiError.forbidden("You don't have access to this factory")

        assert error.code == "forbidden"
        assert error.message == "You don't have access to this factory"

    def test_service_unavailable_factory(self) -> None:
        """Test service_unavailable factory method."""
        error = ApiError.service_unavailable("Plantation Model")

        assert error.code == "service_unavailable"
        assert error.message == "Service 'Plantation Model' is currently unavailable"

    def test_internal_error_factory(self) -> None:
        """Test internal_error factory method."""
        error = ApiError.internal_error()

        assert error.code == "internal_error"
        assert error.message == "An internal error occurred"

    def test_internal_error_custom_message(self) -> None:
        """Test internal_error with custom message."""
        error = ApiError.internal_error("Database connection failed")

        assert error.code == "internal_error"
        assert error.message == "Database connection failed"

    def test_bad_request_factory(self) -> None:
        """Test bad_request factory method."""
        error = ApiError.bad_request("Invalid JSON in request body")

        assert error.code == "bad_request"
        assert error.message == "Invalid JSON in request body"


class TestApiErrorCode:
    """Tests for ApiErrorCode enum."""

    def test_all_error_codes_defined(self) -> None:
        """Test all expected error codes are defined."""
        expected_codes = {
            "validation_error",
            "not_found",
            "unauthorized",
            "forbidden",
            "internal_error",
            "service_unavailable",
            "bad_request",
            "conflict",
        }

        actual_codes = {code.value for code in ApiErrorCode}

        assert actual_codes == expected_codes

    def test_enum_string_values(self) -> None:
        """Test enum values are lowercase strings."""
        assert ApiErrorCode.VALIDATION_ERROR.value == "validation_error"
        assert ApiErrorCode.NOT_FOUND.value == "not_found"
        assert ApiErrorCode.UNAUTHORIZED.value == "unauthorized"
        assert ApiErrorCode.FORBIDDEN.value == "forbidden"
        assert ApiErrorCode.INTERNAL_ERROR.value == "internal_error"
        assert ApiErrorCode.SERVICE_UNAVAILABLE.value == "service_unavailable"
        assert ApiErrorCode.BAD_REQUEST.value == "bad_request"
        assert ApiErrorCode.CONFLICT.value == "conflict"


class TestSchemaExports:
    """Tests for schema module exports."""

    def test_all_exports_importable(self) -> None:
        """Test all exports are importable from schemas package."""
        from bff.api.schemas import (
            ApiError,
            ApiErrorCode,
            ApiResponse,
            AuthErrorCode,
            BoundedResponse,
            ErrorDetail,
            PaginatedResponse,
            PaginationMeta,
            ResponseMeta,
            TokenClaims,
        )

        # All imports should be valid
        assert ApiResponse is not None
        assert PaginatedResponse is not None
        assert BoundedResponse is not None
        assert ApiError is not None
        assert ApiErrorCode is not None
        assert ErrorDetail is not None
        assert PaginationMeta is not None
        assert ResponseMeta is not None
        assert TokenClaims is not None
        assert AuthErrorCode is not None
