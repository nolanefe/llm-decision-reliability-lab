"""Mixed-outcome benchmark aggregation test."""

import json

import pytest

from app.benchmarks.plan import BenchmarkPlan
from app.benchmarks.runner import run_live_benchmark
from app.core.config import get_settings
from app.db.seed import run_seed
from app.llm.provider import ProviderError, ProviderTimeoutError
from app.models.enums import FailureCategory, RunStatus
from app.models.evaluation import Evaluation
from app.models.run import Run
from tests.fakes import ScriptedProvider, make_result

MIXED_OUTCOMES_PLAN = BenchmarkPlan(
    benchmark_id="mixed-outcomes-test",
    experiment_name="Mixed outcomes benchmark test",
    dataset_version="built-in-seed-v1",
    dataset_item_names=("billing-duplicate-charge",),
    prompt_version_names=("baseline-triage",),
    model_names=("gpt-5-mini",),
    repeat_count=6,
)

CORRECT_OUTPUT = (
    '{"category": "billing", "priority": "high", "summary": "s", '
    '"recommended_action": "a"}'
)
MISMATCHED_OUTPUT = (
    '{"category": "bug", "priority": "low", "summary": "s", '
    '"recommended_action": "a"}'
)
SCHEMA_INVALID_OUTPUT = (
    '{"category": "not_a_category", "priority": "low", "summary": "s", '
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


def test_mixed_outcome_benchmark_aggregates_correctly(db_session, export_root):
    run_seed(db_session)
    outcomes = [
        ProviderError("provider failed"),
        ProviderTimeoutError("timed out"),
        make_result("not-json", input_tokens=10, output_tokens=20),
        make_result(SCHEMA_INVALID_OUTPUT, input_tokens=11, output_tokens=21),
        make_result(CORRECT_OUTPUT, input_tokens=12, output_tokens=22),
        make_result(MISMATCHED_OUTPUT, input_tokens=13, output_tokens=23),
    ]
    provider = ScriptedProvider(outcomes=outcomes)

    result = run_live_benchmark(
        db_session,
        plan=MIXED_OUTCOMES_PLAN,
        provider=provider,
    )

    assert result.planned_runs == 6
    assert result.completed_runs == 4
    assert result.failed_runs == 2
    assert len(provider.calls) == 6

    runs = db_session.query(Run).order_by(Run.id).all()
    assert len(runs) == 6
    assert sum(1 for run in runs if run.status == RunStatus.COMPLETED) == 4
    assert sum(1 for run in runs if run.status == RunStatus.FAILED) == 2
    assert sum(1 for run in runs if run.status == RunStatus.COMPLETED) + sum(
        1 for run in runs if run.status == RunStatus.FAILED
    ) == 6

    evaluations = db_session.query(Evaluation).join(Run).order_by(Run.id).all()
    assert len(evaluations) == 6

    schema_valid = [ev for ev in evaluations if ev.schema_valid]
    assert len(schema_valid) == 2
    assert sum(1 for ev in schema_valid if ev.category_correct) == 1
    assert sum(1 for ev in schema_valid if ev.priority_correct) == 1

    failure_categories = {
        ev.failure_category for ev in evaluations if ev.failure_category is not None
    }
    assert failure_categories == {
        FailureCategory.PROVIDER_ERROR,
        FailureCategory.TIMEOUT,
        FailureCategory.INVALID_JSON,
        FailureCategory.SCHEMA_ERROR,
        FailureCategory.CONTENT_MISMATCH,
    }

    completed_runs = [run for run in runs if run.status == RunStatus.COMPLETED]
    assert sum(run.prompt_tokens or 0 for run in completed_runs) == 46
    assert sum(run.completion_tokens or 0 for run in completed_runs) == 86
    assert all(run.prompt_tokens is None for run in runs if run.status == RunStatus.FAILED)

    reliability_by_run = {
        run.repetition_index: next(
            ev.reliability_score
            for ev in evaluations
            if ev.run_id == run.id
        )
        for run in runs
    }
    assert reliability_by_run[5] > reliability_by_run[6]
    assert reliability_by_run[1] == 0.0
    assert reliability_by_run[2] == 0.0

    export_dir = export_root / "benchmarks" / "results" / MIXED_OUTCOMES_PLAN.benchmark_id
    summary = json.loads((export_dir / "summary.json").read_text(encoding="utf-8"))
    variant = summary["variant_metrics"][0]

    assert variant["total_runs"] == 6
    assert variant["completed_runs"] == 4
    assert variant["failed_runs"] == 2
    assert variant["schema_valid_runs"] == 2
    assert variant["schema_validity_rate"] == pytest.approx(2 / 6)
    assert variant["category_accuracy"] == pytest.approx(0.5)
    assert variant["priority_accuracy"] == pytest.approx(0.5)
    assert variant["total_prompt_tokens"] == 46
    assert variant["total_completion_tokens"] == 86
    assert variant["failure_count"] == 5

    methodology = json.loads((export_dir / "methodology.json").read_text(encoding="utf-8"))
    assert methodology["provider_invocations"]["openai_sdk_max_retries"] == 0
    assert methodology["scoring"]["accuracy_denominators"]["category_accuracy"].endswith(
        "schema-valid runs only"
    )
