"""Unit tests for cache stats() calculation including hit_ratio, eviction_rate, and current_size."""

import threading
import time
import pytest

from cache import Cache, Dynamo, TTLLRUCache


class TestCacheStats:
    """Tests covering stats() metrics and zero-division edge cases."""

    def test_empty_cache_zero_division_safety(self):
        """A freshly initialized cache must return 0.0 for hit_ratio and eviction_rate."""
        cache = TTLLRUCache(capacity=5)
        st = cache.stats()

        assert st["hits"] == 0
        assert st["misses"] == 0
        assert st["evictions"] == 0
        assert st["expirations"] == 0
        assert st["hit_ratio"] == 0.0
        assert st["eviction_rate"] == 0.0
        assert st["current_size"] == 0

    def test_puts_without_gets_zero_division_safety(self):
        """Putting items without any get() calls leaves hits + misses == 0, safe zero division."""
        cache = TTLLRUCache(capacity=3)
        cache.put("a", 1)
        cache.put("b", 2)

        st = cache.stats()
        assert st["hits"] == 0
        assert st["misses"] == 0
        assert st["hit_ratio"] == 0.0
        assert st["eviction_rate"] == 0.0
        assert st["current_size"] == 2

    def test_all_hits_ratio(self):
        """100% cache hits should yield hit_ratio == 1.0."""
        cache = TTLLRUCache(capacity=5)
        cache.put("x", 100)
        cache.put("y", 200)

        assert cache.get("x") == 100
        assert cache.get("y") == 200
        assert cache.get("x") == 100
        assert cache.get("y") == 200

        st = cache.stats()
        assert st["hits"] == 4
        assert st["misses"] == 0
        assert st["hit_ratio"] == 1.0
        assert st["eviction_rate"] == 0.0
        assert st["current_size"] == 2

    def test_all_misses_ratio(self):
        """0% cache hits should yield hit_ratio == 0.0."""
        cache = TTLLRUCache(capacity=5)
        assert cache.get("nonexistent_1") is None
        assert cache.get("nonexistent_2") is None
        assert cache.get("nonexistent_3") is None

        st = cache.stats()
        assert st["hits"] == 0
        assert st["misses"] == 3
        assert st["hit_ratio"] == 0.0
        assert st["eviction_rate"] == 0.0
        assert st["current_size"] == 0

    def test_fractional_hit_ratio(self):
        """Mixed hits and misses calculate accurate hit_ratio."""
        cache = TTLLRUCache(capacity=5)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        # 3 hits
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        # 1 miss
        assert cache.get("d") is None

        st = cache.stats()
        assert st["hits"] == 3
        assert st["misses"] == 1
        assert st["hit_ratio"] == 0.75  # 3 / (3 + 1)
        assert st["current_size"] == 3

    def test_eviction_rate_calculation(self):
        """Cache overflow triggers evictions and updates eviction_rate safely."""
        cache = TTLLRUCache(capacity=2)
        cache.put("k1", 1)
        cache.put("k2", 2)
        cache.put("k3", 3)  # evicts k1
        cache.put("k4", 4)  # evicts k2

        # 2 hits, 2 misses (total requests = 4)
        assert cache.get("k3") == 3
        assert cache.get("k4") == 4
        assert cache.get("k1") is None
        assert cache.get("k2") is None

        st = cache.stats()
        assert st["hits"] == 2
        assert st["misses"] == 2
        assert st["evictions"] == 2
        assert st["hit_ratio"] == 0.5  # 2 / 4
        assert st["eviction_rate"] == 0.5  # 2 / 4
        assert st["current_size"] == 2

    def test_current_size_with_deletions_and_clear(self):
        """current_size reflects live item counts as items are added, deleted, or cleared."""
        cache = TTLLRUCache(capacity=10)
        assert cache.stats()["current_size"] == 0

        for i in range(5):
            cache.put(f"key_{i}", i)
        assert cache.stats()["current_size"] == 5

        cache.delete("key_0")
        cache.delete("key_1")
        assert cache.stats()["current_size"] == 3

        cache.clear()
        assert cache.stats()["current_size"] == 0

    def test_aliases_dynamo_and_cache(self):
        """Dynamo and Cache aliases provide the identical functionality."""
        d = Dynamo(capacity=2)
        d.put("a", 1)
        assert d.get("a") == 1
        assert d.get("b") is None
        st_d = d.stats()
        assert st_d["hit_ratio"] == 0.5
        assert st_d["current_size"] == 1

        c = Cache(capacity=2)
        c.put("k", 42)
        assert c.get("k") == 42
        st_c = c.stats()
        assert st_c["hit_ratio"] == 1.0
        assert st_c["current_size"] == 1

    def test_concurrent_access_stats_consistency(self):
        """Threaded access should maintain consistent stats metrics without errors."""
        cache = TTLLRUCache(capacity=10)

        def worker(w_id: int):
            for i in range(50):
                cache.put(f"key_{w_id}_{i % 5}", i)
                cache.get(f"key_{w_id}_{i % 5}")
                cache.get(f"missing_{i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        st = cache.stats()
        assert st["hits"] > 0
        assert st["misses"] > 0
        assert 0.0 <= st["hit_ratio"] <= 1.0
        assert 0.0 <= st["eviction_rate"] <= 1.0
        assert 0 <= st["current_size"] <= 10
