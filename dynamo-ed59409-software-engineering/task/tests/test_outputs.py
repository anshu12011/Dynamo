"""Trusted rate limiter implementations used exclusively by the verifier.

These sources intentionally live under ``tests/`` so an agent can use the
development copies in /app without being able to alter the grading oracle.
"""

REFERENCE = '''import time
import threading
from typing import Dict, Any, Optional


class TokenBucketRateLimiter:
    def __init__(self, capacity: float, refill_rate: float, default_tier: str = "standard"):
        if not isinstance(capacity, (int, float)) or capacity <= 0:
            raise ValueError("Capacity must be > 0")
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
        if not isinstance(capacity, (int, float)) or capacity <= 0:
            raise ValueError("Capacity must be > 0")
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
'''


def source_for(name: str) -> str:
    """Return a fresh, independently trusted reference or one seeded mutant."""
    source = REFERENCE
    if name == "reference":
        return source
    if name == "buggy":
        source = source.replace("elapsed = now - last_time", "elapsed = int(now - last_time)")
        source = source.replace("tokens = min(cap, tokens + elapsed * rate)", "tokens = min(cap + 10.0, tokens + elapsed * rate)")
        source = source.replace(
            "            tokens = bucket[0]\n\n            if tokens >= cost:\n                bucket[0] = tokens - float(cost)",
            "            bucket[0] -= float(cost)\n\n            if bucket[0] >= 0:",
        )
        source = source.replace(
            "        now = time.monotonic()\n        with self._lock:\n            bucket = self._refill_bucket(client_id, now)\n            tokens = min(float(capacity), bucket[0])\n            self._buckets[client_id] = [tokens, float(capacity), float(refill_rate), now]\n            self._reconfigurations += 1",
            "        now = time.monotonic()\n        with self._lock:\n            bucket = self._refill_bucket(client_id, now)\n        tokens = min(float(capacity), bucket[0])\n        self._buckets[client_id] = [tokens, float(capacity), float(refill_rate), now]\n        self._reconfigurations += 1",
        )
        return source

    mutation = int(name.removeprefix("mutant_"))
    if mutation == 1:
        return source.replace("capacity <= 0", "capacity < 0", 1)
    if mutation == 2:
        return source.replace("if tokens >= cost:", "if tokens > cost:", 1)
    if mutation == 3:
        return source.replace("return True", "return True", 1).replace("return False", "return True", 1)
    if mutation == 4:
        return source.replace("bucket[0] = tokens - float(cost)", "pass", 1)
    if mutation == 5:
        return source.replace("self._blocked += 1\n                return False", "bucket[0] -= float(cost)\n                self._blocked += 1\n                return False", 1)
    if mutation == 6:
        return source.replace("tokens = min(cap, tokens + elapsed * rate)", "tokens = max(cap, tokens + elapsed * rate)", 1)
    if mutation == 7:
        return source.replace("elapsed = now - last_time", "elapsed = int(now - last_time)", 1)
    if mutation == 8:
        return source.replace("self._allowed += 1", "pass", 1).replace("self._blocked += 1", "pass", 1)
    if mutation == 9:
        return source.replace("        with self._lock:\n            bucket = self._refill_bucket(client_id, now)\n            tokens = min(float(capacity), bucket[0])\n            self._buckets[client_id] = [tokens, float(capacity), float(refill_rate), now]\n            self._reconfigurations += 1", "        bucket = self._refill_bucket(client_id, now)\n        tokens = min(float(capacity), bucket[0])\n        self._buckets[client_id] = [tokens, float(capacity), float(refill_rate), now]\n        self._reconfigurations += 1", 1)
    if mutation == 10:
        return source.replace("tokens = min(float(capacity), bucket[0])", "tokens = float(capacity)", 1)
    if mutation == 11:
        return source.replace("        if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:\n            raise ValueError(\"Refill rate must be > 0\")\n", "", 1)
    if mutation == 12:
        return source.replace("        if not isinstance(cost, (int, float)) or cost <= 0:\n            raise ValueError(\"Cost must be > 0\")\n", "", 1)
    if mutation == 13:
        return source.replace("            self._buckets.clear()", "            self._buckets.clear()\n            self._allowed = self._blocked = self._refills = self._reconfigurations = 0", 1)
    if mutation == 14:
        return source.replace("return len(self._buckets)", "return 0", 1)
    if mutation == 15:
        return source.replace("return client_id in self._buckets", "self._buckets[client_id] = [self.capacity, self.capacity, self.refill_rate, time.monotonic()]\n            return True", 1)
    if mutation == 16:
        return source.replace(
            "        with self._lock:\n            bucket = self._refill_bucket(client_id, now)\n            tokens = bucket[0]\n\n            if tokens >= cost:\n                bucket[0] = tokens - float(cost)\n                self._allowed += 1\n                return True\n            else:\n                self._blocked += 1\n                return False",
            "        bucket = self._refill_bucket(client_id, now)\n        tokens = bucket[0]\n\n        if tokens >= cost:\n            bucket[0] = tokens - float(cost)\n            self._allowed += 1\n            return True\n        else:\n            self._blocked += 1\n            return False",
            1
        )
    if mutation == 17:
        return source.replace("self._refills += 1", "pass", 1)
    if mutation == 18:
        return source.replace("self._reconfigurations += 1", "pass", 1)
    if mutation == 19:
        return source.replace("        if not isinstance(capacity, (int, float)) or capacity <= 0:\n            raise ValueError(\"Capacity must be > 0\")\n", "", 2)
    if mutation == 20:
        return source.replace("now = time.monotonic()", "now = time.time()", 1)

    raise ValueError(f"Unknown fixture: {name}")


