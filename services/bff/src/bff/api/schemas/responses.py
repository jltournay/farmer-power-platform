"""BFF API response wrapper schemas per ADR-012.

This module provides standardized response wrappers for the BFF API:

- ApiResponse[T]: Single entity responses
- PaginatedResponse[T]: Paginated list responses with cursor support
- BoundedResponse[T]: Bounded list responses (no pagination cursor)
- ApiError: Structured error responses with field-level details

All responses follow Google JSON style guide and ADR-012 patterns.

References:
    - ADR-012: BFF Service Composition & API Design (§4.1-4.3)
    - Google JSON Style Guide: https://google.github.io/styleguide/jsoncstyleguide.xml

Example:
    >>> from bff.api.schemas import ApiResponse, PaginatedResponse
    >>> response = ApiResponse(data=farmer)
    >>> paginated = PaginatedResponse.from_client_response(
    ...     items=farmers,
    ...     total_count=150,
    ...     page_size=20,
    ...     next_page_token="cursor-abc",
    ... )
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiErrorCode(str, Enum):
    """Standard API error codes per ADR-012.

    These codes are used in ApiError responses to provide machine-readable
    error categorization. Distinct from AuthErrorCode which is auth-specific.
    """

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    BAD_REQUEST = "bad_request"
    CONFLICT = "conflict"


class ResponseMeta(BaseModel):
    """Metadata included in all API responses.

    Provides tracing information and API versioning for debugging
    and client compatibility.

    Attributes:
        request_id: Unique identifier for this request (auto-generated).
        timestamp: When the response was generated.
        version: API version string.
    """

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses.

    Supports both offset-based (page number) and cursor-based pagination.
    The next_page_token is opaque to clients and should be passed back
    unchanged to retrieve the next page.

    Attributes:
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        total_count: Total number of items across all pages.
        total_pages: Total number of pages.
        has_next: Whether there are more pages after this one.
        has_prev: Whether there are pages before this one.
        next_page_token: Opaque cursor for fetching the next page.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    total_count: int = Field(default=0, ge=0)
    total_pages: int = Field(default=0, ge=0)
    has_next: bool = False
    has_prev: bool = False
    next_page_token: str | None = None

    @classmethod
    def from_client_response(
        cls,
        total_count: int,
        page_size: int,
        next_page_token: str | None = None,
        page: int = 1,
    ) -> "PaginationMeta":
        """Create pagination metadata from gRPC client response.

        Convenience factory for converting client list_* response tuples
        into pagination metadata.

        Args:
            total_count: Total number of items (from client response).
            page_size: Number of items requested per page.
            next_page_token: Cursor for next page (None if no more pages).
            page: Current page number (default: 1).

        Returns:
            PaginationMeta with calculated has_next, has_prev, total_pages.

        Example:
            >>> meta = PaginationMeta.from_client_response(
            ...     total_count=150,
            ...     page_size=20,
            ...     next_page_token="cursor-abc",
            ...     page=1,
            ... )
            >>> meta.total_pages
            8
            >>> meta.has_next
            True
        """
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=next_page_token is not None,
            has_prev=page > 1,
            next_page_token=next_page_token,
        )


class ApiResponse(BaseModel, Generic[T]):
    """Standard wrapper for single-entity API responses.

    Wraps a single entity with metadata for consistent response format
    per ADR-012 §4.1.

    Attributes:
        data: The response payload (single entity of type T).
        meta: Response metadata (request_id, timestamp, version).

    Example:
        >>> farmer = Farmer(id="WM-0001", name="John")
        >>> response = ApiResponse(data=farmer)
        >>> response.model_dump()
        {"data": {...}, "meta": {"request_id": "...", ...}}
    """

    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard wrapper for paginated list API responses.

    Wraps a list of entities with pagination metadata for cursor-based
    or offset-based pagination per ADR-012 §4.2.

    Attributes:
        data: List of entities of type T.
        pagination: Pagination metadata (page, total_count, next_page_token, etc.).
        meta: Response metadata (request_id, timestamp, version).

    Example:
        >>> response = PaginatedResponse.from_client_response(
        ...     items=farmers,
        ...     total_count=150,
        ...     page_size=20,
        ...     next_page_token="cursor-abc",
        ... )
        >>> len(response.data)
        20
        >>> response.pagination.has_next
        True
    """

    data: list[T]
    pagination: PaginationMeta
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    @classmethod
    def from_client_response(
        cls,
        items: list[T],
        total_count: int,
        page_size: int,
        next_page_token: str | None = None,
        page: int = 1,
    ) -> "PaginatedResponse[T]":
        """Create paginated response from gRPC client response.

        Convenience factory for converting client list_* response tuples
        (items, next_page_token, total_count) into PaginatedResponse.

        Args:
            items: List of items from client response.
            total_count: Total count from client response.
            page_size: Number of items requested per page.
            next_page_token: Cursor for next page (None if no more pages).
            page: Current page number (default: 1).

        Returns:
            PaginatedResponse with data and pagination metadata.

        Example:
            >>> farmers, next_token, total = await client.list_farmers(page_size=20)
            >>> response = PaginatedResponse.from_client_response(
            ...     items=farmers,
            ...     total_count=total,
            ...     page_size=20,
            ...     next_page_token=next_token,
            ... )
        """
        pagination = PaginationMeta.from_client_response(
            total_count=total_count,
            page_size=page_size,
            next_page_token=next_page_token,
            page=page,
        )
        return cls(data=items, pagination=pagination)


