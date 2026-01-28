"""Tests for AI Agent Config admin routes (Story 9.12b).

Tests route layer: HTTP status codes, auth, query params, error handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from bff.api.middleware.auth import get_current_user
from bff.api.routes.admin.ai_agents import get_agent_config_client
from bff.api.schemas import PaginatedResponse
from bff.api.schemas.auth import TokenClaims
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fp_common.models import AgentConfigDetail, AgentConfigSummary, PromptSummary

# Build test app with dependency overrides
app = FastAPI()

# Import and register the router (must come after app creation)
from bff.api.routes.admin.ai_agents import router  # noqa: E402

app.include_router(router, prefix="/api/admin")


def _mock_admin_user() -> TokenClaims:
    """Create a mock platform admin TokenClaims."""
    return TokenClaims(
        sub="admin-user",
        email="admin@farmerpower.test",
        name="Test Admin",
        role="platform_admin",
        factory_id=None,
    )


def _mock_non_admin_user() -> TokenClaims:
    """Create a mock factory_manager TokenClaims."""
    return TokenClaims(
        sub="manager-user",
        email="manager@factory.test",
        name="Test Manager",
        role="factory_manager",
        factory_id="FAC-001",
    )


# Override auth dependency to bypass JWT validation
app.dependency_overrides[get_current_user] = _mock_admin_user

# Mock client instance shared across tests
_mock_client = AsyncMock()


def _get_mock_client() -> AsyncMock:
    """Dependency override for AgentConfigClient in tests."""
    return _mock_client


app.dependency_overrides[get_agent_config_client] = _get_mock_client

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mock_client():
    """Reset mock client before each test."""
    _mock_client.reset_mock()
    # Clear side_effect to prevent lingering error states
    _mock_client.list_agent_configs.side_effect = None
    _mock_client.get_agent_config.side_effect = None
    _mock_client.list_prompts_by_agent.side_effect = None
    yield


def create_agent_config_summary(
    agent_id: str = "disease-diagnosis",
    version: str = "1.0.0",
    agent_type: str = "explorer",
    status: str = "active",
) -> AgentConfigSummary:
    """Create an AgentConfigSummary domain model for testing."""
    return AgentConfigSummary(
        agent_id=agent_id,
        version=version,
        agent_type=agent_type,
        status=status,
        description="Test agent description",
        model="claude-3-5-sonnet",
        prompt_count=2,
        updated_at=datetime.now(UTC),
    )


def create_prompt_summary(
    id: str = "disease-diagnosis:1.0.0",
    prompt_id: str = "disease-diagnosis",
    agent_id: str = "disease-diagnosis",
    version: str = "1.0.0",
    status: str = "active",
) -> PromptSummary:
    """Create a PromptSummary domain model for testing."""
    return PromptSummary(
        id=id,
        prompt_id=prompt_id,
        agent_id=agent_id,
        version=version,
        status=status,
        author="admin",
        updated_at=datetime.now(UTC),
    )


def create_agent_config_detail(
    agent_id: str = "disease-diagnosis",
    version: str = "1.0.0",
) -> AgentConfigDetail:
    """Create an AgentConfigDetail domain model for testing."""
    return AgentConfigDetail(
        agent_id=agent_id,
        version=version,
        agent_type="explorer",
        status="active",
        description="Test agent description",
        model="claude-3-5-sonnet",
        prompt_count=2,
        config_json='{"agent_id": "disease-diagnosis", "type": "explorer"}',
        prompts=[
            create_prompt_summary(),
            create_prompt_summary(id="prompt-2:1.0.0", prompt_id="prompt-2"),
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestListAiAgentsRoute:
    """Tests for GET /api/admin/ai-agents."""

    def test_success(self):
        """Test successful agent config listing."""
        _mock_client.list_agent_configs.return_value = PaginatedResponse.from_client_response(
            items=[
                create_agent_config_summary(agent_id="agent-001"),
                create_agent_config_summary(agent_id="agent-002"),
            ],
            total_count=2,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/ai-agents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["agent_id"] == "agent-001"
        assert data["data"][1]["agent_id"] == "agent-002"
        assert data["pagination"]["total_count"] == 2

    def test_with_pagination(self):
        """Test agent config listing with pagination parameters."""
        _mock_client.list_agent_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_agent_config_summary()],
            total_count=100,
            page_size=10,
            next_page_token="next-token",
        )

        response = client.get("/api/admin/ai-agents?page_size=10&page_token=prev-token")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 10
        assert data["pagination"]["next_page_token"] == "next-token"
        _mock_client.list_agent_configs.assert_called_once_with(
            page_size=10,
            page_token="prev-token",
            agent_type=None,
            status=None,
        )

    def test_with_agent_type_filter(self):
        """Test agent config listing with agent_type filter."""
        _mock_client.list_agent_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_agent_config_summary(agent_type="explorer")],
            total_count=1,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/ai-agents?agent_type=explorer")

        assert response.status_code == 200
        _mock_client.list_agent_configs.assert_called_once_with(
            page_size=20,
            page_token=None,
            agent_type="explorer",
            status=None,
        )

    def test_with_status_filter(self):
        """Test agent config listing with status filter."""
        _mock_client.list_agent_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_agent_config_summary(status="active")],
            total_count=1,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/ai-agents?status=active")

        assert response.status_code == 200
        _mock_client.list_agent_configs.assert_called_once_with(
            page_size=20,
            page_token=None,
            agent_type=None,
            status="active",
        )

    def test_page_size_validation(self):
        """Test page_size validation (max 100)."""
        response = client.get("/api/admin/ai-agents?page_size=200")
        # FastAPI validates Query constraints
        assert response.status_code == 422

    def test_service_unavailable(self):
        """Test 503 when AI Model is unavailable."""
        _mock_client.list_agent_configs.side_effect = ServiceUnavailableError("AI Model unavailable")

        response = client.get("/api/admin/ai-agents")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "service_unavailable"

    def test_empty_result(self):
        """Test successful empty result."""
        _mock_client.list_agent_configs.return_value = PaginatedResponse.from_client_response(
            items=[],
            total_count=0,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/ai-agents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
        assert data["pagination"]["total_count"] == 0


class TestGetAiAgentRoute:
    """Tests for GET /api/admin/ai-agents/{agent_id}."""

    def test_success(self):
        """Test successful agent config detail retrieval."""
        _mock_client.get_agent_config.return_value = create_agent_config_detail(
            agent_id="disease-diagnosis",
        )

        response = client.get("/api/admin/ai-agents/disease-diagnosis")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "disease-diagnosis"
        assert data["agent_type"] == "explorer"
        assert "config_json" in data
        assert "prompts" in data
        assert len(data["prompts"]) == 2

    def test_not_found(self):
        """Test 404 when agent config not found."""
        _mock_client.get_agent_config.side_effect = NotFoundError("Agent config not found")

        response = client.get("/api/admin/ai-agents/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "AGENT_CONFIG_NOT_FOUND"
        assert "nonexistent" in data["detail"]["message"]

    def test_service_unavailable(self):
        """Test 503 when AI Model is unavailable."""
        _mock_client.get_agent_config.side_effect = ServiceUnavailableError("AI Model unavailable")

        response = client.get("/api/admin/ai-agents/disease-diagnosis")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "service_unavailable"

    def test_with_special_characters_in_id(self):
        """Test agent_id with special characters."""
        _mock_client.get_agent_config.return_value = create_agent_config_detail(
            agent_id="agent-with-dashes-v2",
        )

        response = client.get("/api/admin/ai-agents/agent-with-dashes-v2")

        assert response.status_code == 200
        _mock_client.get_agent_config.assert_called_once_with("agent-with-dashes-v2")


class TestListPromptsByAgentRoute:
    """Tests for GET /api/admin/ai-agents/{agent_id}/prompts."""

    def test_success(self):
        """Test successful prompt listing."""
        _mock_client.list_prompts_by_agent.return_value = [
            create_prompt_summary(id="prompt-001:1.0.0", prompt_id="prompt-001"),
            create_prompt_summary(id="prompt-002:1.0.0", prompt_id="prompt-002"),
        ]

        response = client.get("/api/admin/ai-agents/disease-diagnosis/prompts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["prompt_id"] == "prompt-001"
        assert data["data"][1]["prompt_id"] == "prompt-002"
        assert data["total_count"] == 2

    def test_with_status_filter(self):
        """Test prompt listing with status filter."""
        _mock_client.list_prompts_by_agent.return_value = [
            create_prompt_summary(status="active"),
        ]

        response = client.get("/api/admin/ai-agents/disease-diagnosis/prompts?status=active")

        assert response.status_code == 200
        _mock_client.list_prompts_by_agent.assert_called_once_with("disease-diagnosis", status="active")

    def test_agent_not_found(self):
        """Test 404 when agent not found."""
        _mock_client.list_prompts_by_agent.side_effect = NotFoundError("Agent not found")

        response = client.get("/api/admin/ai-agents/nonexistent/prompts")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "AGENT_NOT_FOUND"
        assert "nonexistent" in data["detail"]["message"]

    def test_service_unavailable(self):
        """Test 503 when AI Model is unavailable."""
        _mock_client.list_prompts_by_agent.side_effect = ServiceUnavailableError("AI Model unavailable")

        response = client.get("/api/admin/ai-agents/disease-diagnosis/prompts")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "service_unavailable"

    def test_empty_result(self):
        """Test successful empty result."""
        _mock_client.list_prompts_by_agent.return_value = []

        response = client.get("/api/admin/ai-agents/disease-diagnosis/prompts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
        assert data["total_count"] == 0


class TestAuthRequirement:
    """Tests for authentication requirement on all routes."""

    def test_list_requires_platform_admin(self):
        """Test list endpoint requires platform_admin role."""
        # Override to use non-admin user
        app.dependency_overrides[get_current_user] = _mock_non_admin_user

        response = client.get("/api/admin/ai-agents")

        # Should get 403 Forbidden
        assert response.status_code == 403

        # Restore admin user
        app.dependency_overrides[get_current_user] = _mock_admin_user

    def test_get_requires_platform_admin(self):
        """Test get endpoint requires platform_admin role."""
        # Override to use non-admin user
        app.dependency_overrides[get_current_user] = _mock_non_admin_user

        response = client.get("/api/admin/ai-agents/disease-diagnosis")

        # Should get 403 Forbidden
        assert response.status_code == 403

        # Restore admin user
        app.dependency_overrides[get_current_user] = _mock_admin_user

    def test_list_prompts_requires_platform_admin(self):
        """Test list prompts endpoint requires platform_admin role."""
        # Override to use non-admin user
        app.dependency_overrides[get_current_user] = _mock_non_admin_user

        response = client.get("/api/admin/ai-agents/disease-diagnosis/prompts")

        # Should get 403 Forbidden
        assert response.status_code == 403

        # Restore admin user
        app.dependency_overrides[get_current_user] = _mock_admin_user


class TestResponseFormat:
    """Tests for response format compliance."""

    def test_list_response_format(self):
        """Test list response follows AgentConfigListResponse schema."""
        _mock_client.list_agent_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_agent_config_summary()],
            total_count=1,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/ai-agents")

        assert response.status_code == 200
        data = response.json()
        # Check required fields
        assert "data" in data
        assert "pagination" in data
        # Check data item fields
        item = data["data"][0]
        assert "agent_id" in item
        assert "version" in item
        assert "agent_type" in item
        assert "status" in item
        assert "description" in item
        assert "model" in item
        assert "prompt_count" in item
        # Pagination fields
        assert "page_size" in data["pagination"]
        assert "total_count" in data["pagination"]

    def test_detail_response_format(self):
        """Test detail response follows AgentConfigDetailResponse schema."""
        _mock_client.get_agent_config.return_value = create_agent_config_detail()

        response = client.get("/api/admin/ai-agents/disease-diagnosis")

        assert response.status_code == 200
        data = response.json()
        # Check required fields
        assert "agent_id" in data
        assert "version" in data
        assert "agent_type" in data
        assert "status" in data
        assert "config_json" in data
        assert "prompts" in data
        # Detail-specific fields
        assert "created_at" in data
        assert "updated_at" in data
        # Check prompt fields
        prompt = data["prompts"][0]
        assert "id" in prompt
        assert "prompt_id" in prompt
        assert "agent_id" in prompt
        assert "version" in prompt
        assert "status" in prompt
        assert "author" in prompt

    def test_prompts_response_format(self):
        """Test prompts response follows PromptListResponse schema."""
        _mock_client.list_prompts_by_agent.return_value = [create_prompt_summary()]

        response = client.get("/api/admin/ai-agents/disease-diagnosis/prompts")

        assert response.status_code == 200
        data = response.json()
        # Check required fields
        assert "data" in data
        assert "total_count" in data
        # Check prompt fields
        prompt = data["data"][0]
        assert "id" in prompt
        assert "prompt_id" in prompt
        assert "agent_id" in prompt
        assert "version" in prompt
        assert "status" in prompt
        assert "author" in prompt

    def test_timestamps_are_iso_format(self):
        """Test timestamp fields are ISO format strings."""
        _mock_client.get_agent_config.return_value = create_agent_config_detail()

        response = client.get("/api/admin/ai-agents/disease-diagnosis")

        assert response.status_code == 200
        data = response.json()
        # Should be ISO format strings like "2026-01-25T12:00:00"
        assert data["created_at"] is None or "T" in data["created_at"]
        assert data["updated_at"] is None or "T" in data["updated_at"]
