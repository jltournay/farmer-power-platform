"""Authentication and authorization middleware for the BFF API.

Implements dual-mode JWT validation (mock + Azure B2C) per ADR-003.
"""

from collections.abc import Callable

from bff.api.schemas.auth import AuthErrorCode, TokenClaims
from bff.config import Settings, get_settings
from fastapi import Depends, HTTPException, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from opentelemetry import trace

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=True)


def _add_user_to_trace(user: TokenClaims) -> None:
    """Add user context to current OTel span (no PII).

    Adds user ID, role, and factory_id to the current span for
    tracing and debugging purposes. Does NOT add email or name
    to protect PII.

    Args:
        user: The authenticated user's token claims.
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("user.id", user.sub)
        span.set_attribute("user.role", user.role)
        if user.factory_id:
            span.set_attribute("user.factory_id", user.factory_id)
        if user.factory_ids:
            span.set_attribute("user.factory_count", len(user.factory_ids))


def _validate_mock_token(token: str, secret: str) -> dict:
    """Validate JWT token using mock mode (HS256 with local secret).

    Args:
        token: The JWT token string.
        secret: The HS256 secret for validation.

    Returns:
        Decoded JWT payload.

    Raises:
        ExpiredSignatureError: If token is expired.
        JWTError: If token is invalid.
    """
    return jwt.decode(token, secret, algorithms=["HS256"])


async def _validate_azure_b2c_token(token: str, settings: Settings) -> dict:
    """Validate JWT token using Azure B2C (RS256 with JWKS).

    This is a stub implementation for Story 0.5.3.
    Full JWKS validation will be implemented in Story 0.5.8.

    Args:
        token: The JWT token string.
        settings: Application settings containing B2C configuration.

    Returns:
        Decoded JWT payload.

    Raises:
        NotImplementedError: Azure B2C validation is not yet implemented.
    """
    # Story 0.5.8 will implement:
    # 1. JWKS endpoint fetching from Azure B2C
    # 2. Key caching for 24 hours
    # 3. RS256 signature validation
    raise NotImplementedError("Azure B2C token validation not yet implemented. This will be completed in Story 0.5.8.")


async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> TokenClaims:
    """Validate JWT token - supports both mock and Azure B2C modes.

    This is the main token validation dependency that routes to the
    appropriate validator based on the AUTH_PROVIDER setting.

    Args:
        credentials: HTTP Bearer credentials from the request.
        settings: Application settings.

    Returns:
        TokenClaims extracted from the validated JWT.

    Raises:
        HTTPException: 401 if token is invalid or expired.
    """
    token = credentials.credentials

    try:
        if settings.auth_provider == "mock":
            payload = _validate_mock_token(token, settings.mock_jwt_secret)
        else:
            # Azure B2C mode
            payload = await _validate_azure_b2c_token(token, settings)

        claims = TokenClaims.from_jwt_payload(payload)
        _add_user_to_trace(claims)
        return claims

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={
                "code": AuthErrorCode.TOKEN_EXPIRED.value,
                "message": "Token has expired",
            },
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={
                "code": AuthErrorCode.TOKEN_INVALID.value,
                "message": "Invalid token",
            },
        )


async def get_current_user(
    claims: TokenClaims = Depends(validate_token),
) -> TokenClaims:
    """FastAPI dependency to get the current authenticated user.

    This is a convenience wrapper around validate_token that can be
    used in route handlers to get the current user's claims.

    Args:
        claims: Token claims from validate_token.

    Returns:
        The authenticated user's token claims.
    """
    return claims


def require_permission(permission: str) -> Callable:
    """Create a dependency that checks for a specific permission.

    Use this as a decorator on route handlers to enforce permission-based
    access control.

    Example:
        @router.get("/farmers")
        async def list_farmers(
            user: TokenClaims = require_permission("farmers:read"),
        ):
            ...

    Args:
        permission: The required permission (e.g., "farmers:read").

    Returns:
        A FastAPI dependency that validates the permission.
    """

    async def checker(user: TokenClaims = Depends(get_current_user)) -> TokenClaims:
        """Check if user has the required permission.

        Args:
            user: The authenticated user's token claims.

        Returns:
            The user's token claims if permission is granted.

        Raises:
            HTTPException: 403 if user lacks the required permission.
        """
        # Platform admins bypass all permission checks
        if user.role == "platform_admin":
            return user

        # Check for wildcard permission
        if "*" in user.permissions:
            return user

        # Check specific permission
        if permission not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": AuthErrorCode.INSUFFICIENT_PERMISSIONS.value,
                    "message": f"Requires {permission} permission",
                },
            )
        return user

    return Depends(checker)


def require_factory_access(factory_id_param: str = "factory_id") -> Callable:
    """Create a dependency that ensures user has access to the requested factory.

    Use this to enforce factory-level isolation on routes that accept
    a factory_id path parameter.

    Example:
        @router.get("/factories/{factory_id}/farmers")
        async def list_factory_farmers(
            factory_id: str,
            user: TokenClaims = require_factory_access(),
        ):
            ...

    Args:
        factory_id_param: Name of the path parameter containing factory_id.

    Returns:
        A FastAPI dependency that validates factory access.
    """

    async def checker(
        user: TokenClaims = Depends(get_current_user),
        factory_id: str = Path(alias=factory_id_param),
    ) -> TokenClaims:
        """Check if user has access to the requested factory.

        Args:
            user: The authenticated user's token claims.
            factory_id: The factory ID from the path parameter.

        Returns:
            The user's token claims if access is granted.

        Raises:
            HTTPException: 403 if user cannot access the factory.
        """
        # Platform admins can access all factories
        if user.role == "platform_admin":
            return user

        # Regulators cannot access factory-level data
        if user.role == "regulator":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": AuthErrorCode.REGULATOR_RESTRICTED.value,
                    "message": "Regulators cannot access factory-level data",
                },
            )

        # Check factory access
        allowed_factories = user.factory_ids or ([user.factory_id] if user.factory_id else [])
        if factory_id not in allowed_factories:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": AuthErrorCode.FACTORY_ACCESS_DENIED.value,
                    "message": "No access to this factory",
                },
            )

        return user

    return Depends(checker)


def require_platform_admin() -> Callable:
    """Create a dependency that requires platform_admin role.

    Use this on admin portal routes that should only be accessible
    to platform administrators.

    Example:
        @router.get("/admin/regions")
        async def list_regions(
            user: TokenClaims = require_platform_admin(),
        ):
            ...

    Returns:
        A FastAPI dependency that validates platform_admin role.
    """

    async def checker(user: TokenClaims = Depends(get_current_user)) -> TokenClaims:
        """Check if user has platform_admin role.

        Args:
            user: The authenticated user's token claims.

        Returns:
            The user's token claims if role is platform_admin.

        Raises:
            HTTPException: 403 if user is not a platform admin.
        """
        if user.role != "platform_admin":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": AuthErrorCode.INSUFFICIENT_PERMISSIONS.value,
                    "message": "Platform admin access required",
                },
            )
        return user

    return Depends(checker)
