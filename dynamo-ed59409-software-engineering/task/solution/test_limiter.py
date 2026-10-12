"""Comprehensive, mutation-resistant black-box test suite for TokenBucketRateLimiter."""

import time
import threading
import pytest
from hypothesis import given, settings, strategies as st
from rate_limiter import TokenBucketRateLimiter


class BlockingKey:
    """Custom key object used to test synchronization boundaries of limiter methods."""
    def __init__(self, name, lock_held_event, release_lock_event):
        self.name = name
        self.lock_held_event = lock_held_event
        self.release_lock_event = release_lock_event

    def __hash__(self):
        if self.lock_held_event:
            self.lock_held_event.set()
        if self.release_lock_event:
            self.release_lock_event.wait(timeout=1.0)
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, BlockingKey) and self.name == other.name


def test_init_invalid_parameters():
    """Verify initialization input validation for capacity and refill_rate."""
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=0, refill_rate=1.0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=-5.0, refill_rate=1.0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=10.0, refill_rate=0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=10.0, refill_rate=-2.5)


def test_allow_request_basic_cost():
    """Verify allow_request returns True when tokens are sufficient and handles invalid costs."""
    limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=1.0)
    
    with pytest.raises(ValueError):
        limiter.allow_request("client_a", cost=0)
    with pytest.raises(ValueError):
        limiter.allow_request("client_a", cost=-1.0)

    assert limiter.allow_request("client_a", cost=2.0) is True
    assert limiter.allow_request("client_a", cost=3.0) is True
    assert limiter.allow_request("client_a", cost=1.0) is False  # capacity depleted


def test_allow_request_rejected_does_not_leak_tokens():
    """Verify that a rejected request DOES NOT deduct tokens or leak credits."""
    limiter = TokenBucketRateLimiter(capacity=2.0, refill_rate=1.0)
    assert limiter.allow_request("client_1", cost=1.5) is True

    # Current tokens: 0.5. Attempt a request costing 1.0 (should be rejected)
    assert limiter.allow_request("client_1", cost=1.0) is False

    # Tokens must remain 0.5. A request costing 0.5 must succeed immediately!
    assert limiter.allow_request("client_1", cost=0.5) is True

    stats = limiter.get_stats()
    assert stats["allowed"] == 2
    assert stats["blocked"] == 1


def test_exact_capacity_token_refill_fractional_precision():
    """Verify sub-second fractional token refill calculations."""
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=100.0)
    t0 = time.monotonic()
    limiter.allow_request("client_fast", cost=10.0)  # bucket drained to 0

    time.sleep(0.04)
    t1 = time.monotonic()

    tokens = limiter.refill("client_fast")
    expected = min(10.0, (t1 - t0) * 100.0)
    assert abs(tokens - expected) < 1.0, f"Expected ~{expected} tokens, got {tokens}"
    assert limiter.allow_request("client_fast", cost=tokens) is True


def test_capacity_boundary_limit():
    """Verify tokens never exceed maximum bucket capacity regardless of elapsed time."""
    limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=100.0)
    limiter.allow_request("client_cap", cost=3.0)  # Client exists in buckets, 2 tokens left

    time.sleep(0.08)  # 8 tokens refilled -> should be capped at max capacity 5.0

    tokens = limiter.refill("client_cap")
    assert tokens == 5.0  # strictly capped at capacity 5.0
    assert limiter.allow_request("client_cap", cost=5.1) is False


def test_set_client_quota_atomic_and_stats():
    """Verify setting per-client quota updates capacity, rate, and retains current token balance."""
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=1.0)
    limiter.allow_request("vip_client", cost=8.0)  # 2.0 tokens remaining

    with pytest.raises(ValueError):
        limiter.set_client_quota("vip_client", capacity=0, refill_rate=1.0)
    with pytest.raises(ValueError):
        limiter.set_client_quota("vip_client", capacity=10.0, refill_rate=-1.0)

    # Increase capacity to 100.0: token balance must be retained at ~2.0, not reset to 100.0
    limiter.set_client_quota("vip_client", capacity=100.0, refill_rate=1.0)
    assert limiter.allow_request("vip_client", cost=10.0) is False  # Kills mutant_10

    stats = limiter.get_stats()
    assert stats["reconfigurations"] == 1


