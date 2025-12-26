"""Example Unit Tests for Collection Model

This file demonstrates how to use the test fixtures defined in conftest.py.
Delete or modify this file when implementing actual tests.

Run with:
    pytest tests/unit/collection/test_example.py -v
"""

from __future__ import annotations

import pytest

from tests.conftest import MockDaprClient, MockLLMClient, MockMongoClient, TestDataFactory

# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: USING TEST DATA FACTORY
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataFactoryUsage:
    """Examples of using the TestDataFactory fixture."""

    def test_create_farmer_with_defaults(self, test_data_factory: type[TestDataFactory]) -> None:
        """Factory creates farmer with sensible defaults."""
        farmer = test_data_factory.create_farmer()

        assert farmer["farmer_id"].startswith("WM-")
        assert farmer["region"] == "Kericho-High"
        assert farmer["communication_preference"] == "sms"
        assert farmer["language"] == "sw"

    def test_create_farmer_with_overrides(self, test_data_factory: type[TestDataFactory]) -> None:
        """Factory allows overriding specific fields."""
        farmer = test_data_factory.create_farmer(
            name="John Kamau",
            region="Nandi-Medium",
            language="en",
        )

        assert farmer["name"] == "John Kamau"
        assert farmer["region"] == "Nandi-Medium"
        assert farmer["language"] == "en"
        # Defaults still applied for non-overridden fields
        assert farmer["farmer_id"].startswith("WM-")

    def test_create_qc_event(self, test_data_factory: type[TestDataFactory]) -> None:
        """Factory creates QC event with quality data."""
        event = test_data_factory.create_qc_event(
            grade="B",
            quality_score=78.0,
        )

        assert event["doc_id"].startswith("DOC-")
        assert event["grade"] == "B"
        assert event["quality_score"] == 78.0
        assert event["event_type"] == "END_BAG"


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: USING MOCK DAPR CLIENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestDaprClientUsage:
    """Examples of using the MockDaprClient fixture."""

    @pytest.mark.asyncio
    async def test_publish_event(self, mock_dapr_client: MockDaprClient) -> None:
        """Test publishing events via DAPR."""
        # Simulate publishing an event
        await mock_dapr_client.publish_event(
            pubsub_name="pubsub",
            topic_name="collection.document.received",
            data={"doc_id": "DOC-00001", "farmer_id": "WM-4521"},
        )

        # Verify event was published
        events = mock_dapr_client.get_published_events("collection.document.received")
        assert len(events) == 1
        assert events[0]["data"]["doc_id"] == "DOC-00001"

    @pytest.mark.asyncio
    async def test_service_invocation(self, mock_dapr_client: MockDaprClient) -> None:
        """Test invoking other services via DAPR."""
        # Configure expected response
        mock_dapr_client.configure_response(
            app_id="plantation-model",
            method_name="get_farmer",
            response={"farmer_id": "WM-4521", "name": "James Kipchoge"},
        )

        # Invoke the service
        result = await mock_dapr_client.invoke_method(
            app_id="plantation-model",
            method_name="get_farmer",
            data={"farmer_id": "WM-4521"},
        )

        # Verify response
        assert result["farmer_id"] == "WM-4521"
        assert result["name"] == "James Kipchoge"

        # Verify invocation was recorded
        invocations = mock_dapr_client.get_invocations("plantation-model")
        assert len(invocations) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: USING MOCK LLM CLIENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestLLMClientUsage:
    """Examples of using the MockLLMClient fixture."""

    @pytest.mark.asyncio
    async def test_llm_extraction(self, mock_llm_client: MockLLMClient) -> None:
        """Test LLM-based extraction with mock responses."""
        # Configure expected LLM response
        mock_llm_client.set_default_response(
            response={
                "farmer_id": "WM-4521",
                "grade": "B",
                "quality_score": 78.0,
            },
            model="anthropic/claude-3-haiku",
        )

        # Call the mock LLM
        result = await mock_llm_client.chat_completion(
            model="anthropic/claude-3-haiku",
            messages=[
                {"role": "system", "content": "Extract fields from QC data"},
                {"role": "user", "content": "farmer_code: WM-4521, grade: B"},
            ],
        )

        # Verify response
        import json

        parsed = json.loads(result.content)
        assert parsed["farmer_id"] == "WM-4521"
        assert parsed["grade"] == "B"

        # Verify call was recorded
        calls = mock_llm_client.get_calls()
        assert len(calls) == 1
        assert calls[0]["model"] == "anthropic/claude-3-haiku"


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: USING MOCK MONGODB
# ═══════════════════════════════════════════════════════════════════════════════


