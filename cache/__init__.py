"""Cache and Dynamo module implementing TTLLRUCache with health metrics."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional


class TTLLRUCache:
    """Thread-safe, TTL-aware Least-Recently-Used (LRU) Cache."""

    def __init__(self, capacity: int, default_ttl: Optional[float] = None):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("Capacity must be an integer >= 1")
        if default_ttl is not None and (not isinstance(default_ttl, (int, float)) or default_ttl <= 0):
            raise ValueError("Default TTL must be > 0")

        self.capacity = capacity
        self.default_ttl = float(default_ttl) if default_ttl is not None else None
        self._cache: OrderedDict[Any, tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = threading.RLock()

        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    def _is_expired(self, expire_at: Optional[float], now: float) -> bool:
        if expire_at is None:
            return False
        return now >= expire_at

    def put(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        if ttl is not None and (not isinstance(ttl, (int, float)) or ttl <= 0):
            raise ValueError("TTL must be > 0")

        effective_ttl = float(ttl) if ttl is not None else self.default_ttl
        now = time.monotonic()
        expire_at = (now + effective_ttl) if effective_ttl is not None else None

        with self._lock:
            if key in self._cache:
                _, old_expire_at = self._cache[key]
                if self._is_expired(old_expire_at, now):
                    self._expirations += 1
                self._cache[key] = (value, expire_at)
                self._cache.move_to_end(key)
                return

            # Proactively evict expired items
            expired_keys = [k for k, (_, exp) in self._cache.items() if self._is_expired(exp, now)]
            for k in expired_keys:
                del self._cache[k]
                self._expirations += 1

            # Capacity eviction
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)
                self._evictions += 1

            self._cache[key] = (value, expire_at)
            self._cache.move_to_end(key)

    def get(self, key: Any, default: Any = None) -> Any:
        now = time.monotonic()
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            value, expire_at = self._cache[key]
            if self._is_expired(expire_at, now):
                self._misses += 1
                self._expirations += 1
                del self._cache[key]
                return default

            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def delete(self, key: Any) -> bool:
        now = time.monotonic()
        with self._lock:
            if key not in self._cache:
                return False
            _, expire_at = self._cache[key]
            if self._is_expired(expire_at, now):
                self._expirations += 1
            del self._cache[key]
            return True

    def cleanup_expired(self) -> int:
        now = time.monotonic()
        with self._lock:
            expired_keys = [k for k, (_, exp) in self._cache.items() if self._is_expired(exp, now)]
            for k in expired_keys:
                del self._cache[k]
                self._expirations += 1
            return len(expired_keys)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        now = time.monotonic()
        with self._lock:
            return sum(1 for _, exp in self._cache.values() if not self._is_expired(exp, now))

    def __contains__(self, key: Any) -> bool:
        now = time.monotonic()
        with self._lock:
            if key not in self._cache:
                return False
            _, expire_at = self._cache[key]
            return not self._is_expired(expire_at, now)

    def stats(self) -> Dict[str, Any]:
        """Compute and return health metrics for cache monitoring."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            eviction_rate = (self._evictions / total) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
                "hit_ratio": hit_ratio,
                "eviction_rate": eviction_rate,
                "current_size": len(self._cache),
            }


# Aliases
Cache = TTLLRUCache
Dynamo = TTLLRUCache
LRUCache = TTLLRUCache
