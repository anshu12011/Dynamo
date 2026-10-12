# Task: Mutation-Resistant Test Suite for a Concurrent TTL-Aware LRU Cache

## Overview
This task evaluates an agent's ability to design a mutation-resistant, concurrent black-box test suite and perform root-cause defect analysis for a thread-safe, TTL-aware Least-Recently-Used (LRU) cache (`TTLLRUCache`).

Rather than fixing code, the candidate must write a test suite that constrains cache behavior tightly enough to detect subtle defects and kill seeded mutants while passing 100% against a correct reference implementation.

## Key Requirements & Output Files
1. `/app/test_cache.py`:
   - A complete `pytest` suite testing `TTLLRUCache` via `from lru_cache import TTLLRUCache`.
   - **Reference Compliance**: 100% pass against the correct reference implementation (`CACHE_MODULE=lru_cache_ref`).
   - **Bug Detection**: Must fail against the provided buggy implementation (`CACHE_MODULE=lru_cache_buggy`).
   - **Mutation Score**: Must achieve a mutant kill rate of **>= 90.0%** (killing at least 18 of 20 independently seeded mutants in `/app/mutants/`).

2. `/app/root_cause.txt`:
   - A root-cause report identifying the 4 seeded defects in `/app/lru_cache_buggy.py`:
     1. Recency mutation on expired `get()`.
     2. MRU eviction instead of LRU eviction on capacity overflow.
     3. Non-strict inequality in TTL expiration boundary checks (`now > expire_at`).
     4. Non-atomic lock release during `cleanup_expired()` sweeps.

## Environment & Architecture
- **Base Image**: `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- **Dependencies**: `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `hypothesis==6.112.0` (baked into Dockerfile).
- **Environment Files** (`/app/`):
  - `CACHE_SPEC.md`: Full technical contract for `TTLLRUCache`.
  - `lru_cache_ref.py`: Correct reference implementation.
  - `lru_cache_buggy.py`: Buggy implementation containing seeded defects.
  - `lru_cache.py`: Module router respecting `CACHE_MODULE`.
  - `mutants/`: 20 mutated implementations covering boundary, recency, state, and concurrency bugs.
  - `run_mutation_tests.py`: Local mutation analysis runner.

## Reference Solution
- `/solution/solve.sh` calls `/solution/solve.py`, which generates `/app/test_cache.py` (unit, boundary, metrics, and multi-threaded stress tests) and `/app/root_cause.txt`.

## Verification (`/tests/test_outputs.py`)
- **Path Protection**: Validates `/app/test_cache.py` and `/app/root_cause.txt` exist as regular, non-symlink files within `/app`.
- **Reference Gate**: Requires 100% pass across multiple runs against `lru_cache_ref`.
- **Bug Detection Gate**: Confirms test suite fails against `lru_cache_buggy`.
- **Root Cause Gate**: Verifies `/app/root_cause.txt` describes all 4 buggy defects.
- **Mutation Gate**: Confirms mutant kill rate >= 90.0% across all 20 seeded mutants.
