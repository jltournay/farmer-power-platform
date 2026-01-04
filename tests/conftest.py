"""
Farmer Power Platform - Root Test Configuration

This conftest.py provides core fixtures for all tests across the platform.
It follows the test design document and architecture patterns defined in:
- _bmad-output/test-design-system-level.md
- _bmad-output/project-context.md

Usage:
    pytest tests/                           # Run all tests
    pytest tests/unit/                      # Run unit tests only
    pytest tests/golden/                    # Run golden sample tests
    pytest tests/ -m "not slow"             # Skip slow tests
    pytest tests/ --cov=src                 # With coverage
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════
# PYTEST CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark as integration test")
    config.addinivalue_line("markers", "golden: mark as golden sample test")
    config.addinivalue_line("markers", "contract: mark as contract test")
    config.addinivalue_line("markers", "unit: mark as unit test")
    config.addinivalue_line("markers", "mongodb: mark test as requiring real MongoDB connection")


# ═══════════════════════════════════════════════════════════════════════════════
# ASYNC EVENT LOOP FIXTURE
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create a session-scoped event loop for async tests.

    This fixture is required for pytest-asyncio to work correctly with
    session-scoped async fixtures.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DAPR CLIENT MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class MockDaprClient:
    """Mock DAPR client for testing service invocation and pub/sub."""

    def __init__(self) -> None:
        self.published_events: list[dict[str, Any]] = []
        self.invoked_methods: list[dict[str, Any]] = []
        self._method_responses: dict[str, Any] = {}
        self._state_store: dict[str, Any] = {}

    async def invoke_method(
        self,
        app_id: str,
        method_name: str,
        data: dict[str, Any] | None = None,
        http_verb: str = "POST",
    ) -> dict[str, Any]:
        """Mock service invocation via DAPR."""
        invocation = {
            "app_id": app_id,
            "method_name": method_name,
            "data": data,
            "http_verb": http_verb,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.invoked_methods.append(invocation)

        # Return configured response or empty dict
        key = f"{app_id}:{method_name}"
        return self._method_responses.get(key, {})

    async def publish_event(
        self,
        pubsub_name: str,
        topic_name: str,
        data: dict[str, Any],
        data_content_type: str = "application/json",
    ) -> None:
        """Mock event publishing via DAPR Pub/Sub."""
        event = {
            "pubsub_name": pubsub_name,
            "topic_name": topic_name,
            "data": data,
            "data_content_type": data_content_type,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.published_events.append(event)

    async def save_state(
        self,
        store_name: str,
        key: str,
        value: Any,
    ) -> None:
        """Mock state store save."""
        self._state_store[f"{store_name}:{key}"] = value

    async def get_state(
        self,
        store_name: str,
        key: str,
    ) -> Any | None:
        """Mock state store get."""
        return self._state_store.get(f"{store_name}:{key}")

    def configure_response(
        self,
        app_id: str,
        method_name: str,
        response: dict[str, Any],
    ) -> None:
        """Configure a mock response for a specific method invocation."""
        key = f"{app_id}:{method_name}"
        self._method_responses[key] = response

    def reset(self) -> None:
        """Reset all recorded invocations and events."""
        self.published_events.clear()
        self.invoked_methods.clear()
        self._method_responses.clear()
        self._state_store.clear()

    def get_published_events(self, topic: str | None = None) -> list[dict[str, Any]]:
        """Get published events, optionally filtered by topic."""
        if topic:
            return [e for e in self.published_events if e["topic_name"] == topic]
        return self.published_events

    def get_invocations(self, app_id: str | None = None) -> list[dict[str, Any]]:
        """Get method invocations, optionally filtered by app_id."""
        if app_id:
            return [i for i in self.invoked_methods if i["app_id"] == app_id]
        return self.invoked_methods


@pytest.fixture
def mock_dapr_client() -> MockDaprClient:
    """
    Provide a mock DAPR client for testing.

    Usage:
        def test_event_publishing(mock_dapr_client):
            # Configure expected responses
            mock_dapr_client.configure_response(
                "plantation-model", "get_farmer", {"id": "F-001", "name": "Test Farmer"}
            )

            # ... run test code ...

            # Assert on published events
            events = mock_dapr_client.get_published_events("collection.document.received")
            assert len(events) == 1
    """
    return MockDaprClient()


# ═══════════════════════════════════════════════════════════════════════════════
# LLM / OPENROUTER MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class LLMResponse(BaseModel):
    """Pydantic model for LLM response structure."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str = "stop"


