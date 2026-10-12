"""Dynamic module selector for TTLLRUCache testing."""

import importlib
import os

_module_name = os.environ.get("CACHE_MODULE", "lru_cache_ref")
if _module_name in ("reference", "ref"):
    _module_name = "lru_cache_ref"
elif _module_name == "buggy":
    _module_name = "lru_cache_buggy"

_mod = importlib.import_module(_module_name)
TTLLRUCache = _mod.TTLLRUCache
