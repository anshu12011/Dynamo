# TokenBucketRateLimiter Specification

`TokenBucketRateLimiter` is a thread-safe, continuous token-bucket rate limiter designed for API gateways and microservice request throttling.

## Public Interface

### Initialization
`TokenBucketRateLimiter(capacity: float, refill_rate: float, default_tier: str = "standard")`
- `capacity`: Maximum token capacity per bucket (must be `int` or `float` > 0; raises `ValueError` otherwise).
- `refill_rate`: Refill speed in tokens per second (must be `int` or `float` > 0; raises `ValueError` otherwise).
- `default_tier`: Default client tier label (default `"standard"`).

### Core Operations

`allow_request(client_id: str, cost: float = 1.0) -> bool`
- Evaluates whether `client_id` has at least `cost` tokens available.
- Automatically calculates continuous time-based token refill (`tokens += elapsed_seconds * refill_rate`, capped at client `capacity`) using `time.monotonic()`.
- Raises `ValueError` if `cost` is not numeric or `cost <= 0`.
- **If tokens >= cost**: Deducts `cost` tokens from the bucket, updates last activity timestamp, increments cumulative `allowed` count by 1, and returns `True`.
- **If tokens < cost**: Leaves bucket tokens UNCHANGED (no token leak on rejection!), updates last activity timestamp, increments cumulative `blocked` count by 1, and returns `False`.

`refill(client_id: str) -> float`
- Triggers an explicit refill calculation for `client_id` based on fractional seconds elapsed since last update.
- Increments cumulative `refills` count by 1.
- Returns current available tokens (capped at `capacity`).

`set_client_quota(client_id: str, capacity: float, refill_rate: float) -> None`
- Overrides the default capacity and refill rate for a specific `client_id`.
- Raises `ValueError` if `capacity <= 0` or `refill_rate <= 0`.
- Must execute atomically under lock protection.
- Increments cumulative `reconfigurations` count by 1.

`get_stats() -> Dict[str, int]`
- Returns a dictionary containing cumulative statistics: `{"allowed": int, "blocked": int, "refills": int, "reconfigurations": int}`.

`clear() -> None`
- Clears all active client buckets while preserving cumulative statistics.

`__len__() -> int`
- Returns the count of active client buckets currently tracked.

`__contains__(client_id: str) -> bool`
- Returns `True` if `client_id` has an active bucket, `False` otherwise. Does NOT mutate tokens or statistics.

## Concurrency Requirements
All public operations must be thread-safe under multi-threaded execution. Lock protection must encompass entire operations to guarantee atomicity and prevent race conditions.