def test_set_client_quota_synchronization_boundary():
    """Verify set_client_quota acquires the limiter lock and blocks when another thread holds it."""
    limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=1.0)
    lock_held_event = threading.Event()
    release_lock_event = threading.Event()
    quota_completed_event = threading.Event()

    def worker_holding_lock():
        key = BlockingKey("blocker", lock_held_event, release_lock_event)
        limiter.allow_request(key, cost=1.0)

    def worker_quota():
        limiter.set_client_quota("other_client", capacity=10.0, refill_rate=2.0)
        quota_completed_event.set()

    t_holder = threading.Thread(target=worker_holding_lock)
    t_quota = threading.Thread(target=worker_quota)

    t_holder.start()
    assert lock_held_event.wait(timeout=1.0), "Lock holder thread failed to acquire lock"

    t_quota.start()
    completed_without_lock = quota_completed_event.wait(timeout=0.05)

    release_lock_event.set()
    t_holder.join()
    t_quota.join()

    assert not completed_without_lock, "set_client_quota executed without acquiring the limiter lock"


def test_allow_request_synchronization_boundary():
    """Verify allow_request acquires the limiter lock and blocks when another thread holds it."""
    limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=1.0)
    lock_held_event = threading.Event()
    release_lock_event = threading.Event()
    allow_completed_event = threading.Event()

    def worker_holding_lock():
        key = BlockingKey("blocker", lock_held_event, release_lock_event)
        limiter.set_client_quota(key, capacity=10.0, refill_rate=2.0)

    def worker_allow():
        limiter.allow_request("other_client", cost=1.0)
        allow_completed_event.set()

    t_holder = threading.Thread(target=worker_holding_lock)
    t_allow = threading.Thread(target=worker_allow)

    t_holder.start()
    assert lock_held_event.wait(timeout=1.0), "Lock holder thread failed to acquire lock"

    t_allow.start()
    completed_without_lock = allow_completed_event.wait(timeout=0.05)

    release_lock_event.set()
    t_holder.join()
    t_allow.join()

    assert not completed_without_lock, "allow_request executed without acquiring the limiter lock"


def test_stats_tracking_accuracy():
    """Verify accurate cumulative stats for allowed, blocked, refills, and reconfigurations."""
    limiter = TokenBucketRateLimiter(capacity=2.0, refill_rate=1.0)
    limiter.allow_request("c1", cost=1.0)  # allowed=1
    limiter.allow_request("c1", cost=5.0)  # blocked=1
    limiter.refill("c1")  # refills=1
    limiter.set_client_quota("c1", capacity=4.0, refill_rate=2.0)  # reconfigs=1

    stats = limiter.get_stats()
    assert stats["allowed"] == 1
    assert stats["blocked"] == 1
    assert stats["refills"] == 1
    assert stats["reconfigurations"] == 1


def test_clear_preserves_stats():
    """Verify clear resets client buckets but retains cumulative stats."""
    limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=1.0)
    limiter.allow_request("c1", cost=2.0)
    stats_before = limiter.get_stats()

    limiter.clear()
    assert len(limiter) == 0
    assert "c1" not in limiter

    stats_after = limiter.get_stats()
    assert stats_after["allowed"] == stats_before["allowed"]


def test_len_and_contains_isolation():
    """Verify __len__ and __contains__ report active client state without side effects."""
    limiter = TokenBucketRateLimiter(capacity=5.0, refill_rate=1.0)
    assert len(limiter) == 0
    assert "c1" not in limiter
    assert len(limiter) == 0  # contains check must not add client to buckets

    limiter.allow_request("c1", cost=1.0)
    assert len(limiter) == 1
    assert "c1" in limiter


def test_concurrent_stress():
    """Verify thread safety under concurrent requests and quota adjustments."""
    limiter = TokenBucketRateLimiter(capacity=100.0, refill_rate=50.0)
    errors = []

    def worker_allow(client_idx):
        try:
            for i in range(20):
                limiter.allow_request(f"client_{client_idx}", cost=1.0)
        except Exception as e:
            errors.append(e)

    def worker_quota(client_idx):
        try:
            for i in range(5):
                limiter.set_client_quota(f"client_{client_idx}", capacity=50.0, refill_rate=20.0)
        except Exception as e:
            errors.append(e)

    threads = []
    for idx in range(4):
        threads.append(threading.Thread(target=worker_allow, args=(idx,)))
        threads.append(threading.Thread(target=worker_quota, args=(idx,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent execution errors: {errors}"
    assert len(limiter) <= 4


@settings(max_examples=10)
@given(
    st.lists(
        st.tuples(
            st.sampled_from(["allow", "refill"]),
            st.integers(min_value=1, max_value=5),
            st.floats(min_value=0.5, max_value=3.0)
        )
    )
)
def test_property_state_machine(operations):
    """Property-based state machine test against TokenBucketRateLimiter."""
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=10.0)
    for op, client_id, cost in operations:
        c_str = f"client_{client_id}"
        if op == "allow":
            res = limiter.allow_request(c_str, cost=cost)
            assert isinstance(res, bool)
        elif op == "refill":
            tokens = limiter.refill(c_str)
            assert tokens >= 0.0 and tokens <= 10.0
