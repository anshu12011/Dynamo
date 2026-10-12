Author a test suite and diagnostic report for `TokenBucketRateLimiter`. Specifications are in `/app/RATE_LIMITER_SPEC.md`.

Module Selector (`/app/rate_limiter.py`):
- `LIMITER_MODULE` unset or `"reference"` loads reference implementation (`/app/rate_limiter_ref.py`).
- `LIMITER_MODULE=buggy` loads buggy implementation (`/app/rate_limiter_buggy.py`).
- `LIMITER_MODULE=mutants.mutant_01` .. `mutants.mutant_20` loads faulty variants (`/app/mutants/`).
- Execute `python /app/run_mutation_tests.py` to run mutation checks.

Deliverables in `/app`:

1. Primary Test Suite (`/app/test_limiter.py`):
   - Deliverable path: `/app/test_limiter.py` (must exist as a regular, non-symlink file directly inside `/app`).
   - Import class via: `from rate_limiter import TokenBucketRateLimiter`
   - Requirements:
     a. **Reference Compliance**: Must pass 100% against the reference implementation across multiple runs.
     b. **Held-Out Reference Resilience**: Must pass against reformatted and structurally modified reference implementations (e.g. alternative internal state representations or variable naming).
     c. **Bug Detection**: Must fail against the buggy implementation.
     d. **Mutation Resistance**: Must kill all 20 mutants (`python /app/run_mutation_tests.py`).
     e. **Strict Behavioral Black-Box Isolation**: Evaluate strictly via public API methods (`allow_request`, `refill`, `set_client_quota`, `get_stats`, `clear`, `__len__`, `__contains__`). Do not reference internal implementation module identifiers (`LIMITER_MODULE`, `rate_limiter_ref`, `rate_limiter_buggy`, `mutants.`), inspect private attributes (`_buckets`, `_lock`, `_allowed`, etc.), or use system/introspection/file-reading APIs (`inspect`, `dis`, `open()`, `__code__`, `__file__`, `__module__`, `__dict__`, `getsource`, `os`, `sys`, `scipy`, `subprocess`, etc.).
     f. **Execution Performance**: Each mutant test run must complete within 45 seconds.

2. Diagnostic Root Cause Assessment (`/app/root_cause.txt`):
   - Deliverable path: `/app/root_cause.txt` (must exist as a regular, non-symlink file directly inside `/app`).
   - Technical report (≥120 words total, ≥350 bytes total) analyzing `/app/rate_limiter_buggy.py`.
   - Structured into at least 4 distinct paragraphs separated by blank lines (one paragraph per defect).
   - Each paragraph must contain ≥25 words, ≥2 complete sentences ending with punctuation (`.`, `;`, `:`, `!`), structural connectives (`because`, `due`, `when`, `causes`, `results`, etc.), and ≥40% unique vocabulary ratio (no keyword-salad or repetitive padding).
   - Must detail each of the 4 defects discovered in `/app/rate_limiter_buggy.py` across 4 distinct paragraphs:
     - Name the specific buggy method where the defect occurs (e.g., `allow_request()`, `_refill_bucket()`, `set_client_quota()`).
     - Describe the incorrect code-level mechanism and specific flaw.
     - Explain the operational failure impact.
