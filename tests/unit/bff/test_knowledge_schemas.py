"""Unit tests for Knowledge schemas validation (Story 9.9a - Task 7.3)."""

import pytest
from bff.api.schemas.admin.knowledge_schemas import (
    CreateDocumentRequest,
    DocumentStatus,
    KnowledgeDomain,
    QueryKnowledgeRequest,
    RollbackDocumentRequest,
    UpdateDocumentRequest,
    VectorizeDocumentRequest,
)
from pydantic import ValidationError


class TestKnowledgeDomainEnum:
    def test_valid_domains(self):
        assert KnowledgeDomain.plant_diseases.value == "plant_diseases"
        assert KnowledgeDomain.tea_cultivation.value == "tea_cultivation"
        assert KnowledgeDomain.weather_patterns.value == "weather_patterns"
        assert KnowledgeDomain.quality_standards.value == "quality_standards"
        assert KnowledgeDomain.regional_context.value == "regional_context"

    def test_all_domains_count(self):
        assert len(KnowledgeDomain) == 5


class TestDocumentStatusEnum:
    def test_valid_statuses(self):
        assert DocumentStatus.draft.value == "draft"
        assert DocumentStatus.staged.value == "staged"
        assert DocumentStatus.active.value == "active"
        assert DocumentStatus.archived.value == "archived"


class TestCreateDocumentRequest:
    def test_valid_request(self):
        req = CreateDocumentRequest(
            title="Test Doc",
            domain=KnowledgeDomain.plant_diseases,
            content="Some content",
            author="Dr. Expert",
        )
        assert req.title == "Test Doc"
        assert req.domain == KnowledgeDomain.plant_diseases

    def test_minimal_request(self):
        req = CreateDocumentRequest(
            title="Minimal",
            domain=KnowledgeDomain.tea_cultivation,
        )
        assert req.content == ""
        assert req.author == ""
        assert req.tags == []

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            CreateDocumentRequest(title="", domain=KnowledgeDomain.plant_diseases)

    def test_invalid_domain_rejected(self):
        with pytest.raises(ValidationError):
            CreateDocumentRequest(title="Test", domain="invalid_domain")

    def test_with_tags(self):
        req = CreateDocumentRequest(
            title="Tagged Doc",
            domain=KnowledgeDomain.weather_patterns,
            tags=["drought", "rainfall"],
        )
        assert req.tags == ["drought", "rainfall"]


class TestUpdateDocumentRequest:
    def test_all_empty_is_valid(self):
        req = UpdateDocumentRequest()
        assert req.title == ""
        assert req.content == ""

    def test_partial_update(self):
        req = UpdateDocumentRequest(
            title="New Title",
            change_summary="Updated title",
        )
        assert req.title == "New Title"
        assert req.content == ""


class TestQueryKnowledgeRequest:
    def test_valid_query(self):
        req = QueryKnowledgeRequest(
            query="How to treat blister blight?",
            domains=[KnowledgeDomain.plant_diseases],
            top_k=10,
        )
        assert req.query == "How to treat blister blight?"
        assert req.top_k == 10

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            QueryKnowledgeRequest(query="")

    def test_top_k_limits(self):
        with pytest.raises(ValidationError):
            QueryKnowledgeRequest(query="test", top_k=0)

        with pytest.raises(ValidationError):
            QueryKnowledgeRequest(query="test", top_k=101)

    def test_confidence_threshold_limits(self):
        with pytest.raises(ValidationError):
            QueryKnowledgeRequest(query="test", confidence_threshold=-0.1)

        with pytest.raises(ValidationError):
            QueryKnowledgeRequest(query="test", confidence_threshold=1.1)

    def test_defaults(self):
        req = QueryKnowledgeRequest(query="test")
        assert req.domains == []
        assert req.top_k == 5
        assert req.confidence_threshold == 0.0


class TestRollbackDocumentRequest:
    def test_valid_request(self):
        req = RollbackDocumentRequest(target_version=2)
        assert req.target_version == 2

    def test_zero_version_rejected(self):
        with pytest.raises(ValidationError):
            RollbackDocumentRequest(target_version=0)

    def test_negative_version_rejected(self):
        with pytest.raises(ValidationError):
            RollbackDocumentRequest(target_version=-1)


class TestVectorizeDocumentRequest:
    def test_defaults(self):
        req = VectorizeDocumentRequest()
        assert req.version == 0

    def test_negative_version_rejected(self):
        with pytest.raises(ValidationError):
            VectorizeDocumentRequest(version=-1)