class TestMongoDBUsage:
    """Examples of using the MockMongoClient fixture."""

    @pytest.mark.asyncio
    async def test_insert_and_find(self, mock_mongodb_client: MockMongoClient) -> None:
        """Test MongoDB insert and find operations."""
        db = mock_mongodb_client["collection_model"]
        collection = db["quality_events"]

        # Insert a document
        doc = {
            "farmer_id": "WM-4521",
            "grade": "B",
            "quality_score": 78.0,
        }
        result = await collection.insert_one(doc)
        assert result.inserted_id is not None

        # Find the document
        found = await collection.find_one({"farmer_id": "WM-4521"})
        assert found is not None
        assert found["grade"] == "B"

    @pytest.mark.asyncio
    async def test_update_document(self, mock_mongodb_client: MockMongoClient) -> None:
        """Test MongoDB update operations."""
        db = mock_mongodb_client["collection_model"]
        collection = db["quality_events"]

        # Insert initial document
        await collection.insert_one({"farmer_id": "WM-4521", "status": "pending"})

        # Update the document
        await collection.update_one(
            {"farmer_id": "WM-4521"},
            {"$set": {"status": "processed"}},
        )

        # Verify update
        found = await collection.find_one({"farmer_id": "WM-4521"})
        assert found["status"] == "processed"


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: USING MCP CLIENT MOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPClientUsage:
    """Examples of using MCP client mocks."""

    @pytest.mark.asyncio
    async def test_collection_mcp_get_document(self, mock_collection_mcp) -> None:
        """Test calling Collection MCP tools."""
        # Configure tool response
        mock_collection_mcp.configure_tool_response(
            "get_document",
            {
                "doc_id": "DOC-00001",
                "farmer_id": "WM-4521",
                "grade": "B",
                "raw_data": {"leaf_count": 150},
            },
        )

        # Call the tool
        result = await mock_collection_mcp.call_tool(
            "get_document",
            {"doc_id": "DOC-00001"},
        )

        # Verify response
        assert result["farmer_id"] == "WM-4521"
        assert result["grade"] == "B"

        # Verify call was recorded
        calls = mock_collection_mcp.get_tool_calls("get_document")
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_plantation_mcp_get_farmer(self, mock_plantation_mcp) -> None:
        """Test calling Plantation MCP tools."""
        # Configure tool response
        mock_plantation_mcp.configure_tool_response(
            "get_farmer",
            {
                "farmer_id": "WM-4521",
                "name": "James Kipchoge",
                "region": "Kericho-High",
                "performance_summary": {
                    "quality_score_avg": 75.5,
                    "primary_percentage": 82.0,
                },
            },
        )

        # Call the tool
        result = await mock_plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": "WM-4521"},
        )

        # Verify response
        assert result["name"] == "James Kipchoge"
        assert result["performance_summary"]["primary_percentage"] == 82.0


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: USING SAMPLE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


class TestSampleFixtures:
    """Examples of using pre-built sample fixtures."""

    def test_sample_qc_payload(self, sample_qc_payload: dict) -> None:
        """Test with pre-built QC payload."""
        assert sample_qc_payload["source"] == "qc-analyzer"
        assert sample_qc_payload["event_type"] == "END_BAG"
        assert sample_qc_payload["farmer_id"] == "WM-4521"
        assert "moisture_percent" in sample_qc_payload["raw_data"]

    def test_sample_farmer(self, sample_farmer: dict) -> None:
        """Test with pre-built farmer data."""
        assert sample_farmer["farmer_id"] == "WM-4521"
        assert sample_farmer["name"] == "James Kipchoge"
        assert sample_farmer["region"] == "Kericho-High"
        assert sample_farmer["performance_summary"]["primary_percentage"] == 82.0


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: MARKED TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_unit_example() -> None:
    """Example of a unit test marked with @pytest.mark.unit."""
    assert 1 + 1 == 2


@pytest.mark.slow
@pytest.mark.asyncio
async def test_slow_example() -> None:
    """Example of a slow test - skip with: pytest -m 'not slow'."""
    import asyncio

    await asyncio.sleep(0.1)  # Simulate slow operation
    assert True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_example(mock_dapr_client: MockDaprClient) -> None:
    """Example of an integration test."""
    await mock_dapr_client.publish_event(
        pubsub_name="pubsub",
        topic_name="test.event",
        data={"test": True},
    )
    assert len(mock_dapr_client.published_events) == 1
