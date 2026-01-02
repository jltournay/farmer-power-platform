"""Authentication schemas for the BFF API.

Defines TokenClaims model and AuthErrorCode enum per ADR-003.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuthErrorCode(str, Enum):
    """Standardized auth error codes for consistent API responses.

    These codes are returned in the error detail to help clients
    understand the specific authentication/authorization failure.
    """

    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "invalid_token"
    TOKEN_MISSING = "missing_token"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    FACTORY_ACCESS_DENIED = "factory_access_denied"
    REGULATOR_RESTRICTED = "regulator_restricted"


class TokenClaims(BaseModel):
    """JWT token claims model per ADR-003.

    Contains all user attributes extracted from the JWT token.
    Used for authorization decisions throughout the BFF.

    Attributes:
        sub: User ID (Azure AD object ID or mock user ID).
        email: User email address.
        name: User display name.
        role: Primary role (platform_admin, factory_owner, factory_manager, etc.).
        factory_id: Single factory assignment (for most users).
        factory_ids: Multiple factory assignments (for owners).
        collection_point_id: Collection point assignment (for clerks).
        region_ids: Region assignments (for regulators).
        permissions: List of computed permissions.
    """

    sub: str = Field(..., description="User ID (Azure AD object ID)")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User display name")
    role: str = Field(..., description="Primary role")
    factory_id: str | None = Field(default=None, description="Single factory assignment")
    factory_ids: list[str] = Field(default_factory=list, description="Multi-factory assignments")
    collection_point_id: str | None = Field(default=None, description="Collection point for clerks")
    region_ids: list[str] = Field(default_factory=list, description="Region assignments for regulators")
    permissions: list[str] = Field(default_factory=list, description="Computed permissions")

    @classmethod
    def from_jwt_payload(cls, payload: dict[str, Any]) -> "TokenClaims":
        """Create TokenClaims from JWT payload.

        Extracts all relevant claims from the JWT payload and creates
        a TokenClaims instance with proper defaults for missing fields.

        Args:
            payload: Decoded JWT payload dictionary.

        Returns:
            TokenClaims instance with extracted claims.
        """
        return cls(
            sub=payload.get("sub", ""),
            email=payload.get("email", ""),
            name=payload.get("name", ""),
            role=payload.get("role", ""),
            factory_id=payload.get("factory_id"),
            factory_ids=payload.get("factory_ids", []),
            collection_point_id=payload.get("collection_point_id"),
            region_ids=payload.get("region_ids", []),
            permissions=payload.get("permissions", []),
        )

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: The permission to check (e.g., "farmers:read").

        Returns:
            True if user has the permission or wildcard access.
        """
        # Wildcard permission grants all access
        if "*" in self.permissions:
            return True
        return permission in self.permissions

    def can_access_factory(self, factory_id: str) -> bool:
        """Check if user can access a specific factory.

        Args:
            factory_id: The factory ID to check access for.

        Returns:
            True if user has access to the factory.
        """
        # Platform admins can access all factories
        if self.role == "platform_admin":
            return True

        # Regulators cannot access factory-level data
        if self.role == "regulator":
            return False

        # Check factory assignments
        allowed_factories = self.factory_ids or ([self.factory_id] if self.factory_id else [])
        return factory_id in allowed_factories
