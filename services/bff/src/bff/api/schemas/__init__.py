"""BFF API schemas (Pydantic models).

This package contains request/response schemas for the BFF API.
"""

from bff.api.schemas.auth import AuthErrorCode, TokenClaims

__all__ = [
    "AuthErrorCode",
    "TokenClaims",
]
