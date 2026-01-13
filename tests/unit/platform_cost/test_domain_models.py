"""Unit tests for Platform Cost domain models.

Story 13.3: Cost Repository and Budget Monitor

Tests:
- UnifiedCostEvent creation and serialization
- Response models (CostTypeSummary, DailyCostEntry, etc.)
- MongoDB document conversion
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit
from platform_cost.domain.cost_event import (
    AgentTypeCost,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
    UnifiedCostEvent,
)


class TestUnifiedCostEvent:
    """Tests for UnifiedCostEvent model."""

    def test_from_event_llm_extracts_metadata(self) -> None:
        """Test that from_event extracts indexed fields from LLM events."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd=Decimal("0.0015"),
            quantity=1500,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={
                "model": "anthropic/claude-3-haiku",
                "agent_type": "extractor",
                "tokens_in": 1000,
                "tokens_out": 500,
            },
        )

        unified = UnifiedCostEvent.from_event(event_id="test-123", event=event)

        assert unified.id == "test-123"
        assert unified.cost_type == "llm"
        assert unified.amount_usd == Decimal("0.0015")
        assert unified.quantity == 1500
        assert unified.unit == "tokens"
        assert unified.source_service == "ai-model"
        assert unified.success is True
        # Indexed fields extracted from metadata
        assert unified.agent_type == "extractor"
        assert unified.model == "anthropic/claude-3-haiku"
        assert unified.knowledge_domain is None  # Not an embedding

    def test_from_event_embedding_extracts_knowledge_domain(self) -> None:
        """Test that from_event extracts knowledge_domain from embedding events."""
        event = CostRecordedEvent(
            cost_type=CostType.EMBEDDING,
            amount_usd=Decimal("0.0001"),
            quantity=3,
            unit=CostUnit.QUERIES,
            timestamp=datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC),
            source_service="knowledge-model",
            success=True,
            metadata={
                "model": "text-embedding-ada-002",
                "knowledge_domain": "tea-quality",
                "texts_count": 3,
            },
        )

        unified = UnifiedCostEvent.from_event(event_id="emb-456", event=event)

        assert unified.cost_type == "embedding"
        assert unified.model == "text-embedding-ada-002"
        assert unified.knowledge_domain == "tea-quality"
        assert unified.agent_type is None  # Not an LLM event

    def test_from_event_document_no_extracted_fields(self) -> None:
        """Test that from_event handles document events correctly."""
        event = CostRecordedEvent(
            cost_type=CostType.DOCUMENT,
            amount_usd=Decimal("0.05"),
            quantity=5,
            unit=CostUnit.PAGES,
            timestamp=datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC),
            source_service="collection-model",
            success=True,
            metadata={
                "model_id": "prebuilt-document",
                "page_count": 5,
            },
        )

        unified = UnifiedCostEvent.from_event(event_id="doc-789", event=event)

        assert unified.cost_type == "document"
        assert unified.quantity == 5
        assert unified.agent_type is None
        assert unified.model is None  # No model in document metadata
        assert unified.knowledge_domain is None

    def test_from_event_sms(self) -> None:
        """Test that from_event handles SMS events correctly."""
        event = CostRecordedEvent(
            cost_type=CostType.SMS,
            amount_usd=Decimal("0.02"),
            quantity=1,
            unit=CostUnit.MESSAGES,
            timestamp=datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC),
            source_service="notification-model",
            success=True,
            metadata={
                "message_type": "advisory",
                "recipient_count": 1,
            },
        )

        unified = UnifiedCostEvent.from_event(event_id="sms-001", event=event)

        assert unified.cost_type == "sms"
        assert unified.unit == "messages"
        assert unified.source_service == "notification-model"

    def test_to_mongo_doc_sets_id_and_converts_decimal(self) -> None:
        """Test that to_mongo_doc produces correct MongoDB document."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd=Decimal("0.0015"),
            quantity=1500,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={"model": "claude-3-haiku", "agent_type": "extractor"},
        )

        unified = UnifiedCostEvent.from_event(event_id="mongo-test", event=event)
        doc = unified.to_mongo_doc()

        # _id should be set and 'id' field removed
        assert doc["_id"] == "mongo-test"
        assert "id" not in doc

        # Decimal should be stored as string
        assert doc["amount_usd"] == "0.0015"
        assert isinstance(doc["amount_usd"], str)

        # Other fields should be present
        assert doc["cost_type"] == "llm"
        assert doc["source_service"] == "ai-model"

    def test_from_event_with_optional_fields(self) -> None:
        """Test from_event with factory_id and request_id."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd=Decimal("0.01"),
            quantity=2000,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            factory_id="FAC-001",
            request_id="req-abc-123",
        )

        unified = UnifiedCostEvent.from_event(event_id="opt-test", event=event)

        assert unified.factory_id == "FAC-001"
        assert unified.request_id == "req-abc-123"