class BoundedResponse(BaseModel, Generic[T]):
    """Wrapper for bounded lists (all items up to limit, no pagination cursor).

    Used for methods that return a bounded result set without pagination,
    such as get_documents_by_farmer which returns all documents for a farmer
    up to a specified limit.

    Unlike PaginatedResponse, this has no next_page_token and is intended
    for complete (or limit-bounded) result sets.

    Attributes:
        data: List of entities of type T.
        total_count: Total number of items matching the query.
        meta: Response metadata (request_id, timestamp, version).

    Example:
        >>> response = BoundedResponse.from_client_response(
        ...     items=documents,
        ...     total_count=42,
        ... )
        >>> len(response)
        42
    """

    data: list[T]
    total_count: int = Field(ge=0)
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    def __len__(self) -> int:
        """Return count of items returned."""
        return len(self.data)

    @classmethod
    def from_client_response(
        cls,
        items: list[T],
        total_count: int,
    ) -> "BoundedResponse[T]":
        """Create bounded response from gRPC client response.

        Convenience factory for converting client get_*_by_* response tuples
        (items, total_count) into BoundedResponse.

        Args:
            items: List of items from client response.
            total_count: Total count from client response.

        Returns:
            BoundedResponse with data and total_count.

        Example:
            >>> docs, total = await client.get_documents_by_farmer("WM-0001", "qc")
            >>> response = BoundedResponse.from_client_response(
            ...     items=docs,
            ...     total_count=total,
            ... )
        """
        return cls(data=items, total_count=total_count)


class ErrorDetail(BaseModel):
    """Field-level validation error detail.

    Provides structured information about a specific validation failure
    on a request field. Multiple ErrorDetails can be included in an
    ApiError for comprehensive validation feedback.

    Attributes:
        field: Field path that failed validation (e.g., "contact.phone").
        message: Human-readable error description.
        code: Optional machine-readable error code for this field.

    Example:
        >>> error = ErrorDetail(
        ...     field="contact.phone",
        ...     message="Invalid phone format",
        ...     code="invalid_format",
        ... )
    """

    field: str
    message: str
    code: str | None = None


