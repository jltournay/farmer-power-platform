"""Unit tests for BFF authentication middleware.

Tests AC1-7 for Story 0.5.3: BFF Auth Middleware.
"""

import pytest
from bff.api.middleware.auth import (
    get_current_user,
    require_factory_access,
    require_permission,
)
from bff.api.schemas.auth import AuthErrorCode, TokenClaims
from bff.config import Settings, get_settings
from fastapi import Depends, FastAPI, Path
from fastapi.testclient import TestClient
from pydantic import ValidationError

from .conftest import (
    MOCK_JWT_SECRET,
    MOCK_USERS,
    auth_headers,
    create_mock_jwt_token,
)

# =============================================================================
# AC1: Mock Mode Token Validation
# =============================================================================


class TestMockModeTokenValidation:
    """Tests for AC1: Mock mode token validation."""

    def test_valid_token_extracts_claims(self, mock_manager_token: str) -> None:
        """Given a valid mock token, claims are extracted correctly."""
        # Create a test app with auth endpoint
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        # Override get_settings dependency
        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/test")
        async def test_endpoint(user: TokenClaims = Depends(get_current_user)):
            return {"sub": user.sub, "role": user.role}

        client = TestClient(app)
        response = client.get("/test", headers=auth_headers(mock_manager_token))

        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "mock-manager-001"
        assert data["role"] == "factory_manager"

    def test_invalid_token_returns_401(self, invalid_token: str) -> None:
        """Given an invalid token, 401 is returned."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/test")
        async def test_endpoint(user: TokenClaims = Depends(get_current_user)):
            return {"sub": user.sub}

        client = TestClient(app)
        response = client.get("/test", headers=auth_headers(invalid_token))

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == AuthErrorCode.TOKEN_INVALID.value

    def test_missing_token_returns_401_or_403(self) -> None:
        """Given no token, 401 or 403 is returned (HTTPBearer auto_error)."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/test")
        async def test_endpoint(user: TokenClaims = Depends(get_current_user)):
            return {"sub": user.sub}

        client = TestClient(app)
        response = client.get("/test")

        # HTTPBearer with auto_error=True returns 401 or 403 for missing token
        # depending on FastAPI version (older returns 403, newer returns 401)
        assert response.status_code in (401, 403)


# =============================================================================
# AC3: Token Claims Extraction
# =============================================================================


class TestTokenClaimsExtraction:
    """Tests for AC3: Token claims extraction."""

    def test_from_jwt_payload_extracts_all_fields(self) -> None:
        """Given a JWT payload, all claim fields are extracted."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "factory_manager",
            "factory_id": "FAC-001",
            "factory_ids": ["FAC-001", "FAC-002"],
            "collection_point_id": "CP-001",
            "region_ids": ["region-a", "region-b"],
            "permissions": ["farmers:read", "farmers:write"],
        }

        claims = TokenClaims.from_jwt_payload(payload)

        assert claims.sub == "user-123"
        assert claims.email == "test@example.com"
        assert claims.name == "Test User"
        assert claims.role == "factory_manager"
        assert claims.factory_id == "FAC-001"
        assert claims.factory_ids == ["FAC-001", "FAC-002"]
        assert claims.collection_point_id == "CP-001"
        assert claims.region_ids == ["region-a", "region-b"]
        assert claims.permissions == ["farmers:read", "farmers:write"]

    def test_from_jwt_payload_defaults_missing_fields(self) -> None:
        """Given a minimal payload, missing fields get defaults."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "viewer",
        }

        claims = TokenClaims.from_jwt_payload(payload)

        assert claims.sub == "user-123"
        assert claims.factory_id is None
        assert claims.factory_ids == []
        assert claims.collection_point_id is None
        assert claims.region_ids == []
        assert claims.permissions == []

    def test_has_permission_with_wildcard(self) -> None:
        """Given wildcard permission, any permission check returns True."""
        claims = TokenClaims(
            sub="admin",
            email="admin@test.com",
            name="Admin",
            role="platform_admin",
            permissions=["*"],
        )

        assert claims.has_permission("farmers:read") is True
        assert claims.has_permission("anything:else") is True

    def test_has_permission_specific(self) -> None:
        """Given specific permissions, only those return True."""
        claims = TokenClaims(
            sub="user",
            email="user@test.com",
            name="User",
            role="factory_manager",
            permissions=["farmers:read", "quality_events:read"],
        )

        assert claims.has_permission("farmers:read") is True
        assert claims.has_permission("quality_events:read") is True
        assert claims.has_permission("farmers:write") is False

    def test_can_access_factory_platform_admin(self) -> None:
        """Given platform_admin, any factory is accessible."""
        claims = TokenClaims(
            sub="admin",
            email="admin@test.com",
            name="Admin",
            role="platform_admin",
            permissions=["*"],
        )

        assert claims.can_access_factory("FAC-001") is True
        assert claims.can_access_factory("ANY-FACTORY") is True

    def test_can_access_factory_regulator_blocked(self) -> None:
        """Given regulator role, factory access is blocked."""
        claims = TokenClaims(
            sub="regulator",
            email="reg@test.com",
            name="Regulator",
            role="regulator",
            region_ids=["region-a"],
            permissions=["national_stats:read"],
        )

        assert claims.can_access_factory("FAC-001") is False

    def test_can_access_factory_with_assignment(self) -> None:
        """Given factory assignment, only those factories are accessible."""
        claims = TokenClaims(
            sub="manager",
            email="manager@test.com",
            name="Manager",
            role="factory_manager",
            factory_id="FAC-001",
            factory_ids=["FAC-001"],
            permissions=["farmers:read"],
        )

        assert claims.can_access_factory("FAC-001") is True
        assert claims.can_access_factory("FAC-002") is False


