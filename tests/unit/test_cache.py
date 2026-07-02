"""Unit tests for EntityCache."""

from unittest.mock import patch

from megaplan_sdk.cache import EntityCache


def test_ttl_expiration():
    """Test TTL expiration using time mocking."""

    cache = EntityCache(max_size=100, ttl=5)

    # Set an entry with mocked time
    with patch("megaplan_sdk.cache.time") as mock_time:
        mock_time.return_value = 0  # Start at time 0
        cache.set("Employee", 1, {"id": 1, "name": "John"})

        # Should be available immediately
        assert cache.get("Employee", 1) is not None
        assert cache.get("Employee", 1)["name"] == "John"

        # Advance time past TTL (5 seconds)
        mock_time.return_value = 10  # 10 seconds later (past TTL of 5)
        # Entry should be expired
        assert cache.get("Employee", 1) is None
        assert cache.size() == 0


def test_lru_eviction():
    """Test LRU eviction when max_size is exceeded."""
    cache = EntityCache(max_size=3, ttl=300)

    # Add 3 entries
    cache.set("Employee", 1, {"id": 1})
    cache.set("Employee", 2, {"id": 2})
    cache.set("Employee", 3, {"id": 3})

    assert cache.size() == 3

    # Access first entry to update LRU order
    cache.get("Employee", 1)

    # Add 4th entry - should evict oldest (entry 2, since 1 was accessed)
    cache.set("Employee", 4, {"id": 4})

    assert cache.size() == 3
    assert cache.get("Employee", 1) is not None  # Still there (was accessed)
    assert cache.get("Employee", 2) is None  # Evicted (oldest)
    assert cache.get("Employee", 3) is not None  # Still there
    assert cache.get("Employee", 4) is not None  # New entry


def test_clear_cache_type():
    """Test clearing cache for specific entity type."""
    cache = EntityCache(max_size=100, ttl=300)

    cache.set("Employee", 1, {"id": 1})
    cache.set("Employee", 2, {"id": 2})
    cache.set("Task", 3, {"id": 3})
    cache.set("Task", 4, {"id": 4})

    assert cache.size() == 4

    # Clear only Employee type
    cache.clear_type("Employee")

    assert cache.size() == 2
    assert cache.get("Employee", 1) is None
    assert cache.get("Employee", 2) is None
    assert cache.get("Task", 3) is not None
    assert cache.get("Task", 4) is not None


def test_stats():
    """Test stats() method returns correct keys and values."""
    cache = EntityCache(max_size=1000, ttl=300)

    cache.set("Employee", 1, {"id": 1})
    cache.set("Employee", 2, {"id": 2})
    cache.set("Task", 3, {"id": 3})
    cache.set("Deal", 4, {"id": 4})

    stats = cache.stats()

    assert "size" in stats
    assert "max_size" in stats
    assert "ttl" in stats
    assert "types" in stats

    assert stats["size"] == 4
    assert stats["max_size"] == 1000
    assert stats["ttl"] == 300
    assert stats["types"]["Employee"] == 2
    assert stats["types"]["Task"] == 1
    assert stats["types"]["Deal"] == 1


def test_access_order_update():
    """Test that access order is updated on get() (LRU)."""
    cache = EntityCache(max_size=3, ttl=300)

    # Add 3 entries
    cache.set("Employee", 1, {"id": 1})
    cache.set("Employee", 2, {"id": 2})
    cache.set("Employee", 3, {"id": 3})

    # Access entry 1 - should move it to end of LRU list
    cache.get("Employee", 1)

    # Add 4th entry - should evict entry 2 (oldest, since 1 was accessed)
    cache.set("Employee", 4, {"id": 4})

    assert cache.get("Employee", 1) is not None  # Still there
    assert cache.get("Employee", 2) is None  # Evicted
    assert cache.get("Employee", 3) is not None  # Still there
    assert cache.get("Employee", 4) is not None  # New entry


def test_expired_entry_removal():
    """Test that expired entries are removed from _access_order."""
    cache = EntityCache(max_size=100, ttl=5)

    # Set entries with mocked time
    with patch("megaplan_sdk.cache.time") as mock_time:
        mock_time.return_value = 0  # Start at time 0
        cache.set("Employee", 1, {"id": 1})
        cache.set("Employee", 2, {"id": 2})

        # Verify entries are in access order
        assert cache.size() == 2

        # Advance time past TTL
        mock_time.return_value = 10  # Past TTL

        # Get expired entry - should remove from cache and access_order
        result = cache.get("Employee", 1)
        assert result is None
        assert cache.size() == 1

        # Access order should be updated
        assert cache.get("Employee", 2) is None  # Also expired
        assert cache.size() == 0


def test_set_existing_key():
    """Test that setting existing key updates it without eviction."""
    cache = EntityCache(max_size=2, ttl=300)

    cache.set("Employee", 1, {"id": 1, "name": "John"})
    cache.set("Employee", 2, {"id": 2, "name": "Jane"})

    assert cache.size() == 2

    # Update existing key
    cache.set("Employee", 1, {"id": 1, "name": "John Updated"})

    assert cache.size() == 2  # Size unchanged
    assert cache.get("Employee", 1)["name"] == "John Updated"
    assert cache.get("Employee", 2) is not None  # Still there


def test_clear():
    """Test clearing all cache."""
    cache = EntityCache(max_size=100, ttl=300)

    cache.set("Employee", 1, {"id": 1})
    cache.set("Task", 2, {"id": 2})
    cache.set("Deal", 3, {"id": 3})

    assert cache.size() == 3

    cache.clear()

    assert cache.size() == 0
    assert cache.get("Employee", 1) is None
    assert cache.get("Task", 2) is None
    assert cache.get("Deal", 3) is None


def test_size():
    """Test size() method."""
    cache = EntityCache(max_size=100, ttl=300)

    assert cache.size() == 0

    cache.set("Employee", 1, {"id": 1})
    assert cache.size() == 1

    cache.set("Employee", 2, {"id": 2})
    assert cache.size() == 2

    cache.get("Employee", 1)  # Access doesn't change size
    assert cache.size() == 2

    cache.clear()
    assert cache.size() == 0
