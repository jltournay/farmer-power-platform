"""Integration tests for FarmerRepository with real MongoDB.

These tests validate that Farmer CRUD operations work correctly
with a real MongoDB instance.

Prerequisites:
    docker-compose -f tests/docker-compose.test.yaml up -d

Usage:
    PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src" \
        pytest tests/integration/test_farmer_repository_mongodb.py -v
"""

import pytest
from plantation_model.domain.models import (
    ContactInfo,
    Farmer,
    FarmScale,
    GeoLocation,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)


def create_test_farmer(
    farmer_id: str = "WM-0001",
    phone: str = "+254712345678",
    national_id: str = "12345678",
    region_id: str = "nyeri-highland",
    collection_point_id: str = "nyeri-highland-cp-001",
    is_active: bool = True,
) -> Farmer:
    """Create a test farmer with default values."""
    return Farmer(
        id=farmer_id,
        first_name="Test",
        last_name="Farmer",
        region_id=region_id,
        collection_point_id=collection_point_id,
        farm_location=GeoLocation(
            latitude=-0.4197,
            longitude=36.9553,
            altitude_meters=1950.0,
        ),
        contact=ContactInfo(phone=phone),
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        national_id=national_id,
        is_active=is_active,
        notification_channel=NotificationChannel.SMS,
        interaction_pref=InteractionPreference.TEXT,
        pref_lang=PreferredLanguage.SWAHILI,
    )


