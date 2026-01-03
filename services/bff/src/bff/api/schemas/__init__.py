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

Farmer Schemas (Story 0.5.4b):
    - FarmerSummary: Farmer list item
    - FarmerListResponse: Paginated farmer list
    - FarmerDetailResponse: Full farmer detail with performance
    - TierLevel, TrendIndicator: Quality presentation enums
"""

from bff.api.schemas.auth import AuthErrorCode, TokenClaims
from bff.api.schemas.farmer_schemas import (
    FarmerDetailResponse,
    FarmerListResponse,
    FarmerPerformanceAPI,
    FarmerProfile,
    FarmerSummary,
    TierLevel,
    TrendIndicator,
)
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
    "FarmerDetailResponse",
    "FarmerListResponse",
    "FarmerPerformanceAPI",
    "FarmerProfile",
    "FarmerSummary",
    "PaginatedResponse",
    "PaginationMeta",
    "ResponseMeta",
    "TierLevel",
    "TokenClaims",
    "TrendIndicator",
]
