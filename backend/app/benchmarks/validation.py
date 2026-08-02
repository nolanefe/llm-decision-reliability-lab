"""Safe benchmark identifier validation for filesystem paths."""

import re

BENCHMARK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class InvalidBenchmarkIdError(ValueError):
    """Raised when a benchmark id is unsafe or does not match the convention."""


def validate_benchmark_id(benchmark_id: str) -> str:
    """Validate ``benchmark_id`` for use as a single path segment.

    Allowed: lowercase letters, digits, hyphens; must start with a letter
    or digit. Rejects path separators, ``..``, whitespace, and uppercase.
    """
    if not isinstance(benchmark_id, str):
        raise InvalidBenchmarkIdError("benchmark_id must be a string")
    candidate = benchmark_id.strip()
    if candidate != benchmark_id or not candidate:
        raise InvalidBenchmarkIdError(
            "benchmark_id must be non-empty and must not contain leading or trailing whitespace"
        )
    if "/" in candidate or "\\" in candidate or ".." in candidate:
        raise InvalidBenchmarkIdError(
            "benchmark_id must not contain path separators or parent-directory segments"
        )
    if not BENCHMARK_ID_PATTERN.fullmatch(candidate):
        raise InvalidBenchmarkIdError(
            "benchmark_id must match ^[a-z0-9][a-z0-9-]*$ (lowercase letters, "
            "digits, and hyphens only)"
        )
    return candidate