# =============================================================================
# AC4: Permission-Based Authorization
# =============================================================================


class TestPermissionBasedAuthorization:
    """Tests for AC4: Permission decorator."""

    def test_permission_allowed(self, mock_manager_token: str) -> None:
        """Given user with permission, access is allowed."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/farmers")
        async def list_farmers(user: TokenClaims = require_permission("farmers:read")):
            return {"user": user.sub}

        client = TestClient(app)
        response = client.get("/farmers", headers=auth_headers(mock_manager_token))

        assert response.status_code == 200
        assert response.json()["user"] == "mock-manager-001"

    def test_permission_denied(self, mock_manager_token: str) -> None:
        """Given user without permission, 403 is returned."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/settings")
        async def update_settings(
            user: TokenClaims = require_permission("factory_settings:write"),
        ):
            return {"user": user.sub}

        client = TestClient(app)
        response = client.get("/settings", headers=auth_headers(mock_manager_token))

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == AuthErrorCode.INSUFFICIENT_PERMISSIONS.value

    def test_platform_admin_bypasses_permission(self, mock_admin_token: str) -> None:
        """Given platform_admin, permission checks are bypassed."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/settings")
        async def update_settings(
            user: TokenClaims = require_permission("any_permission:write"),
        ):
            return {"user": user.sub}

        client = TestClient(app)
        response = client.get("/settings", headers=auth_headers(mock_admin_token))

        assert response.status_code == 200
        assert response.json()["user"] == "mock-admin-001"


# =============================================================================
# AC5: Factory-Level Authorization
# =============================================================================


class TestFactoryLevelAuthorization:
    """Tests for AC5: Factory access decorator."""

    def test_own_factory_access_allowed(self, mock_manager_token: str) -> None:
        """Given user accessing own factory, access is allowed."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/factories/{factory_id}/farmers")
        async def list_factory_farmers(
            factory_id: str = Path(...),
            user: TokenClaims = require_factory_access(),
        ):
            return {"factory_id": factory_id, "user": user.sub}

        client = TestClient(app)
        response = client.get(
            "/factories/KEN-FAC-001/farmers",
            headers=auth_headers(mock_manager_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["factory_id"] == "KEN-FAC-001"
        assert data["user"] == "mock-manager-001"

    def test_other_factory_access_denied(self, mock_manager_token: str) -> None:
        """Given user accessing other factory, 403 is returned."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/factories/{factory_id}/farmers")
        async def list_factory_farmers(
            factory_id: str = Path(...),
            user: TokenClaims = require_factory_access(),
        ):
            return {"factory_id": factory_id}

        client = TestClient(app)
        response = client.get(
            "/factories/KEN-FAC-999/farmers",
            headers=auth_headers(mock_manager_token),
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == AuthErrorCode.FACTORY_ACCESS_DENIED.value

    def test_multi_factory_owner_access(self, mock_owner_token: str) -> None:
        """Given owner with multiple factories, all are accessible."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/factories/{factory_id}/farmers")
        async def list_factory_farmers(
            factory_id: str = Path(...),
            user: TokenClaims = require_factory_access(),
        ):
            return {"factory_id": factory_id, "user": user.sub}

        client = TestClient(app)

        # Access first factory
        response1 = client.get(
            "/factories/KEN-FAC-001/farmers",
            headers=auth_headers(mock_owner_token),
        )
        assert response1.status_code == 200

        # Access second factory
        response2 = client.get(
            "/factories/KEN-FAC-002/farmers",
            headers=auth_headers(mock_owner_token),
        )
        assert response2.status_code == 200

    def test_regulator_factory_access_blocked(self, mock_regulator_token: str) -> None:
        """Given regulator, factory access is blocked."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/factories/{factory_id}/farmers")
        async def list_factory_farmers(
            factory_id: str = Path(...),
            user: TokenClaims = require_factory_access(),
        ):
            return {"factory_id": factory_id}

        client = TestClient(app)
        response = client.get(
            "/factories/KEN-FAC-001/farmers",
            headers=auth_headers(mock_regulator_token),
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == AuthErrorCode.REGULATOR_RESTRICTED.value

    def test_platform_admin_bypasses_factory_restriction(self, mock_admin_token: str) -> None:
        """Given platform_admin, factory restrictions are bypassed."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/factories/{factory_id}/farmers")
        async def list_factory_farmers(
            factory_id: str = Path(...),
            user: TokenClaims = require_factory_access(),
        ):
            return {"factory_id": factory_id, "user": user.sub}

        client = TestClient(app)
        response = client.get(
            "/factories/ANY-FACTORY/farmers",
            headers=auth_headers(mock_admin_token),
        )

        assert response.status_code == 200
        assert response.json()["user"] == "mock-admin-001"


