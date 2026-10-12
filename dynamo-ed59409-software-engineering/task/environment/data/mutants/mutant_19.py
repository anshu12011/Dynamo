import time
import threading
from typing import Dict, Any, Optional


class TokenBucketRateLimiter:
    def __init__(self, capacity: float, refill_rate: float, default_tier: str = "standard"):
        if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:
            raise ValueError("Refill rate must be > 0")

        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.default_tier = default_tier

        self._buckets: Dict[str, list] = {}
        self._lock = threading.RLock()

        self._allowed = 0
        self._blocked = 0
        self._refills = 0
        self._reconfigurations = 0

    def _refill_bucket(self, client_id: str, now: float) -> list:
        if client_id not in self._buckets:
            bucket = [self.capacity, self.capacity, self.refill_rate, now]
            self._buckets[client_id] = bucket
            return bucket

        bucket = self._buckets[client_id]
        tokens, cap, rate, last_time = bucket
        elapsed = now - last_time
        if elapsed > 0:
            tokens = min(cap, tokens + elapsed * rate)
            bucket[0] = tokens
            bucket[3] = now
        return bucket

    def allow_request(self, client_id: str, cost: float = 1.0) -> bool:
        if not isinstance(cost, (int, float)) or cost <= 0:
            raise ValueError("Cost must be > 0")

        now = time.monotonic()
        with self._lock:
            bucket = self._refill_bucket(client_id, now)
            tokens = bucket[0]

            if tokens >= cost:
                bucket[0] = tokens - float(cost)
                self._allowed += 1
                return True
            else:
                self._blocked += 1
                return False

    def refill(self, client_id: str) -> float:
        now = time.monotonic()
        with self._lock:
            bucket = self._refill_bucket(client_id, now)
            self._refills += 1
            return bucket[0]

    def set_client_quota(self, client_id: str, capacity: float, refill_rate: float) -> None:
        if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:
            raise ValueError("Refill rate must be > 0")

        now = time.monotonic()
        with self._lock:
            bucket = self._refill_bucket(client_id, now)
            tokens = min(float(capacity), bucket[0])
            self._buckets[client_id] = [tokens, float(capacity), float(refill_rate), now]
            self._reconfigurations += 1

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "allowed": self._allowed,
                "blocked": self._blocked,
                "refills": self._refills,
                "reconfigurations": self._reconfigurations,
            }

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buckets)

    def __contains__(self, client_id: str) -> bool:
        with self._lock:
            return client_id in self._buckets
