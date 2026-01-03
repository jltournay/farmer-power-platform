"""BFF API schemas (Pydantic models).

This package contains request/response schemas for the BFF API.

Response Wrappers (ADR-012):
    - ApiResponse[T]: Single entity responses
    - PaginatedResponse[T]: Paginated list responses with cursor support
    - BoundedResponse[T]: Bounded list responses (no pagination cursor)
    - ApiError: Structured error responses

Auth Schemas (ADR-003):
    - TokenClaims: JWT token claims model
    - AuthErrorCode: Auth-specific error codes
"""

from bff.api.schemas.auth import AuthErrorCode, TokenClaims
from bff.api.schemas.responses import (
    ApiError,
    ApiErrorCode,
    ApiResponse,
    BoundedResponse,
    ErrorDetail,
    PaginatedResponse,
    PaginationMeta,
    ResponseMeta,
)

__all__ = [
    "ApiError",
    "ApiErrorCode",
    "ApiResponse",
    "AuthErrorCode",
    "BoundedResponse",
    "ErrorDetail",
    "PaginatedResponse",
    "PaginationMeta",
    "ResponseMeta",
    "TokenClaims",
]
