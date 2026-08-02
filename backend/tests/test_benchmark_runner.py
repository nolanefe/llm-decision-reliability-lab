"""Tests for benchmark runner dry-run and live guardrails."""

import pytest

from app.benchmarks.plan import PORTFOLIO_BENCHMARK_V1
from app.benchmarks.runner import (
    BenchmarkConfigurationError,
    describe_benchmark_plan,
    run_live_benchmark,
)
from app.core.config import get_settings
from app.core.exceptions import ProviderUnavailableError
from app.db.seed import run_seed
from tests.fakes import ScriptedProvider, make_result

VALID_OUTPUT = (
    '{"category": "billing", "priority": "high", "summary": "s", '
    '"recommended_action": "a"}'
)


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch):
    monkeypatch.setitem(
        __import__("app.core.config", fromlist=["Settings"]).Settings.model_config,
        "env_file",
        None,
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def export_root(tmp_path, monkeypatch):
    monkeypatch.setattr("app.benchmarks.export.repo_root", lambda: tmp_path)
    return tmp_path


def test_describe_benchmark_plan_resolves_seed_ids(db_session):
    run_seed(db_session)
    summary = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)

    assert summary.planned_run_count == 16
    assert len(summary.dataset_item_ids) == 4
    assert len(summary.prompt_version_ids) == 2
    assert summary.openai_api_key_configured is False


def test_describe_benchmark_plan_with_unknown_dataset_names_raises(db_session):
    from app.benchmarks.plan import BenchmarkPlan

    run_seed(db_session)
    bad_plan = BenchmarkPlan(
        benchmark_id="bad-plan",
        experiment_name="bad",
        dataset_version="built-in-seed-v1",
        dataset_item_names=("nonexistent-dataset-item",),
        prompt_version_names=PORTFOLIO_BENCHMARK_V1.prompt_version_names,
        model_names=PORTFOLIO_BENCHMARK_V1.model_names,
        repeat_count=1,
    )
    with pytest.raises(BenchmarkConfigurationError, match="Missing dataset items"):
        describe_benchmark_plan(db_session, bad_plan)


def test_run_live_benchmark_without_api_key_raises(db_session, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    run_seed(db_session)

    with pytest.raises(ProviderUnavailableError, match="OPENAI_API_KEY"):
        run_live_benchmark(db_session, plan=PORTFOLIO_BENCHMARK_V1)


def test_run_live_benchmark_with_fake_provider(db_session, export_root):
    run_seed(db_session)
    dry_run = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)
    outcomes = [make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    provider = ScriptedProvider(outcomes=outcomes)

    result = run_live_benchmark(
        db_session,
        plan=PORTFOLIO_BENCHMARK_V1,
        provider=provider,
    )

    assert result.planned_runs == 16
    assert result.completed_runs == 16
    assert result.failed_runs == 0
    assert len(provider.calls) == 16

    export_dir = export_root / "benchmarks" / "results" / PORTFOLIO_BENCHMARK_V1.benchmark_id
    assert export_dir.exists()
