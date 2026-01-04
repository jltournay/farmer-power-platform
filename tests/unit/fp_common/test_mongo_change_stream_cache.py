"""Unit tests for MongoChangeStreamCache base class.

Story 0.75.4: Tests for the abstract base cache class (ADR-013).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_common.cache import MongoChangeStreamCache
from pydantic import BaseModel

# =============================================================================
# TEST FIXTURES
# =============================================================================


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    id: str
    name: str
    status: str = "active"


class SampleCache(MongoChangeStreamCache[SampleModel]):
    """Concrete implementation for testing."""

    def _get_cache_key(self, item: SampleModel) -> str:
        return item.id

    def _parse_document(self, doc: dict) -> SampleModel:
        doc.pop("_id", None)
        return SampleModel.model_validate(doc)

    def _get_filter(self) -> dict:
        return {"status": "active"}


@pytest.fixture
def mock_db():
    """Create mock MongoDB database."""
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def mock_collection(mock_db):
    """Get the mock collection from db."""
    return mock_db["test_collection"]


@pytest.fixture
def sample_cache(mock_db):
    """Create a SampleCache instance."""
    return SampleCache(db=mock_db, collection_name="test_collection", cache_name="sample")


# =============================================================================
# CACHE VALIDITY TESTS
# =============================================================================


class TestCacheValidity:
    """Tests for cache validity checking."""

    def test_is_cache_valid_returns_false_when_cache_is_none(self, sample_cache):
        """Test _is_cache_valid returns False when cache is None."""
        sample_cache._cache = None
        sample_cache._cache_loaded_at = None

        assert sample_cache._is_cache_valid() is False

    def test_is_cache_valid_returns_false_when_cache_expired(self, sample_cache):
        """Test _is_cache_valid returns False when cache TTL expired."""
        sample_cache._cache = {"item1": SampleModel(id="1", name="Test")}
        # Set cache loaded time to 10 minutes ago (beyond 5 min TTL)
        sample_cache._cache_loaded_at = datetime.now(UTC) - timedelta(minutes=10)

        assert sample_cache._is_cache_valid() is False

    def test_is_cache_valid_returns_true_when_cache_valid(self, sample_cache):
        """Test _is_cache_valid returns True when cache exists and not expired."""
        sample_cache._cache = {"item1": SampleModel(id="1", name="Test")}
        sample_cache._cache_loaded_at = datetime.now(UTC) - timedelta(minutes=2)

        assert sample_cache._is_cache_valid() is True

    def test_is_cache_valid_at_boundary(self, sample_cache):
        """Test _is_cache_valid at exactly TTL boundary (should be valid)."""
        sample_cache._cache = {"item1": SampleModel(id="1", name="Test")}
        # Set to just under 5 minutes
        sample_cache._cache_loaded_at = datetime.now(UTC) - timedelta(minutes=4, seconds=59)

        assert sample_cache._is_cache_valid() is True


# =============================================================================
# CACHE AGE TESTS
# =============================================================================


class TestCacheAge:
    """Tests for cache age calculation."""

    def test_get_cache_age_returns_zero_when_cache_is_none(self, sample_cache):
        """Test get_cache_age returns 0 when cache is not loaded."""
        sample_cache._cache_loaded_at = None

        assert sample_cache.get_cache_age() == 0.0

    def test_get_cache_age_returns_positive_value_when_cache_exists(self, sample_cache):
        """Test get_cache_age returns positive seconds when cache loaded."""
        sample_cache._cache_loaded_at = datetime.now(UTC) - timedelta(seconds=30)

        age = sample_cache.get_cache_age()
        assert 29 < age < 31  # Allow for small timing variance


# =============================================================================
# CACHE ACCESS TESTS
# =============================================================================


class TestCacheAccess:
    """Tests for cache get_all and get methods."""

    @pytest.mark.asyncio
    async def test_get_all_loads_from_db_on_first_call(self, sample_cache, mock_collection):
        """Test get_all loads from database on cache miss."""
        # Setup mock cursor
        docs = [
            {"_id": "mongo1", "id": "1", "name": "Item 1", "status": "active"},
            {"_id": "mongo2", "id": "2", "name": "Item 2", "status": "active"},
        ]

        async def async_iter():
            for doc in docs:
                yield doc

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        # First call - cache miss
        result = await sample_cache.get_all()

        assert len(result) == 2
        assert "1" in result
        assert "2" in result
        assert result["1"].name == "Item 1"
        mock_collection.find.assert_called_once_with({"status": "active"})

    @pytest.mark.asyncio
    async def test_get_all_returns_cached_data_on_second_call(self, sample_cache, mock_collection):
        """Test get_all returns cached data on cache hit."""
        # Pre-populate cache
        sample_cache._cache = {
            "1": SampleModel(id="1", name="Cached Item"),
        }
        sample_cache._cache_loaded_at = datetime.now(UTC)

        result = await sample_cache.get_all()

        assert len(result) == 1
        assert result["1"].name == "Cached Item"
        # find should NOT be called on cache hit
        mock_collection.find.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_returns_specific_item_by_key(self, sample_cache):
        """Test get returns specific item by key."""
        sample_cache._cache = {
            "1": SampleModel(id="1", name="Item 1"),
            "2": SampleModel(id="2", name="Item 2"),
        }
        sample_cache._cache_loaded_at = datetime.now(UTC)

        result = await sample_cache.get("2")

        assert result is not None
        assert result.id == "2"
        assert result.name == "Item 2"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self, sample_cache):
        """Test get returns None for missing key."""
        sample_cache._cache = {
            "1": SampleModel(id="1", name="Item 1"),
        }
        sample_cache._cache_loaded_at = datetime.now(UTC)

        result = await sample_cache.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_skips_invalid_documents(self, sample_cache, mock_collection):
        """Test get_all skips documents that fail to parse."""
        # Mix of valid and invalid documents
        docs = [
            {"_id": "mongo1", "id": "1", "name": "Valid Item", "status": "active"},
            {"_id": "mongo2", "invalid_field": "missing_required_id"},  # Will fail parsing
            {"_id": "mongo3", "id": "3", "name": "Another Valid", "status": "active"},
        ]

        async def async_iter():
            for doc in docs:
                yield doc

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        # Should not raise, just skip invalid document
        result = await sample_cache.get_all()

        # Only valid documents should be in cache
        assert len(result) == 2
        assert "1" in result
        assert "3" in result
        assert "2" not in result  # Invalid doc was skipped


# =============================================================================
# CACHE INVALIDATION TESTS
# =============================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_cache_clears_cache(self, sample_cache):
        """Test _invalidate_cache clears the cache."""
        sample_cache._cache = {"1": SampleModel(id="1", name="Test")}
        sample_cache._cache_loaded_at = datetime.now(UTC)

        sample_cache._invalidate_cache(reason="test")

        assert sample_cache._cache is None
        assert sample_cache._cache_loaded_at is None

    def test_public_invalidate_cache_works(self, sample_cache):
        """Test public invalidate_cache method."""
        sample_cache._cache = {"1": SampleModel(id="1", name="Test")}
        sample_cache._cache_loaded_at = datetime.now(UTC)

        sample_cache.invalidate_cache()

        assert sample_cache._cache is None


# =============================================================================
# HEALTH STATUS TESTS
# =============================================================================


class TestHealthStatus:
    """Tests for health status reporting."""

    def test_get_health_status_returns_correct_structure(self, sample_cache):
        """Test get_health_status returns correct dict structure."""
        sample_cache._cache = {
            "1": SampleModel(id="1", name="Test"),
            "2": SampleModel(id="2", name="Test 2"),
        }
        sample_cache._cache_loaded_at = datetime.now(UTC) - timedelta(seconds=10)

        status = sample_cache.get_health_status()

        assert "cache_size" in status
        assert "cache_age_seconds" in status
        assert "change_stream_active" in status
        assert "cache_valid" in status

        assert status["cache_size"] == 2
        assert 9 < status["cache_age_seconds"] < 11
        assert status["change_stream_active"] is False
        assert status["cache_valid"] is True

    def test_get_health_status_when_cache_empty(self, sample_cache):
        """Test get_health_status when cache is empty."""
        sample_cache._cache = None
        sample_cache._cache_loaded_at = None

        status = sample_cache.get_health_status()

        assert status["cache_size"] == 0
        assert status["cache_age_seconds"] == 0.0
        assert status["cache_valid"] is False


# =============================================================================
# CHANGE STREAM TESTS
# =============================================================================


class TestChangeStream:
    """Tests for change stream management."""

    @pytest.mark.asyncio
    async def test_start_change_stream_spawns_background_task(self, sample_cache, mock_collection):
        """Test start_change_stream spawns a background task."""
        # Mock the watch context manager
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()
        mock_stream.__aiter__ = lambda self: self
        mock_stream.__anext__ = AsyncMock(side_effect=asyncio.CancelledError)
        mock_collection.watch = MagicMock(return_value=mock_stream)

        await sample_cache.start_change_stream()

        assert sample_cache._change_stream_task is not None
        assert sample_cache._change_stream_active is True

        # Cleanup
        await sample_cache.stop_change_stream()

    @pytest.mark.asyncio
    async def test_stop_change_stream_cancels_background_task(self, sample_cache, mock_collection):
        """Test stop_change_stream cancels the background task."""
        # Mock the watch context manager
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()

        async def never_ending():
            while True:
                await asyncio.sleep(1)
                raise StopAsyncIteration

        mock_stream.__aiter__ = lambda self: self
        mock_stream.__anext__ = never_ending
        mock_collection.watch = MagicMock(return_value=mock_stream)

        await sample_cache.start_change_stream()
        assert sample_cache._change_stream_task is not None

        await sample_cache.stop_change_stream()

        assert sample_cache._change_stream_active is False
        assert sample_cache._change_stream_task is None

    @pytest.mark.asyncio
    async def test_start_change_stream_warns_if_already_running(self, sample_cache, mock_collection):
        """Test start_change_stream logs warning if already running."""
        # Mock the watch context manager
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()
        mock_stream.__aiter__ = lambda self: self
        mock_stream.__anext__ = AsyncMock(side_effect=asyncio.CancelledError)
        mock_collection.watch = MagicMock(return_value=mock_stream)

        await sample_cache.start_change_stream()
        first_task = sample_cache._change_stream_task

        # Try to start again
        await sample_cache.start_change_stream()

        # Task should be the same (not recreated)
        assert sample_cache._change_stream_task is first_task

        # Cleanup
        await sample_cache.stop_change_stream()


# =============================================================================
# ABSTRACT METHOD TESTS
# =============================================================================


class TestAbstractMethods:
    """Tests for abstract method implementations."""

    def test_get_cache_key_returns_id(self, sample_cache):
        """Test _get_cache_key returns the id field."""
        item = SampleModel(id="test-123", name="Test")
        key = sample_cache._get_cache_key(item)
        assert key == "test-123"

    def test_parse_document_removes_mongo_id(self, sample_cache):
        """Test _parse_document removes MongoDB _id."""
        doc = {"_id": "mongo-id", "id": "model-id", "name": "Test", "status": "active"}
        item = sample_cache._parse_document(doc)

        assert item.id == "model-id"
        assert item.name == "Test"

    def test_get_filter_returns_status_active(self, sample_cache):
        """Test _get_filter returns the expected filter."""
        filter_dict = sample_cache._get_filter()
        assert filter_dict == {"status": "active"}


# =============================================================================
# INTEGRATION-LIKE TESTS
# =============================================================================


class TestCacheLifecycle:
    """Tests for complete cache lifecycle."""

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit_cycle(self, sample_cache, mock_collection):
        """Test complete cache miss then hit cycle."""
        docs = [{"_id": "m1", "id": "1", "name": "Item 1", "status": "active"}]

        async def async_iter():
            for doc in docs:
                yield doc

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        # First call - miss
        result1 = await sample_cache.get_all()
        assert len(result1) == 1
        assert mock_collection.find.call_count == 1

        # Second call - hit
        result2 = await sample_cache.get_all()
        assert len(result2) == 1
        assert mock_collection.find.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_invalidation_causes_reload(self, sample_cache, mock_collection):
        """Test cache invalidation causes reload on next access."""
        # Pre-populate cache
        sample_cache._cache = {"old": SampleModel(id="old", name="Old Item")}
        sample_cache._cache_loaded_at = datetime.now(UTC)

        # Invalidate
        sample_cache.invalidate_cache()
        assert sample_cache._cache is None

        # Setup new data
        new_docs = [{"_id": "m1", "id": "new", "name": "New Item", "status": "active"}]

        async def async_iter():
            for doc in new_docs:
                yield doc

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        # Access - should reload
        result = await sample_cache.get_all()

        assert "new" in result
        assert "old" not in result
        mock_collection.find.assert_called_once()
