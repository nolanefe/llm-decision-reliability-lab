"""Fixed, version-controlled portfolio benchmark definitions.

Each plan describes a small, bounded evaluation that reuses the built-in
seed dataset and prompt versions. Plans are intentionally small so a live
run stays inexpensive and reproducible.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkPlan:
    """A reproducible benchmark configuration."""

    benchmark_id: str
    experiment_name: str
    dataset_version: str
    dataset_item_names: tuple[str, ...]
    prompt_version_names: tuple[str, ...]
    model_names: tuple[str, ...]
    repeat_count: int

    @property
    def planned_run_count(self) -> int:
        return (
            len(self.dataset_item_names)
            * len(self.prompt_version_names)
            * len(self.model_names)
            * self.repeat_count
        )


PORTFOLIO_BENCHMARK_V1 = BenchmarkPlan(
    benchmark_id="portfolio-v1",
    experiment_name="Portfolio benchmark v1",
    dataset_version="built-in-seed-v1",
    dataset_item_names=(
        "billing-duplicate-charge",
        "account-locked-out",
        "bug-export-crash",
        "feature-request-dark-mode",
    ),
    prompt_version_names=(
        "baseline-triage",
        "explicit-criteria-triage",
    ),
    model_names=("gpt-5-mini",),
    repeat_count=2,
)

DEFAULT_BENCHMARK_PLAN = PORTFOLIO_BENCHMARK_V1