class TestCostTypeSummary:
    """Tests for CostTypeSummary model."""

    def test_creation_with_all_fields(self) -> None:
        """Test CostTypeSummary creation with all fields."""
        summary = CostTypeSummary(
            cost_type="llm",
            total_cost_usd=Decimal("5.50"),
            total_quantity=100000,
            request_count=250,
            percentage=65.5,
        )

        assert summary.cost_type == "llm"
        assert summary.total_cost_usd == Decimal("5.50")
        assert summary.total_quantity == 100000
        assert summary.request_count == 250
        assert summary.percentage == 65.5

    def test_serialization_preserves_decimal_as_string(self) -> None:
        """Test that Decimal is serialized as string in JSON."""
        summary = CostTypeSummary(
            cost_type="document",
            total_cost_usd=Decimal("1.2345"),
            total_quantity=50,
            request_count=10,
            percentage=14.5,
        )

        json_data = summary.model_dump(mode="json")
        assert json_data["total_cost_usd"] == "1.2345"


class TestDailyCostEntry:
    """Tests for DailyCostEntry model."""

    def test_creation_with_breakdown(self) -> None:
        """Test DailyCostEntry with per-type breakdown."""
        entry = DailyCostEntry(
            entry_date=date(2026, 1, 12),
            total_cost_usd=Decimal("10.00"),
            llm_cost_usd=Decimal("7.50"),
            document_cost_usd=Decimal("1.50"),
            embedding_cost_usd=Decimal("0.50"),
            sms_cost_usd=Decimal("0.50"),
        )

        assert entry.entry_date == date(2026, 1, 12)
        assert entry.total_cost_usd == Decimal("10.00")
        assert entry.llm_cost_usd == Decimal("7.50")
        assert entry.document_cost_usd == Decimal("1.50")

    def test_defaults_to_zero(self) -> None:
        """Test that cost breakdown defaults to zero."""
        entry = DailyCostEntry(
            entry_date=date(2026, 1, 12),
            total_cost_usd=Decimal("5.00"),
        )

        assert entry.llm_cost_usd == Decimal("0")
        assert entry.document_cost_usd == Decimal("0")
        assert entry.embedding_cost_usd == Decimal("0")
        assert entry.sms_cost_usd == Decimal("0")


class TestCurrentDayCost:
    """Tests for CurrentDayCost model."""

    def test_creation_with_by_type(self) -> None:
        """Test CurrentDayCost with per-type breakdown."""
        now = datetime.now(UTC)
        cost = CurrentDayCost(
            cost_date=date.today(),
            total_cost_usd=Decimal("3.25"),
            by_type={
                "llm": Decimal("2.50"),
                "document": Decimal("0.75"),
            },
            updated_at=now,
        )

        assert cost.total_cost_usd == Decimal("3.25")
        assert cost.by_type["llm"] == Decimal("2.50")
        assert cost.by_type["document"] == Decimal("0.75")
        assert cost.updated_at == now


class TestAgentTypeCost:
    """Tests for AgentTypeCost model."""

    def test_creation_with_all_fields(self) -> None:
        """Test AgentTypeCost creation."""
        cost = AgentTypeCost(
            agent_type="extractor",
            cost_usd=Decimal("2.50"),
            request_count=500,
            tokens_in=250000,
            tokens_out=125000,
            percentage=45.5,
        )

        assert cost.agent_type == "extractor"
        assert cost.cost_usd == Decimal("2.50")
        assert cost.request_count == 500
        assert cost.tokens_in == 250000
        assert cost.tokens_out == 125000
        assert cost.percentage == 45.5


class TestModelCost:
    """Tests for ModelCost model."""

    def test_creation_with_model_name(self) -> None:
        """Test ModelCost creation with model name."""
        cost = ModelCost(
            model="anthropic/claude-3-haiku",
            cost_usd=Decimal("1.75"),
            request_count=350,
            tokens_in=175000,
            tokens_out=87500,
            percentage=31.8,
        )

        assert cost.model == "anthropic/claude-3-haiku"
        assert cost.cost_usd == Decimal("1.75")
        assert cost.percentage == 31.8


class TestDomainCost:
    """Tests for DomainCost model."""

    def test_creation(self) -> None:
        """Test DomainCost creation."""
        cost = DomainCost(
            knowledge_domain="tea-quality",
            cost_usd=Decimal("0.25"),
            tokens_total=50000,
            texts_count=100,
            percentage=50.0,
        )

        assert cost.knowledge_domain == "tea-quality"
        assert cost.tokens_total == 50000
        assert cost.texts_count == 100


class TestDocumentCostSummary:
    """Tests for DocumentCostSummary model."""

    def test_creation_with_average(self) -> None:
        """Test DocumentCostSummary with average cost calculation."""
        summary = DocumentCostSummary(
            total_cost_usd=Decimal("5.00"),
            total_pages=100,
            avg_cost_per_page_usd=Decimal("0.05"),
            document_count=20,
        )

        assert summary.total_cost_usd == Decimal("5.00")
        assert summary.total_pages == 100
        assert summary.avg_cost_per_page_usd == Decimal("0.05")
        assert summary.document_count == 20