class MockLLMClient:
    """
    Mock LLM client with record/replay capability for OpenRouter.

    Supports:
    - Recording real LLM responses for golden sample creation
    - Replaying recorded responses for deterministic tests
    - Custom response configuration for specific prompts
    """

    def __init__(self, fixtures_path: Path | None = None) -> None:
        self.fixtures_path = fixtures_path or Path("tests/fixtures/llm_responses")
        self._responses: dict[str, LLMResponse] = {}
        self._calls: list[dict[str, Any]] = []
        self._record_mode: bool = False
        self._default_response: LLMResponse | None = None

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2000,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        """Mock chat completion API call."""
        call = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._calls.append(call)

        # Generate cache key from messages
        cache_key = self._generate_cache_key(messages)

        # Check for configured response
        if cache_key in self._responses:
            return self._responses[cache_key]

        # Check for recorded response in fixtures
        recorded = self._load_recorded_response(cache_key, model)
        if recorded:
            return recorded

        # Return default response if configured
        if self._default_response:
            return self._default_response

        # Fallback: return empty response
        return LLMResponse(
            content="{}",
            model=model,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

    def configure_response(
        self,
        messages: list[dict[str, str]],
        response: str | dict[str, Any],
        model: str = "anthropic/claude-3-haiku",
    ) -> None:
        """Configure a specific response for given messages."""
        cache_key = self._generate_cache_key(messages)
        content = json.dumps(response) if isinstance(response, dict) else response
        self._responses[cache_key] = LLMResponse(
            content=content,
            model=model,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

    def set_default_response(self, response: str | dict[str, Any], model: str = "anthropic/claude-3-haiku") -> None:
        """Set default response when no match is found."""
        content = json.dumps(response) if isinstance(response, dict) else response
        self._default_response = LLMResponse(
            content=content,
            model=model,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

    def get_calls(self, model: str | None = None) -> list[dict[str, Any]]:
        """Get all LLM calls, optionally filtered by model."""
        if model:
            return [c for c in self._calls if c["model"] == model]
        return self._calls

    def reset(self) -> None:
        """Reset all configured responses and recorded calls."""
        self._responses.clear()
        self._calls.clear()
        self._default_response = None

    def _generate_cache_key(self, messages: list[dict[str, str]]) -> str:
        """Generate a deterministic cache key from messages."""
        # Use hash of serialized messages as key
        serialized = json.dumps(messages, sort_keys=True)
        return str(hash(serialized))

    def _load_recorded_response(self, cache_key: str, model: str) -> LLMResponse | None:
        """Load recorded response from fixtures if available."""
        fixture_file = self.fixtures_path / f"{cache_key}.json"
        if fixture_file.exists():
            data = json.loads(fixture_file.read_text())
            return LLMResponse(**data)
        return None


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """
    Provide a mock LLM client for testing.

    Usage:
        def test_extraction(mock_llm_client):
            # Configure expected LLM response
            mock_llm_client.set_default_response({
                "farmer_id": "WM-4521",
                "grade": "B",
                "quality_score": 78
            })

            # ... run test code ...

            # Verify LLM was called
            calls = mock_llm_client.get_calls()
            assert len(calls) == 1
    """
    return MockLLMClient()


@pytest.fixture
def mock_openrouter(mock_llm_client: MockLLMClient) -> MockLLMClient:
    """Alias for mock_llm_client - matches architecture naming."""
    return mock_llm_client


# ═══════════════════════════════════════════════════════════════════════════════
# MONGODB MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class MockMongoCollection:
    """Mock MongoDB collection for testing."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._documents: dict[str, dict[str, Any]] = {}
        self._id_counter: int = 0

    async def insert_one(self, document: dict[str, Any]) -> MagicMock:
        """Mock insert_one operation."""
        if "_id" not in document:
            self._id_counter += 1
            document["_id"] = f"mock_id_{self._id_counter}"
        self._documents[str(document["_id"])] = document.copy()
        result = MagicMock()
        result.inserted_id = document["_id"]
        return result

    async def insert_many(self, documents: list[dict[str, Any]]) -> MagicMock:
        """Mock insert_many operation."""
        inserted_ids = []
        for doc in documents:
            result = await self.insert_one(doc)
            inserted_ids.append(result.inserted_id)
        result = MagicMock()
        result.inserted_ids = inserted_ids
        return result

    def _match_filter(self, doc: dict[str, Any], filter: dict[str, Any]) -> bool:
        """Check if document matches filter including operators."""
        for key, value in filter.items():
            if isinstance(value, dict):
                # Handle MongoDB operators
                for op, op_value in value.items():
                    if op == "$ne":
                        if doc.get(key) == op_value:
                            return False
                    elif op == "$gt":
                        if not doc.get(key, "") > op_value:
                            return False
                    elif op == "$gte":
                        if not doc.get(key, "") >= op_value:
                            return False
                    elif op == "$lt":
                        if not doc.get(key, "") < op_value:
                            return False
                    elif op == "$lte":
                        if not doc.get(key, "") <= op_value:
                            return False
                    elif op == "$in" and doc.get(key) not in op_value:
                        return False
            else:
                if doc.get(key) != value:
                    return False
        return True

    async def find_one(self, filter: dict[str, Any]) -> dict[str, Any] | None:
        """Mock find_one operation."""
        for doc in self._documents.values():
            if self._match_filter(doc, filter):
                return doc.copy()
        return None

    def find(self, filter: dict[str, Any]) -> MockMongoCursor:
        """Mock find operation returning cursor (sync, like Motor's find)."""
        matching = [doc.copy() for doc in self._documents.values() if self._match_filter(doc, filter)]
        return MockMongoCursor(matching)

    async def find_one_and_update(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        return_document: bool = False,
    ) -> dict[str, Any] | None:
        """Mock find_one_and_update operation."""
        for _doc_id, doc in self._documents.items():
            if self._match_filter(doc, filter):
                if "$set" in update:
                    # Handle nested key updates like "metadata.updated_at"
                    for key, value in update["$set"].items():
                        if "." in key:
                            # Handle dotted notation
                            parts = key.split(".")
                            current = doc
                            for part in parts[:-1]:
                                if part not in current:
                                    current[part] = {}
                                current = current[part]
                            current[parts[-1]] = value
                        else:
                            doc[key] = value
                if return_document:
                    return doc.copy()
                return doc.copy()
        return None

    async def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> MagicMock:
        """Mock update_one operation."""
        for _doc_id, doc in self._documents.items():
            if all(doc.get(k) == v for k, v in filter.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                result = MagicMock()
                result.matched_count = 1
                result.modified_count = 1
                return result

        if upsert:
            new_doc = {**filter, **update.get("$set", {})}
            await self.insert_one(new_doc)
            result = MagicMock()
            result.matched_count = 0
            result.modified_count = 0
            result.upserted_id = new_doc["_id"]
            return result

        result = MagicMock()
        result.matched_count = 0
        result.modified_count = 0
        return result

    async def delete_one(self, filter: dict[str, Any]) -> MagicMock:
        """Mock delete_one operation."""
        for doc_id, doc in list(self._documents.items()):
            if all(doc.get(k) == v for k, v in filter.items()):
                del self._documents[doc_id]
                result = MagicMock()
                result.deleted_count = 1
                return result
        result = MagicMock()
        result.deleted_count = 0
        return result

    async def count_documents(self, filter: dict[str, Any]) -> int:
        """Mock count_documents operation."""
        return sum(1 for doc in self._documents.values() if self._match_filter(doc, filter))

    async def create_index(
        self,
        keys: Any,
        unique: bool = False,
        name: str | None = None,
    ) -> str:
        """Mock create_index operation."""
        # Just return a mock index name - we don't actually create indexes in tests
        return name or f"mock_index_{len(self._documents)}"

    def reset(self) -> None:
        """Clear all documents."""
        self._documents.clear()
        self._id_counter = 0


class MockMongoCursor:
    """Mock MongoDB cursor for iteration."""

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents
        self._index = 0

    def __aiter__(self) -> MockMongoCursor:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._documents):
            raise StopAsyncIteration
        doc = self._documents[self._index]
        self._index += 1
        return doc

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        """Convert cursor to list."""
        if length:
            return self._documents[:length]
        return self._documents

    def skip(self, n: int) -> MockMongoCursor:
        """Skip n documents."""
        return MockMongoCursor(self._documents[n:])

    def limit(self, n: int) -> MockMongoCursor:
        """Limit to n documents."""
        return MockMongoCursor(self._documents[:n])

    def sort(self, key_or_list: Any, direction: int = 1) -> MockMongoCursor:
        """Mock sort - returns self for chaining."""
        return self


class MockMongoDatabase:
    """Mock MongoDB database for testing."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._collections: dict[str, MockMongoCollection] = {}

    def __getitem__(self, collection_name: str) -> MockMongoCollection:
        """Get collection by name."""
        if collection_name not in self._collections:
            self._collections[collection_name] = MockMongoCollection(collection_name)
        return self._collections[collection_name]

    def get_collection(self, name: str) -> MockMongoCollection:
        """Get collection by name."""
        return self[name]

    def reset(self) -> None:
        """Reset all collections."""
        for collection in self._collections.values():
            collection.reset()


class MockMongoClient:
    """Mock MongoDB client for testing."""

    def __init__(self) -> None:
        self._databases: dict[str, MockMongoDatabase] = {}

    def __getitem__(self, database_name: str) -> MockMongoDatabase:
        """Get database by name."""
        if database_name not in self._databases:
            self._databases[database_name] = MockMongoDatabase(database_name)
        return self._databases[database_name]

    def get_database(self, name: str) -> MockMongoDatabase:
        """Get database by name."""
        return self[name]

    def reset(self) -> None:
        """Reset all databases."""
        for db in self._databases.values():
            db.reset()


@pytest.fixture
def mock_mongodb_client() -> MockMongoClient:
    """
    Provide a mock MongoDB client for testing.

    Usage:
        async def test_farmer_storage(mock_mongodb_client):
            db = mock_mongodb_client["plantation_model"]
            farmers = db["farmers"]

            await farmers.insert_one({"farmer_id": "F-001", "name": "Test"})

            result = await farmers.find_one({"farmer_id": "F-001"})
            assert result["name"] == "Test"
    """
    return MockMongoClient()


@pytest.fixture
async def mongodb_test_client(mock_mongodb_client: MockMongoClient) -> AsyncGenerator[MockMongoClient, None]:
    """
    Async fixture that provides and cleans up MongoDB client.

    Use this for tests that need database cleanup after each test.
    """
    yield mock_mongodb_client
    mock_mongodb_client.reset()


# ═══════════════════════════════════════════════════════════════════════════════
# MCP CLIENT MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class MockMCPClient:
    """Mock MCP client for testing tool invocations."""

    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self._tool_responses: dict[str, Any] = {}
        self._tool_calls: list[dict[str, Any]] = []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Mock MCP tool call."""
        call = {
            "server": self.server_name,
            "tool": tool_name,
            "arguments": arguments,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._tool_calls.append(call)

        # Return configured response or empty dict
        return self._tool_responses.get(tool_name, {})

    def configure_tool_response(self, tool_name: str, response: dict[str, Any]) -> None:
        """Configure response for a specific tool."""
        self._tool_responses[tool_name] = response

    def get_tool_calls(self, tool_name: str | None = None) -> list[dict[str, Any]]:
        """Get tool calls, optionally filtered by tool name."""
        if tool_name:
            return [c for c in self._tool_calls if c["tool"] == tool_name]
        return self._tool_calls

    def reset(self) -> None:
        """Reset all configured responses and recorded calls."""
        self._tool_responses.clear()
        self._tool_calls.clear()


@pytest.fixture
def mock_collection_mcp() -> MockMCPClient:
    """Mock Collection Model MCP client."""
    return MockMCPClient("collection-mcp")


@pytest.fixture
def mock_plantation_mcp() -> MockMCPClient:
    """Mock Plantation Model MCP client."""
    return MockMCPClient("plantation-mcp")


@pytest.fixture
def mock_knowledge_mcp() -> MockMCPClient:
    """Mock Knowledge Model MCP client."""
    return MockMCPClient("knowledge-mcp")


# ═══════════════════════════════════════════════════════════════════════════════
# EXTERNAL API MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class MockExternalAPIClient:
    """Base class for external API mocks."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._responses: dict[str, Any] = {}
        self._requests: list[dict[str, Any]] = []

    async def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Mock HTTP request."""
        request = {
            "method": method,
            "path": path,
            "data": data,
            "headers": headers,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._requests.append(request)
        return self._responses.get(path, {"status": "success"})

    def configure_response(self, path: str, response: dict[str, Any]) -> None:
        """Configure response for a specific path."""
        self._responses[path] = response

    def get_requests(self, path: str | None = None) -> list[dict[str, Any]]:
        """Get requests, optionally filtered by path."""
        if path:
            return [r for r in self._requests if r["path"] == path]
        return self._requests

    def reset(self) -> None:
        """Reset all responses and requests."""
        self._responses.clear()
        self._requests.clear()


@pytest.fixture
def mock_starfish_api() -> MockExternalAPIClient:
    """Mock Starfish Network API client."""
    client = MockExternalAPIClient("https://api.starfish.network")
    # Configure default responses
    client.configure_response("/v1/buyers", {"buyers": []})
    client.configure_response("/v1/prices", {"prices": []})
    return client


@pytest.fixture
def mock_weather_api() -> MockExternalAPIClient:
    """Mock Weather API client."""
    client = MockExternalAPIClient("https://api.weather.service")
    # Configure default weather response
    client.configure_response(
        "/v1/forecast",
        {
            "temperature": 25.0,
            "humidity": 70,
            "rainfall_mm": 0,
            "conditions": "partly_cloudy",
        },
    )
    return client


@pytest.fixture
def mock_africas_talking_api() -> MockExternalAPIClient:
    """Mock Africa's Talking API client."""
    client = MockExternalAPIClient("https://api.africastalking.com")
    # Configure default SMS response
    client.configure_response(
        "/version1/messaging",
        {
            "SMSMessageData": {
                "Message": "Sent to 1/1 Total Cost: KES 0.80",
                "Recipients": [{"status": "Success", "messageId": "mock-123"}],
            }
        },
    )
    return client


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataFactory:
    """
    Factory for generating test data with sensible defaults.

    Follows patterns from project-context.md for farmer/factory data.
    """

    _farmer_counter: int = 0
    _factory_counter: int = 0
    _document_counter: int = 0

    @classmethod
    def create_farmer(
        cls,
        farmer_id: str | None = None,
        name: str | None = None,
        phone: str | None = None,
        region: str | None = None,
        factory_id: str | None = None,
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create a test farmer with sensible defaults."""
        cls._farmer_counter += 1
        return {
            "farmer_id": farmer_id or f"WM-{cls._farmer_counter:04d}",
            "name": name or f"Test Farmer {cls._farmer_counter}",
            "phone": phone or f"+2547{cls._farmer_counter:08d}",
            "region": region or "Kericho-High",
            "factory_id": factory_id or "FAC-001",
            "altitude_band": "high",
            "communication_preference": "sms",
            "language": "sw",
            "created_at": datetime.now(UTC).isoformat(),
            **overrides,
        }

    @classmethod
    def create_factory(
        cls,
        factory_id: str | None = None,
        name: str | None = None,
        region: str | None = None,
        grading_model_id: str | None = None,
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create a test factory with sensible defaults."""
        cls._factory_counter += 1
        return {
            "factory_id": factory_id or f"FAC-{cls._factory_counter:03d}",
            "name": name or f"Test Factory {cls._factory_counter}",
            "region": region or "Kericho",
            "grading_model_id": grading_model_id or "GM-TERNARY",
            "created_at": datetime.now(UTC).isoformat(),
            **overrides,
        }

    @classmethod
    def create_qc_event(
        cls,
        farmer_id: str | None = None,
        grade: str = "B",
        quality_score: float = 78.0,
        source: str = "qc-analyzer",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create a test QC event with sensible defaults."""
        cls._document_counter += 1
        return {
            "doc_id": f"DOC-{cls._document_counter:05d}",
            "farmer_id": farmer_id or f"WM-{cls._farmer_counter:04d}",
            "source": source,
            "event_type": "END_BAG",
            "grade": grade,
            "quality_score": quality_score,
            "timestamp": datetime.now(UTC).isoformat(),
            "validation_warnings": [],
            **overrides,
        }

    @classmethod
    def create_diagnosis(
        cls,
        farmer_id: str | None = None,
        condition: str = "tea_blister_blight",
        confidence: float = 0.85,
        severity: str = "moderate",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create a test diagnosis result."""
        return {
            "farmer_id": farmer_id or f"WM-{cls._farmer_counter:04d}",
            "diagnosis": {
                "condition": condition,
                "confidence": confidence,
                "severity": severity,
                "details": "Test diagnosis details",
            },
            "recommendations": [
                "Apply fungicide treatment",
                "Improve drainage",
            ],
            "created_at": datetime.now(UTC).isoformat(),
            **overrides,
        }

    @classmethod
    def create_action_plan(
        cls,
        farmer_id: str | None = None,
        priority: str = "high",
        **overrides: Any,
    ) -> dict[str, Any]:
        """Create a test action plan."""
        return {
            "farmer_id": farmer_id or f"WM-{cls._farmer_counter:04d}",
            "priority": priority,
            "dashboard_content": "Detailed action plan for dashboard",
            "sms_summary": "Chai yako: WATCH. Fanya hivi...",
            "voice_script": {
                "greeting": "Habari, mkulima",
                "quality_summary": "Chai yako ina hali ya wastani",
                "main_actions": ["Kagua majani", "Weka mbolea"],
                "closing": "Asante",
            },
            "created_at": datetime.now(UTC).isoformat(),
            **overrides,
        }

    @classmethod
    def reset(cls) -> None:
        """Reset all counters."""
        cls._farmer_counter = 0
        cls._factory_counter = 0
        cls._document_counter = 0


@pytest.fixture
def test_data_factory() -> type[TestDataFactory]:
    """
    Provide test data factory.

    Usage:
        def test_farmer_creation(test_data_factory):
            farmer = test_data_factory.create_farmer(name="John Kamau")
            assert farmer["name"] == "John Kamau"
            assert farmer["farmer_id"].startswith("WM-")
    """
    TestDataFactory.reset()
    return TestDataFactory


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN SAMPLE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


class GoldenSample:
    """Represents a single golden sample test case."""

    def __init__(
        self,
        input_data: dict[str, Any],
        expected_output: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        acceptable_variance: dict[str, float] | None = None,
    ) -> None:
        self.input_data = input_data
        self.expected_output = expected_output
        self.metadata = metadata or {}
        self.acceptable_variance = acceptable_variance or {}

    def validate_output(self, actual_output: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate actual output against expected with variance tolerance.

        Returns:
            Tuple of (passed, list of error messages)
        """
        errors: list[str] = []

        for key, expected_value in self.expected_output.items():
            if key not in actual_output:
                errors.append(f"Missing key: {key}")
                continue

            actual_value = actual_output[key]

            # Check if variance is allowed for this field
            if key in self.acceptable_variance:
                variance = self.acceptable_variance[key]
                if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                    if abs(expected_value - actual_value) > variance:
                        errors.append(f"Key '{key}': expected {expected_value} (+/- {variance}), got {actual_value}")
                    continue

            # Exact match required
            if expected_value != actual_value:
                errors.append(f"Key '{key}': expected {expected_value}, got {actual_value}")

        return len(errors) == 0, errors


class GoldenSampleLoader:
    """Loader for golden sample test cases."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or Path("tests/golden")

    def load_samples(self, agent_name: str) -> list[GoldenSample]:
        """Load all golden samples for an agent."""
        samples_file = self.base_path / agent_name / "samples.json"
        if not samples_file.exists():
            return []

        data = json.loads(samples_file.read_text())
        return [
            GoldenSample(
                input_data=sample["input"],
                expected_output=sample["expected_output"],
                metadata=sample.get("metadata", {}),
                acceptable_variance=sample.get("acceptable_variance", {}),
            )
            for sample in data.get("samples", [])
        ]

    def save_sample(
        self,
        agent_name: str,
        sample: GoldenSample,
    ) -> None:
        """Save a golden sample to the fixtures directory."""
        samples_dir = self.base_path / agent_name
        samples_dir.mkdir(parents=True, exist_ok=True)

        samples_file = samples_dir / "samples.json"

        # Load existing samples
        if samples_file.exists():
            data = json.loads(samples_file.read_text())
        else:
            data = {"samples": [], "metadata": {"agent": agent_name, "created_at": datetime.now(UTC).isoformat()}}

        # Add new sample
        data["samples"].append(
            {
                "input": sample.input_data,
                "expected_output": sample.expected_output,
                "metadata": sample.metadata,
                "acceptable_variance": sample.acceptable_variance,
            }
        )

        samples_file.write_text(json.dumps(data, indent=2))


@pytest.fixture
def golden_sample_loader() -> GoldenSampleLoader:
    """
    Provide golden sample loader for tests.

    Usage:
        @pytest.mark.golden
        def test_extractor_accuracy(golden_sample_loader, mock_llm_client):
            samples = golden_sample_loader.load_samples("qc_event_extractor")

            for sample in samples:
                # Configure LLM with expected response for this sample
                mock_llm_client.set_default_response(sample.expected_output)

                # Run extraction
                result = await extract_qc_event(sample.input_data)

                # Validate
                passed, errors = sample.validate_output(result)
                assert passed, f"Golden sample failed: {errors}"
    """
    return GoldenSampleLoader()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_fixtures_path(tmp_path: Path) -> Path:
    """Provide temporary directory for test fixtures."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    return fixtures


@pytest.fixture
def sample_qc_payload() -> dict[str, Any]:
    """Sample QC analyzer payload for testing."""
    return {
        "source": "qc-analyzer",
        "event_type": "END_BAG",
        "timestamp": "2024-12-23T10:30:00Z",
        "farmer_id": "WM-4521",
        "raw_data": {
            "leaf_count": 150,
            "moisture_percent": 72.5,
            "defects": ["yellow_leaves", "insect_damage"],
            "grade": "B",
        },
        "image_url": "https://storage.example.com/images/bag-12345.jpg",
    }


@pytest.fixture
def sample_farmer() -> dict[str, Any]:
    """Sample farmer data for testing."""
    return {
        "farmer_id": "WM-4521",
        "name": "James Kipchoge",
        "phone": "+254712345678",
        "region": "Kericho-High",
        "factory_id": "FAC-001",
        "altitude_band": "high",
        "communication_preference": "sms",
        "language": "sw",
        "is_lead_farmer": False,
        "performance_summary": {
            "quality_score_avg": 75.5,
            "primary_percentage": 82.0,
            "trend": "stable",
            "last_updated": "2024-12-22T00:00:00Z",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def cleanup_test_data(
    request: pytest.FixtureRequest,
    test_data_factory: type[TestDataFactory],
) -> Generator[None, None, None]:
    """Automatically clean up test data after each test."""
    yield
    test_data_factory.reset()
