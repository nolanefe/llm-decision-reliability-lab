"""Tests for benchmark_id path validation."""

import pytest

from app.benchmarks.validation import InvalidBenchmarkIdError, validate_benchmark_id


@pytest.mark.parametrize(
    "benchmark_id",
    [
        "portfolio-v1",
        "v1",
        "a",
        "benchmark-2026-08",
    ],
)
def test_validate_benchmark_id_accepts_safe_ids(benchmark_id: str) -> None:
    assert validate_benchmark_id(benchmark_id) == benchmark_id


@pytest.mark.parametrize(
    "benchmark_id",
    [
        "../escape",
        "..",
        "portfolio/../v1",
        "/tmp/escape",
        "Portfolio-V1",
        "has space",
        "",
        "   ",
        "bad_chars!",
    ],
)
def test_validate_benchmark_id_rejects_unsafe_ids(benchmark_id: str) -> None:
    with pytest.raises(InvalidBenchmarkIdError):
        validate_benchmark_id(benchmark_id)
