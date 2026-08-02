"""Tests for benchmark plan bounds and configuration."""

from app.benchmarks.plan import DEFAULT_BENCHMARK_PLAN, PORTFOLIO_BENCHMARK_V1
from app.core.config import get_settings


def test_portfolio_benchmark_planned_run_count_is_bounded():
    plan = PORTFOLIO_BENCHMARK_V1
    assert plan.planned_run_count == 16
    assert len(plan.dataset_item_names) == 4
    assert len(plan.prompt_version_names) == 2
    assert len(plan.model_names) == 1
    assert plan.repeat_count == 2


def test_default_benchmark_plan_is_portfolio_v1():
    assert DEFAULT_BENCHMARK_PLAN is PORTFOLIO_BENCHMARK_V1


def test_planned_runs_within_max_runs_per_experiment():
    get_settings.cache_clear()
    settings = get_settings()
    assert PORTFOLIO_BENCHMARK_V1.planned_run_count <= settings.max_runs_per_experiment
    get_settings.cache_clear()