# =============================================================================
# AC6: Token Expiry Handling
# =============================================================================


class TestTokenExpiryHandling:
    """Tests for AC6: Token expiry handling."""

    def test_expired_token_returns_401_with_code(self, expired_token: str) -> None:
        """Given an expired token, 401 is returned with token_expired code."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="mock",
                mock_jwt_secret=MOCK_JWT_SECRET,
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/test")
        async def test_endpoint(user: TokenClaims = Depends(get_current_user)):
            return {"sub": user.sub}

        client = TestClient(app)
        response = client.get("/test", headers=auth_headers(expired_token))

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == AuthErrorCode.TOKEN_EXPIRED.value
        assert "expired" in data["detail"]["message"].lower()


# =============================================================================
# AC7: Security Guardrail
# =============================================================================


class TestSecurityGuardrail:
    """Tests for AC7: Mock mode in production guardrail."""

    def test_mock_in_production_raises_error(self) -> None:
        """Given mock auth in production, startup fails."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                auth_provider="mock",
                app_env="production",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "SECURITY ERROR" in str(errors[0]["msg"])

    def test_mock_in_development_allowed(self) -> None:
        """Given mock auth in development, startup succeeds."""
        settings = Settings(
            auth_provider="mock",
            app_env="development",
        )
        assert settings.auth_provider == "mock"
        assert settings.app_env == "development"

    def test_azure_b2c_in_production_allowed(self) -> None:
        """Given azure-b2c in production, startup succeeds."""
        settings = Settings(
            auth_provider="azure-b2c",
            app_env="production",
        )
        assert settings.auth_provider == "azure-b2c"
        assert settings.app_env == "production"


# =============================================================================
# AC2: Azure B2C Mode (Stub)
# =============================================================================


class TestAzureB2CMode:
    """Tests for AC2: Azure B2C mode (stub for Story 0.5.8)."""

    def test_azure_b2c_not_implemented(self) -> None:
        """Given azure-b2c provider, NotImplementedError is raised."""
        app = FastAPI()

        def get_test_settings() -> Settings:
            return Settings(
                auth_provider="azure-b2c",
                app_env="development",
            )

        app.dependency_overrides[get_settings] = get_test_settings

        @app.get("/test")
        async def test_endpoint(user: TokenClaims = Depends(get_current_user)):
            return {"sub": user.sub}

        # Create a token (it won't be validated correctly, but we test the path)
        token = create_mock_jwt_token(MOCK_USERS["factory_manager"])

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test", headers=auth_headers(token))

        # Should fail with 500 due to NotImplementedError
        assert response.status_code == 500


# =============================================================================
# AuthErrorCode Tests
# =============================================================================


class TestAuthErrorCode:
    """Tests for AuthErrorCode enum."""

    def test_error_codes_are_strings(self) -> None:
        """Error codes are string values."""
        assert AuthErrorCode.TOKEN_EXPIRED.value == "token_expired"
        assert AuthErrorCode.TOKEN_INVALID.value == "invalid_token"
        assert AuthErrorCode.TOKEN_MISSING.value == "missing_token"
        assert AuthErrorCode.INSUFFICIENT_PERMISSIONS.value == "insufficient_permissions"
        assert AuthErrorCode.FACTORY_ACCESS_DENIED.value == "factory_access_denied"
        assert AuthErrorCode.REGULATOR_RESTRICTED.value == "regulator_restricted"