"""Verifier test suite for validating the TokenBucketRateLimiter task outputs."""

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest



APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
TEST_FILE = APP_ROOT / "test_limiter.py"
ROOT_CAUSE_FILE = APP_ROOT / "root_cause.txt"


def _safe_output_path(path: Path) -> Path:
    """Validate that required artifact exists as a regular, non-symlink file inside /app."""
    assert path.exists(), f"Target deliverable is missing: {path}"
    assert path.is_file(), f"Target deliverable must be a standard file: {path}"
    assert not path.is_symlink() and not os.path.islink(path), f"Symbolic links are prohibited: {path}"
    resolved = path.resolve()
    assert not resolved.is_symlink() and not os.path.islink(resolved), f"Symbolic links are prohibited: {resolved}"
    app_resolved = APP_ROOT.resolve()
    assert not APP_ROOT.is_symlink() and not os.path.islink(APP_ROOT), "Base directory cannot be a symbolic link."
    try:
        resolved.relative_to(app_resolved)
    except ValueError:
        pytest.fail(f"Path traversal outside root directory detected: {resolved}")
    assert resolved.parent == app_resolved, f"Artifact must reside directly within {APP_ROOT}: {resolved}"
    return resolved


def _assert_suite_does_not_select_implementation(test_path: Path) -> None:
    """Ensure candidate suite relies on public API contract rather than implementation introspection."""
    source = test_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test_path))
    forbidden_names = {"LIMITER_MODULE", "rate_limiter_ref", "rate_limiter_buggy", "mutants."}
    string_literals = [node.value for node in ast.walk(tree)
                       if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    offenders = [value for value in string_literals if any(name in value for name in forbidden_names)]
    assert not offenders, (
        "test_limiter.py must evaluate TokenBucketRateLimiter strictly through behavioral tests "
        f"and may not reference implementation module names: {offenders[:3]}"
    )

    forbidden_modules = {
        "inspect", "dis", "marshal", "importlib", "pkgutil", "runpy", "tokenize",
        "os", "io", "builtins", "pathlib", "sys", "types", "linecache", "traceback",
        "code", "codeop", "site", "shutil", "tempfile", "glob", "fnmatch", "gc",
        "scipy", "subprocess", "ctypes", "socket", "urllib", "requests", "multiprocessing",
        "signal", "asyncio", "tracemalloc", "resource",
    }
    forbidden_calls = {
        "getattr", "setattr", "delattr", "vars", "dir", "globals", "locals",
        "eval", "exec", "compile", "__import__", "open", "read", "readline", "readlines",
    }
    forbidden_attributes = {
        "__code__", "__file__", "__loader__", "__module__", "__spec__",
        "__dict__", "__getattribute__", "getsource", "getsourcefile",
        "getsourcelines", "getmembers", "getfile", "co_code", "co_consts",
        "__wrapped__", "__qualname__", "__func__", "read_text", "read_bytes",
        "open", "read", "readline", "readlines", "open_code",
        "_buckets", "_lock", "_allowed", "_blocked", "_refills", "_reconfigurations",
    }
    forbidden_path_strings = {"limiter_under_test", "rate_limiter.py", "__file__", "mutant"}
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = [alias.name.split(".")[0] for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                module_names.append(node.module.split(".")[0])
            violations.extend(name for name in module_names if name in forbidden_modules)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                violations.append(node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_calls:
                violations.append(node.func.attr)
        elif isinstance(node, ast.Attribute):
            if node.attr in forbidden_attributes:
                violations.append(node.attr)

    for literal in string_literals:
        for pattern in forbidden_path_strings:
            if pattern in literal:
                violations.append(f"string containing '{pattern}'")

    assert not violations, (
        "test_limiter.py must enforce pure black-box isolation: source inspection, AST analysis, "
        f"and module introspection APIs are strictly prohibited ({sorted(set(violations))[:5]})."
    )


def _make_reference_alt() -> str:
    """Generate a functionally identical reference implementation with modified internal formatting."""
    source = source_for("reference")
    alt = source.replace("prev_ts", "last_update_ts")
    alt = alt.replace("_state_store", "_client_balances")
    alt = alt.replace("time_delta > 0", "not (time_delta <= 0)")
    alt = alt.replace("balance >= cost", "not (balance < cost)")

    alt = re.sub(r'"""[\s\S]*?"""', '', alt)
    alt = re.sub(r'#.*', '', alt)

    lines = []
    for line in alt.splitlines():
        if line.startswith("    "):
            leading = len(line) - len(line.lstrip(' '))
            new_leading = (leading // 4) * 2
            lines.append(" " * new_leading + line.lstrip(' '))
        else:
            lines.append(line)
    return "\n".join(lines)


def _make_reference_alt2() -> str:
    """Generate a second held-out reference implementation using dictionary-based internal state representation.

    This ensures test suites cannot hardcode or rely on internal list indexing (e.g. bucket[0])
    or private attribute names, enforcing pure black-box testing against observable API behavior.
    """
    source = source_for("reference")
    alt = source.replace("bucket = [self.capacity, self.capacity, self.refill_rate, now]",
                         'bucket = {"tokens": self.capacity, "cap": self.capacity, "rate": self.refill_rate, "ts": now}')
    alt = alt.replace("tokens, cap, rate, last_time = bucket",
                         'tokens, cap, rate, last_time = bucket["tokens"], bucket["cap"], bucket["rate"], bucket["ts"]')
    alt = alt.replace("bucket[0] = tokens", 'bucket["tokens"] = tokens')
    alt = alt.replace("bucket[3] = now", 'bucket["ts"] = now')
    alt = alt.replace("tokens = bucket[0]", 'tokens = bucket["tokens"]')
    alt = alt.replace("bucket[0] = tokens - float(cost)", 'bucket["tokens"] = tokens - float(cost)')
    alt = alt.replace("return bucket[0]", 'return bucket["tokens"]')
    alt = alt.replace("tokens = min(float(capacity), bucket[0])", 'tokens = min(float(capacity), bucket["tokens"])')
    alt = alt.replace("self._buckets[client_id] = [tokens, float(capacity), float(refill_rate), now]",
                         'self._buckets[client_id] = {"tokens": tokens, "cap": float(capacity), "rate": float(refill_rate), "ts": now}')
    alt = alt.replace("self._buckets", "self._client_state_store")
    alt = alt.replace("self._lock", "self._concurrency_mutex")
    return alt


def _run_suite_against(test_path: Path, fixture: str) -> subprocess.CompletedProcess[str]:
    """Execute candidate test suite against a selected implementation in an isolated directory."""
    with tempfile.TemporaryDirectory(prefix="limiter-verification-") as directory:
        sandbox = Path(directory)
        candidate = sandbox / "test_limiter.py"
        shutil.copy2(test_path, candidate)
        (sandbox / "limiter_under_test.py").write_text(source_for(fixture), encoding="utf-8")
        (sandbox / "rate_limiter.py").write_text(
            "from limiter_under_test import TokenBucketRateLimiter\n\n__all__ = ['TokenBucketRateLimiter']\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env.pop("LIMITER_MODULE", None)
        env["PYTHONPATH"] = str(sandbox)
        return subprocess.run(
            [sys.executable, "-m", "pytest", str(candidate), "-q", "--tb=short"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=sandbox,
            timeout=45,
        )


def _run_suite_against_source(test_path: Path, impl_source: str) -> subprocess.CompletedProcess[str]:
    """Execute candidate test suite against custom implementation source text."""
    with tempfile.TemporaryDirectory(prefix="limiter-verification-") as directory:
        sandbox = Path(directory)
        candidate = sandbox / "test_limiter.py"
        shutil.copy2(test_path, candidate)
        (sandbox / "limiter_under_test.py").write_text(impl_source, encoding="utf-8")
        (sandbox / "rate_limiter.py").write_text(
            "from limiter_under_test import TokenBucketRateLimiter\n\n__all__ = ['TokenBucketRateLimiter']\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env.pop("LIMITER_MODULE", None)
        env["PYTHONPATH"] = str(sandbox)
        return subprocess.run(
            [sys.executable, "-m", "pytest", str(candidate), "-q", "--tb=short"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=sandbox,
            timeout=45,
        )


def _split_into_paragraphs(text: str) -> list[str]:
    """Parse text document into distinct paragraph blocks separated by blank lines."""
    parts = re.split(r'\n\s*\n', text)
    return [p.strip() for p in parts if p.strip()]


def _paragraph_has_explanation(paragraph: str, method_keywords: list[str],
                                primary_keywords: list[str],
                                context_keywords: list[str],
                                correctness_patterns: list[str],
                                negation_patterns: list[str] | None = None,
                                min_words: int = 25) -> bool:
    """Evaluate whether a paragraph contains a valid, directionally accurate defect explanation."""
    lower = paragraph.lower()
    words = lower.split()
    if len(words) < min_words:
        return False
    has_method = any(kw in lower for kw in method_keywords)
    if not has_method:
        return False
    if not any(re.search(pattern, lower, re.DOTALL) for pattern in correctness_patterns):
        return False

    if negation_patterns and any(
        re.search(pat, lower, re.DOTALL) for pat in negation_patterns
    ):
        return False

    # Enforce minimum 40% unique vocabulary ratio
    unique_words = set(words)
    uniqueness_ratio = len(unique_words) / len(words) if words else 0
    if uniqueness_ratio < 0.40:
        return False

    # Reject word padding / keyword salad (no single non-stopword > 10% of total words, no repeated consecutive words)
    structure_words = {"the", "to", "in", "of", "a", "an", "is", "was", "for",
                       "with", "by", "from", "as", "at", "on", "it", "this", "that", "and", "or"}
    word_counts: dict[str, int] = {}
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[\W_]+', '', w)
        if clean_w:
            word_counts[clean_w] = word_counts.get(clean_w, 0) + 1
            if clean_w not in structure_words and word_counts[clean_w] > max(3, int(len(words) * 0.10)):
                return False  # Over-repeated non-stopword padding
        if idx > 0 and w == words[idx - 1] and w not in structure_words:
            return False  # Consecutive word repetition padding

    connectives = ["because", "due", "when", "causes", "results", "leads", "where",
                   "after", "before", "instead", "prior", "incorrectly", "fails",
                   "resulting", "causing", "updating", "evicting", "calling",
                   "executing", "evaluating", "releasing", "retaining", "modifying",
                   "rather", "using", "equals", "treated", "violating", "updates",
                   "requires", "performs", "returns", "checks", "verifying", "subtracting",
                   "deducting", "draining", "calculating", "underflow", "exceeding"]

    has_structure = sum(1 for w in words if w in structure_words) >= 2
    has_connective = any(c in lower for c in connectives)
    has_punctuation = sum(1 for p in paragraph if p in [".", ";", ":", "!"]) >= 2

    if not (has_structure and has_connective and has_punctuation):
        return False
    return True


def test_scored_output_files_exist_and_are_regular():
    """Verify deliverable files exist as regular non-symlink files in /app."""
    test_path = _safe_output_path(TEST_FILE)
    report_path = _safe_output_path(ROOT_CAUSE_FILE)
    assert test_path.is_file(), f"{TEST_FILE} must be a regular file"
    assert report_path.is_file(), f"{ROOT_CAUSE_FILE} must be a regular file"


def test_root_cause_report_size():
    """Verify report deliverable satisfies minimum byte length constraints."""
    test_path = _safe_output_path(TEST_FILE)
    report_path = _safe_output_path(ROOT_CAUSE_FILE)
    assert test_path.stat().st_size > 0, f"{TEST_FILE} cannot be empty"
    assert report_path.stat().st_size >= 350, f"{ROOT_CAUSE_FILE} must be at least 350 bytes"


def test_suite_uses_black_box_isolation():
    """Verify test_limiter.py respects black-box behavioral testing rules."""
    test_path = _safe_output_path(TEST_FILE)
    _assert_suite_does_not_select_implementation(test_path)


def test_reference_implementation_passes_repeatedly():
    """Verify suite passes 100% against reference implementation across 3 iterations."""
    test_path = _safe_output_path(TEST_FILE)
    for run in range(3):
        result = _run_suite_against(test_path, "reference")
        assert result.returncode == 0, (
            f"Reference run {run + 1} failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def test_reference_alt_formatting_passes():
    """Verify test suite passes against a reformatted reference implementation."""
    test_path = _safe_output_path(TEST_FILE)
    alt_source = _make_reference_alt()
    result = _run_suite_against_source(test_path, alt_source)
    assert result.returncode == 0, (
        "test_limiter.py failed against a reformatted (but behaviourally identical) "
        "reference implementation. This indicates reliance on source text patterns "
        "rather than public contract verification.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_reference_alt2_formatting_passes():
    """Verify test suite passes against a structurally-modified, dict-backed reference implementation."""
    test_path = _safe_output_path(TEST_FILE)
    alt2_source = _make_reference_alt2()
    result = _run_suite_against_source(test_path, alt2_source)
    assert result.returncode == 0, (
        "test_limiter.py failed against a structurally-modified reference implementation. "
        "This indicates reliance on private attribute names or internal list structures "
        "rather than public contract verification.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_buggy_implementation_is_detected_by_behavior():
    """Verify test suite detects failure when executed against the buggy implementation."""
    result = _run_suite_against(_safe_output_path(TEST_FILE), "buggy")
    assert result.returncode != 0, "The suite did not detect the defective rate limiter."


def test_root_cause_report_explains_distinct_mechanisms():
    """Verify root_cause.txt contains substantive per-defect analysis matching code-level defects."""
    content = _safe_output_path(ROOT_CAUSE_FILE).read_text(encoding="utf-8")
    total_words = len(content.split())
    assert total_words >= 120, (
        f"The root-cause report has only {total_words} words; "
        f"at least 120 words of substantive analysis are required."
    )

    paragraphs = _split_into_paragraphs(content)
    assert len(paragraphs) >= 4, (
        f"The root-cause report has only {len(paragraphs)} paragraph(s). "
        f"Each of the 4 defects must be explained in its own paragraph."
    )

    # Defect 1: Token credit leak on rejected request — must reference allow_request()
    # Requires code-level specifics: the subtraction happens before the >= 0 check (bucket[0] -= cost before bucket[0] >= 0)
    defect1 = any(
        _paragraph_has_explanation(
            p,
            method_keywords=["allow_request(", "allow_request()", ".allow_request", "def allow_request"],
            primary_keywords=["token", "leak", "deduct", "subtract", "credit"],
            context_keywords=["reject", "block", "before", "prior", "false"],
            correctness_patterns=[
                r"bucket\[0\]\s*-=",
                r"bucket\[0\]\s*-\s*float\(cost\)",
                r"-\s*float\(cost\)",
                r"bucket\[0\]\s*-\s*cost",
                r"bucket\[0\]",
            ],
            negation_patterns=None,
        )
        for p in paragraphs
    )
    assert defect1, (
        "root_cause.txt must contain a substantive paragraph (>= 25 words, >= 40% unique) "
        "explaining the token credit leak on rejected requests in allow_request(). "
        "Reference allow_request and the token deduction (bucket[0] -= cost) before validation."
    )

    # Defect 2: Integer elapsed seconds underflow — must reference _refill_bucket() or refill
    # Requires code-level specifics: int(now - last_time) truncates fractional sub-second elapsed
    defect2 = any(
        _paragraph_has_explanation(
            p,
            method_keywords=["_refill_bucket", "refill(", "refill()", ".refill"],
            primary_keywords=["integer", "int(", "underflow", "elapsed"],
            context_keywords=["fractional", "sub-second", "millisecond", "second", "time"],
            correctness_patterns=[
                r"int\(now\s*-\s*last_time\)",
                r"int\(now",
                r"int\(.{0,40}\)",
                r"int\(elapsed\)",
            ],
            negation_patterns=None,
        )
        for p in paragraphs
    )
    assert defect2, (
        "root_cause.txt must contain a substantive paragraph (>= 25 words, >= 40% unique) "
        "explaining the integer elapsed seconds underflow defect in _refill_bucket(). "
        "Reference the int(now - last_time) truncation that discards sub-second fractional elapsed time."
    )

    # Defect 3: Refill capacity overflow — must reference _refill_bucket() or capacity
    # Requires code-level specifics: min(cap + 10.0, ...) — the + 10.0 offset that allows overflow
    defect3 = any(
        _paragraph_has_explanation(
            p,
            method_keywords=["_refill_bucket", "capacity", "refill"],
            primary_keywords=["overflow", "exceed", "limit", "+ 10", "10.0"],
            context_keywords=["maximum", "bucket", "capacity", "min("],
            correctness_patterns=[
                r"cap\s*\+\s*10",
                r"min\(cap\s*\+\s*10",
                r"\+\s*10\.0",
                r"cap\s*\+\s*10\.0",
            ],
            negation_patterns=None,
        )
        for p in paragraphs
    )
    assert defect3, (
        "root_cause.txt must contain a substantive paragraph (>= 25 words, >= 40% unique) "
        "explaining the refill capacity overflow defect in _refill_bucket(). "
        "Reference the min(cap + 10.0, ...) expression that allows buckets to exceed maximum capacity."
    )

    # Defect 4: Non-atomic lock release in quota reconfiguration — must reference set_client_quota()
    # Requires code-level specifics: self._lock released inside 'with self._lock:' block before bucket assignment
    defect4 = any(
        _paragraph_has_explanation(
            p,
            method_keywords=["set_client_quota(", "set_client_quota()", ".set_client_quota", "set_client_quota"],
            primary_keywords=["lock", "atomic", "non-atomic"],
            context_keywords=["release", "race", "concurrent", "thread", "unprotected"],
            correctness_patterns=[
                r"with\s+self\._lock:",
                r"self\._lock",
            ],
            negation_patterns=None,
        )
        for p in paragraphs
    )
    assert defect4, (
        "root_cause.txt must contain a substantive paragraph (>= 25 words, >= 40% unique) "
        "explaining the non-atomic concurrency lock release in set_client_quota(). "
        "Reference self._lock being released before the bucket dictionary assignment completes."
    )

    defect_matches = []
    for i, p in enumerate(paragraphs):
        lower = p.lower()
        matches = set()
        if any(kw in lower for kw in ["allow_request(", "allow_request()", ".allow_request", "allow_request"]) and \
           any(kw in lower for kw in ["token", "leak", "deduct", "subtract", "credit"]):
            matches.add("defect1")
        if any(kw in lower for kw in ["_refill_bucket", "refill(", "refill()", ".refill"]) and \
           any(kw in lower for kw in ["integer", "int(", "underflow", "elapsed"]):
            matches.add("defect2")
        if any(kw in lower for kw in ["_refill_bucket", "capacity", "refill"]) and \
           any(kw in lower for kw in ["overflow", "exceed", "limit", "+ 10", "10.0"]):
            matches.add("defect3")
        if any(kw in lower for kw in ["set_client_quota(", "set_client_quota()", ".set_client_quota", "set_client_quota"]) and \
           any(kw in lower for kw in ["lock", "atomic", "non-atomic"]):
            matches.add("defect4")
        if matches:
            defect_matches.append((i, matches))

    covered_defects = set()
    distinct_paragraphs = set()
    for p_idx, matches in defect_matches:
        covered_defects.update(matches)
        distinct_paragraphs.add(p_idx)
    assert len(covered_defects) >= 4 and len(distinct_paragraphs) >= 4, (
        f"The root-cause report must cover all 4 defects across at least 4 distinct paragraphs. "
        f"Found {len(covered_defects)} defect category match(es) across {len(distinct_paragraphs)} distinct paragraph(s)."
    )


def test_mutation_kill_rate():
    """Verify test suite kills 100% (20 of 20) of seeded mutants."""
    test_path = _safe_output_path(TEST_FILE)
    killed, survived = [], []
    for index in range(1, 21):
        name = f"mutant_{index:02d}"
        result = _run_suite_against(test_path, name)
        (killed if result.returncode else survived).append(name)

    assert len(killed) == 20, (
        f"Mutation score {len(killed)}/20 is below the 20/20 requirement. "
        f"Surviving mutants: {survived}"
    )

