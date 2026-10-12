"""Reference implementation of TokenBucketRateLimiter."""

import time
import threading
from typing import Dict, Any, Optional, Tuple


class TokenBucketRateLimiter:
    def __init__(self, capacity: float, refill_rate: float, default_tier: str = "standard"):
        if not isinstance(capacity, (int, float)) or capacity <= 0:
            raise ValueError("Capacity must be > 0")
        if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:
            raise ValueError("Refill rate must be > 0")

        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.default_tier = default_tier

        # mapping of client identifiers to their respective state arrays
        # state array format: [current_balance, max_capacity, fill_velocity, prev_ts]
        self._state_store: Dict[str, list] = {}
        self._mutex = threading.RLock()

        self._metrics_allowed = 0
        self._metrics_blocked = 0
        self._metrics_refills = 0
        self._metrics_reconfigs = 0

    def _update_client_state(self, key: str, current_ts: float) -> list:
        if key not in self._state_store:
            initial_state = [self.capacity, self.capacity, self.refill_rate, current_ts]
            self._state_store[key] = initial_state
            return initial_state

        state_array = self._state_store[key]
        balance, max_cap, fill_velocity, prev_ts = state_array
        time_delta = current_ts - prev_ts
        if time_delta > 0:
            balance = min(max_cap, balance + time_delta * fill_velocity)
            state_array[0] = balance
            state_array[3] = current_ts
        return state_array

    def allow_request(self, client_id: str, cost: float = 1.0) -> bool:
        if not isinstance(cost, (int, float)) or cost <= 0:
            raise ValueError("Cost must be > 0")

        current_ts = time.monotonic()
        with self._mutex:
            state_array = self._update_client_state(client_id, current_ts)
            balance = state_array[0]

            if balance >= cost:
                state_array[0] = balance - float(cost)
                self._metrics_allowed += 1
                return True
            else:
                self._metrics_blocked += 1
                return False

    def refill(self, client_id: str) -> float:
        current_ts = time.monotonic()
        with self._mutex:
            state_array = self._update_client_state(client_id, current_ts)
            self._metrics_refills += 1
            return state_array[0]

    def set_client_quota(self, client_id: str, capacity: float, refill_rate: float) -> None:
        if not isinstance(capacity, (int, float)) or capacity <= 0:
            raise ValueError("Capacity must be > 0")
        if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:
            raise ValueError("Refill rate must be > 0")

        current_ts = time.monotonic()
        with self._mutex:
            state_array = self._update_client_state(client_id, current_ts)
            balance = min(float(capacity), state_array[0])
            self._state_store[client_id] = [balance, float(capacity), float(refill_rate), current_ts]
            self._metrics_reconfigs += 1

    def get_stats(self) -> Dict[str, int]:
        with self._mutex:
            return {
                "allowed": self._metrics_allowed,
                "blocked": self._metrics_blocked,
                "refills": self._metrics_refills,
                "reconfigurations": self._metrics_reconfigs,
            }

    def clear(self) -> None:
        with self._mutex:
            self._state_store.clear()

    def __len__(self) -> int:
        with self._mutex:
            return len(self._state_store)

    def __contains__(self, client_id: str) -> bool:
        with self._mutex:
            return client_id in self._state_store