@pytest.mark.mongodb
@pytest.mark.asyncio
class TestFarmerRepository:
    """Integration tests for FarmerRepository."""

    async def test_create_farmer(self, test_db) -> None:
        """Test farmer creation persists to MongoDB correctly."""
        repo = FarmerRepository(test_db)

        farmer = create_test_farmer()
        created = await repo.create(farmer)

        assert created.id == "WM-0001"
        assert created.first_name == "Test"
        assert created.contact.phone == "+254712345678"

    async def test_get_by_id(self, test_db) -> None:
        """Test farmer retrieval by ID."""
        repo = FarmerRepository(test_db)

        # Create and retrieve
        farmer = create_test_farmer()
        await repo.create(farmer)

        retrieved = await repo.get_by_id("WM-0001")

        assert retrieved is not None
        assert retrieved.id == "WM-0001"
        assert retrieved.first_name == "Test"
        assert retrieved.last_name == "Farmer"
        assert retrieved.region_id == "nyeri-highland"
        assert retrieved.farm_scale == FarmScale.MEDIUM
        assert retrieved.contact.phone == "+254712345678"

    async def test_get_by_id_returns_none_for_missing(self, test_db) -> None:
        """Test retrieval returns None for non-existent farmer."""
        repo = FarmerRepository(test_db)

        result = await repo.get_by_id("WM-9999")

        assert result is None

    async def test_get_by_phone(self, test_db) -> None:
        """Test farmer lookup by phone number."""
        repo = FarmerRepository(test_db)

        # Create farmer
        farmer = create_test_farmer(phone="+254711111111")
        await repo.create(farmer)

        # Lookup by phone
        result = await repo.get_by_phone("+254711111111")

        assert result is not None
        assert result.id == "WM-0001"
        assert result.contact.phone == "+254711111111"

    async def test_get_by_phone_returns_none_for_missing(self, test_db) -> None:
        """Test phone lookup returns None for unknown phone."""
        repo = FarmerRepository(test_db)

        result = await repo.get_by_phone("+254799999999")

        assert result is None

    async def test_get_by_national_id(self, test_db) -> None:
        """Test farmer lookup by national ID."""
        repo = FarmerRepository(test_db)

        # Create farmer
        farmer = create_test_farmer(national_id="98765432")
        await repo.create(farmer)

        # Lookup by national ID
        result = await repo.get_by_national_id("98765432")

        assert result is not None
        assert result.id == "WM-0001"
        assert result.national_id == "98765432"

    async def test_get_by_national_id_returns_none_for_missing(self, test_db) -> None:
        """Test national ID lookup returns None for unknown ID."""
        repo = FarmerRepository(test_db)

        result = await repo.get_by_national_id("00000000")

        assert result is None

    async def test_update_farmer(self, test_db) -> None:
        """Test updating farmer fields."""
        repo = FarmerRepository(test_db)

        # Create farmer
        farmer = create_test_farmer()
        await repo.create(farmer)

        # Update
        updated = await repo.update(
            "WM-0001",
            {"first_name": "Updated", "farm_size_hectares": 3.0},
        )

        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.farm_size_hectares == 3.0
        assert updated.last_name == "Farmer"  # Unchanged

    async def test_list_by_collection_point(self, test_db) -> None:
        """Test listing farmers by collection point."""
        repo = FarmerRepository(test_db)

        # Create farmers at different collection points
        for i in range(3):
            farmer = create_test_farmer(
                farmer_id=f"WM-{i:04d}",
                phone=f"+25471{i:07d}",
                national_id=f"1234567{i}",
                collection_point_id="cp-001",
            )
            await repo.create(farmer)

        for i in range(2):
            farmer = create_test_farmer(
                farmer_id=f"WM-{100 + i:04d}",
                phone=f"+25472{i:07d}",
                national_id=f"9876543{i}",
                collection_point_id="cp-002",
            )
            await repo.create(farmer)

        # List farmers at cp-001
        farmers, _, total = await repo.list_by_collection_point("cp-001")

        assert total == 3
        assert len(farmers) == 3
        assert all(f.collection_point_id == "cp-001" for f in farmers)

    async def test_list_by_collection_point_active_only(self, test_db) -> None:
        """Test listing only active farmers."""
        repo = FarmerRepository(test_db)

        # Create active and inactive farmers
        active = create_test_farmer(
            farmer_id="WM-0001",
            phone="+254711111111",
            national_id="11111111",
            is_active=True,
        )
        await repo.create(active)

        inactive = create_test_farmer(
            farmer_id="WM-0002",
            phone="+254722222222",
            national_id="22222222",
            is_active=False,
        )
        await repo.create(inactive)

        # List only active
        farmers, _, total = await repo.list_by_collection_point(
            "nyeri-highland-cp-001",
            active_only=True,
        )

        assert total == 1
        assert farmers[0].id == "WM-0001"

        # List all (including inactive)
        farmers_all, _, total_all = await repo.list_by_collection_point(
            "nyeri-highland-cp-001",
            active_only=False,
        )

        assert total_all == 2

    async def test_list_by_region(self, test_db) -> None:
        """Test listing farmers by region."""
        repo = FarmerRepository(test_db)

        # Create farmers in different regions
        for i in range(3):
            farmer = create_test_farmer(
                farmer_id=f"WM-{i:04d}",
                phone=f"+25471{i:07d}",
                national_id=f"1234567{i}",
                region_id="nyeri-highland",
            )
            await repo.create(farmer)

        for i in range(2):
            farmer = create_test_farmer(
                farmer_id=f"WM-{100 + i:04d}",
                phone=f"+25472{i:07d}",
                national_id=f"9876543{i}",
                region_id="kericho-midland",
            )
            await repo.create(farmer)

        # List farmers in nyeri-highland
        farmers, _, total = await repo.list_by_region("nyeri-highland")

        assert total == 3
        assert all(f.region_id == "nyeri-highland" for f in farmers)

    async def test_ensure_indexes(self, test_db) -> None:
        """Test index creation happens correctly."""
        repo = FarmerRepository(test_db)

        # Create indexes
        await repo.ensure_indexes()

        # Verify indexes exist
        indexes = await test_db["farmers"].index_information()

        assert "idx_farmer_id" in indexes
        assert "idx_farmer_phone" in indexes
        assert "idx_farmer_national_id" in indexes
        assert "idx_farmer_collection_point" in indexes
        assert "idx_farmer_region" in indexes

    async def test_unique_phone_constraint(self, test_db) -> None:
        """Test duplicate phone rejection."""
        repo = FarmerRepository(test_db)
        await repo.ensure_indexes()

        # Create first farmer
        farmer1 = create_test_farmer(
            farmer_id="WM-0001",
            phone="+254712345678",
            national_id="11111111",
        )
        await repo.create(farmer1)

        # Try duplicate phone - should raise
        farmer2 = create_test_farmer(
            farmer_id="WM-0002",
            phone="+254712345678",  # Same phone
            national_id="22222222",
        )
        with pytest.raises(Exception):  # DuplicateKeyError
            await repo.create(farmer2)

    async def test_unique_national_id_constraint(self, test_db) -> None:
        """Test duplicate national ID rejection."""
        repo = FarmerRepository(test_db)
        await repo.ensure_indexes()

        # Create first farmer
        farmer1 = create_test_farmer(
            farmer_id="WM-0001",
            phone="+254711111111",
            national_id="12345678",
        )
        await repo.create(farmer1)

        # Try duplicate national ID - should raise
        farmer2 = create_test_farmer(
            farmer_id="WM-0002",
            phone="+254722222222",
            national_id="12345678",  # Same national ID
        )
        with pytest.raises(Exception):  # DuplicateKeyError
            await repo.create(farmer2)

    async def test_delete_farmer(self, test_db) -> None:
        """Test deleting a farmer."""
        repo = FarmerRepository(test_db)

        # Create farmer
        farmer = create_test_farmer()
        await repo.create(farmer)

        # Verify exists
        existing = await repo.get_by_id("WM-0001")
        assert existing is not None

        # Delete
        deleted = await repo.delete("WM-0001")
        assert deleted is True

        # Verify deleted
        after_delete = await repo.get_by_id("WM-0001")
        assert after_delete is None
