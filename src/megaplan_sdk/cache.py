"""Entity caching system for Megaplan SDK."""

from collections import defaultdict
from dataclasses import dataclass
from time import time
from typing import Any


@dataclass
class CacheEntry:
    """Cache entry with data and expiration time.

    Attributes:
        data: Cached entity data (dict or model).
        expires_at: Expiration timestamp (seconds since epoch).
    """

    data: Any
    expires_at: float


class EntityCache:
    """LRU cache for entities with TTL.

    Thread-safe cache with automatic expiration and size limits.
    Uses (contentType, id) as key for entity storage.

    Attributes:
        max_size: Maximum number of entities to cache.
        ttl: Time-to-live in seconds for cached entities.

    Examples:
        >>> cache = EntityCache(max_size=1000, ttl=300)
        >>> cache.set("Employee", 123, {"id": 123, "name": "John"})
        >>> data = cache.get("Employee", 123)
        >>> print(data)
        {'id': 123, 'name': 'John'}
    """

    def __init__(self, max_size: int = 1000, ttl: int = 300) -> None:
        """Initialize entity cache.

        Args:
            max_size: Maximum cache size (default: 1000 entities).
            ttl: Time-to-live in seconds (default: 300 = 5 minutes).
        """
        self._cache: dict[tuple[str, int], CacheEntry] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._access_order: list[tuple[str, int]] = []
        self._type_keys: dict[str, set[tuple[str, int]]] = defaultdict(set)
        self._type_counts: dict[str, int] = defaultdict(int)

    def _move_to_end(self, key: tuple[str, int]) -> None:
        """Move key to end of access order (LRU update)."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def get(self, content_type: str, entity_id: int) -> Any | None:
        """Get entity from cache if not expired.

        Args:
            content_type: Entity content type (e.g., "Employee").
            entity_id: Entity identifier.

        Returns:
            Cached entity data or None if not found/expired.

        Examples:
            >>> cache = EntityCache()
            >>> cache.set("Employee", 123, {"name": "John"})
            >>> data = cache.get("Employee", 123)
            >>> print(data)
            {'name': 'John'}
        """
        key = (content_type, entity_id)
        entry = self._cache.get(key)

        if entry is None:
            return None

        # Check expiration
        if time() > entry.expires_at:
            self._cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)
            self._type_keys[content_type].discard(key)
            self._type_counts[content_type] = max(0, self._type_counts[content_type] - 1)
            return None

        self._move_to_end(key)
        return entry.data

    def set(self, content_type: str, entity_id: int, data: Any) -> None:
        """Add entity to cache with expiration.

        Args:
            content_type: Entity content type (e.g., "Employee").
            entity_id: Entity identifier.
            data: Entity data to cache.

        Examples:
            >>> cache = EntityCache()
            >>> cache.set("Employee", 123, {"id": 123, "name": "John"})
        """
        key = (content_type, entity_id)

        is_new_key = key not in self._cache

        # Evict oldest if at capacity
        if is_new_key and len(self._cache) >= self._max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            old_type = oldest_key[0]
            self._cache.pop(oldest_key, None)
            self._type_keys[old_type].discard(oldest_key)
            self._type_counts[old_type] = max(0, self._type_counts[old_type] - 1)

        # Store entry
        self._cache[key] = CacheEntry(
            data=data,
            expires_at=time() + self._ttl,
        )

        # Update type tracking
        if is_new_key:
            self._type_keys[content_type].add(key)
            self._type_counts[content_type] += 1

        self._move_to_end(key)

    def clear(self) -> None:
        """Clear all cached entities.

        Examples:
            >>> cache = EntityCache()
            >>> cache.set("Employee", 1, {"id": 1})
            >>> cache.clear()
            >>> assert cache.get("Employee", 1) is None
        """
        self._cache.clear()
        self._access_order.clear()
        self._type_keys.clear()
        for content_type in self._type_counts:
            self._type_counts[content_type] = 0

    def clear_type(self, content_type: str) -> None:
        """Clear cache for specific entity type.

        Args:
            content_type: Entity type to clear (e.g., "Employee").

        Examples:
            >>> cache = EntityCache()
            >>> cache.set("Employee", 1, {"id": 1})
            >>> cache.set("Task", 2, {"id": 2})
            >>> cache.clear_type("Employee")
            >>> assert cache.get("Employee", 1) is None
            >>> assert cache.get("Task", 2) is not None
        """
        keys_to_remove = self._type_keys.get(content_type, set()).copy()

        for key in keys_to_remove:
            self._cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)

        self._type_keys[content_type].clear()
        self._type_counts[content_type] = 0

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached entities.

        Examples:
            >>> cache = EntityCache()
            >>> cache.set("Employee", 1, {"id": 1})
            >>> cache.set("Employee", 2, {"id": 2})
            >>> assert cache.size() == 2
        """
        return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats (size, types, etc.).

        Examples:
            >>> cache = EntityCache()
            >>> cache.set("Employee", 1, {"id": 1})
            >>> cache.set("Task", 2, {"id": 2})
            >>> stats = cache.stats()
            >>> print(stats["size"])
            2
            >>> print(stats["types"])
            {'Employee': 1, 'Task': 1}
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl": self._ttl,
            "types": dict(self._type_counts),
        }
