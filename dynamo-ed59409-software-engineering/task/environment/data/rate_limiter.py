"""Application wrapper for TokenBucketRateLimiter implementation selection."""

import os
import importlib

module_name = os.environ.get("LIMITER_MODULE", "reference")

if module_name in ("reference", "", None):
    from rate_limiter_ref import TokenBucketRateLimiter
elif module_name == "buggy":
    from rate_limiter_buggy import TokenBucketRateLimiter
elif module_name.startswith("mutants."):
    mod = importlib.import_module(module_name)
    TokenBucketRateLimiter = mod.TokenBucketRateLimiter
else:
    raise ValueError(f"Unknown LIMITER_MODULE setting: {module_name}")

__all__ = ["TokenBucketRateLimiter"]