class ApiError(BaseModel):
    """Structured error response per ADR-012 §4.3.

    Provides consistent error formatting with optional field-level details
    for validation errors. Can be used with FastAPI HTTPException.

    Attributes:
        code: Error code from ApiErrorCode enum (or custom string).
        message: Human-readable error description.
        details: Optional additional error context (e.g., field errors).

    Example:
        >>> error = ApiError.validation_error([
        ...     ErrorDetail(field="phone", message="Invalid format"),
        ...     ErrorDetail(field="email", message="Required"),
        ... ])
        >>> error.code
        'validation_error'
        >>> len(error.details["fields"])
        2
    """

    code: str
    message: str
    details: dict | None = None

    @classmethod
    def validation_error(cls, errors: list[ErrorDetail]) -> "ApiError":
        """Create validation error with field details.

        Factory method for creating a standardized validation error
        response with multiple field-level errors.

        Args:
            errors: List of ErrorDetail instances for each field error.

        Returns:
            ApiError with code="validation_error" and field details.

        Example:
            >>> error = ApiError.validation_error([
            ...     ErrorDetail(field="phone", message="Invalid format"),
            ... ])
        """
        return cls(
            code=ApiErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            details={"fields": [e.model_dump() for e in errors]},
        )

    @classmethod
    def not_found(cls, resource: str, resource_id: str) -> "ApiError":
        """Create not found error.

        Factory method for creating a standardized not found error.

        Args:
            resource: Type of resource (e.g., "Farmer", "Factory").
            resource_id: ID of the resource that was not found.

        Returns:
            ApiError with code="not_found".

        Example:
            >>> error = ApiError.not_found("Farmer", "WM-9999")
            >>> error.message
            "Farmer with ID 'WM-9999' not found"
        """
        return cls(
            code=ApiErrorCode.NOT_FOUND.value,
            message=f"{resource} with ID '{resource_id}' not found",
        )

    @classmethod
    def unauthorized(cls, message: str = "Authentication required") -> "ApiError":
        """Create unauthorized error.

        Factory method for creating a standardized authentication error.

        Args:
            message: Custom error message (default: "Authentication required").

        Returns:
            ApiError with code="unauthorized".
        """
        return cls(
            code=ApiErrorCode.UNAUTHORIZED.value,
            message=message,
        )

    @classmethod
    def forbidden(cls, message: str = "Access denied") -> "ApiError":
        """Create forbidden error.

        Factory method for creating a standardized authorization error.

        Args:
            message: Custom error message (default: "Access denied").

        Returns:
            ApiError with code="forbidden".
        """
        return cls(
            code=ApiErrorCode.FORBIDDEN.value,
            message=message,
        )

    @classmethod
    def service_unavailable(cls, service: str) -> "ApiError":
        """Create service unavailable error.

        Factory method for creating a standardized service error
        when a downstream service is unreachable.

        Args:
            service: Name of the unavailable service.

        Returns:
            ApiError with code="service_unavailable".

        Example:
            >>> error = ApiError.service_unavailable("Plantation Model")
        """
        return cls(
            code=ApiErrorCode.SERVICE_UNAVAILABLE.value,
            message=f"Service '{service}' is currently unavailable",
        )

    @classmethod
    def internal_error(cls, message: str = "An internal error occurred") -> "ApiError":
        """Create internal error.

        Factory method for creating a standardized internal server error.
        Use sparingly - prefer more specific error types when possible.

        Args:
            message: Custom error message.

        Returns:
            ApiError with code="internal_error".
        """
        return cls(
            code=ApiErrorCode.INTERNAL_ERROR.value,
            message=message,
        )

    @classmethod
    def bad_request(cls, message: str) -> "ApiError":
        """Create bad request error.

        Factory method for creating a standardized bad request error
        for malformed or invalid requests (not field validation).

        Args:
            message: Description of what's wrong with the request.

        Returns:
            ApiError with code="bad_request".
        """
        return cls(
            code=ApiErrorCode.BAD_REQUEST.value,
            message=message,
        )

    @classmethod
    def conflict(cls, message: str) -> "ApiError":
        """Create conflict error.

        Factory method for creating a standardized conflict error
        when a resource state conflict occurs (e.g., duplicate entry,
        optimistic locking failure).

        Args:
            message: Description of the conflict.

        Returns:
            ApiError with code="conflict".

        Example:
            >>> error = ApiError.conflict("Farmer with this phone already exists")
        """
        return cls(
            code=ApiErrorCode.CONFLICT.value,
            message=message,
        )
