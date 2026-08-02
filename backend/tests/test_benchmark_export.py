"""Tests for sanitized benchmark evidence export."""

import json
import re

import pytest

from app.benchmarks.export import export_benchmark_evidence
from app.benchmarks.plan import PORTFOLIO_BENCHMARK_V1
from app.benchmarks.runner import describe_benchmark_plan, run_live_benchmark
from app.core.config import get_settings
from app.models.enums import ExperimentStatus
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


def test_export_writes_all_artifact_files(db_session, export_root):
    from app.db.seed import run_seed

    run_seed(db_session)
    dry_run = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)
    outcomes = [make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    provider = ScriptedProvider(outcomes=outcomes)

    result = run_live_benchmark(
        db_session,
        plan=PORTFOLIO_BENCHMARK_V1,
        provider=provider,
    )

    export_dir = export_root / "benchmarks" / "results" / PORTFOLIO_BENCHMARK_V1.benchmark_id
    assert export_dir.exists()
    assert result.export_dir == str(export_dir)
    for name in ("summary.json", "results.csv", "methodology.json", "README.md"):
        assert (export_dir / name).exists()


def test_export_refuses_to_overwrite_existing_directory(db_session, export_root):
    from app.db.seed import run_seed

    run_seed(db_session)
    dry_run = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)
    outcomes = [make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    provider = ScriptedProvider(outcomes=outcomes)

    run_live_benchmark(db_session, plan=PORTFOLIO_BENCHMARK_V1, provider=provider)

    completed = db_session.query(
        __import__("app.models.experiment", fromlist=["Experiment"]).Experiment
    ).filter_by(status=ExperimentStatus.COMPLETED).first()

    with pytest.raises(FileExistsError):
        export_benchmark_evidence(
            db_session,
            experiment=completed,
            plan=PORTFOLIO_BENCHMARK_V1,
            benchmark_id=PORTFOLIO_BENCHMARK_V1.benchmark_id,
            output_root=export_root,
        )


def test_exported_artifacts_contain_no_secrets(db_session, export_root, monkeypatch):
    from app.db.seed import run_seed

    monkeypatch.setenv("OPENAI_API_KEY", "sk-export-test-secret-value")
    get_settings.cache_clear()
    run_seed(db_session)

    dry_run = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)
    outcomes = [make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    provider = ScriptedProvider(outcomes=outcomes)
    run_live_benchmark(db_session, plan=PORTFOLIO_BENCHMARK_V1, provider=provider)

    export_dir = export_root / "benchmarks" / "results" / PORTFOLIO_BENCHMARK_V1.benchmark_id
    secret_pattern = re.compile(r"sk-[A-Za-z0-9_-]{6,}")

    for path in export_dir.iterdir():
        text = path.read_text(encoding="utf-8")
        assert secret_pattern.search(text) is None
        assert "/Users/" not in text
        assert "export-test-secret" not in text


def test_export_summary_variant_metrics(db_session, export_root):
    from app.db.seed import run_seed

    run_seed(db_session)
    dry_run = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)
    outcomes = [make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    provider = ScriptedProvider(outcomes=outcomes)
    run_live_benchmark(db_session, plan=PORTFOLIO_BENCHMARK_V1, provider=provider)

    export_dir = export_root / "benchmarks" / "results" / PORTFOLIO_BENCHMARK_V1.benchmark_id
    summary = json.loads((export_dir / "summary.json").read_text(encoding="utf-8"))

    assert summary["planned_runs"] == 16
    assert summary["logical_provider_invocations"] == 16
    assert summary["execution_outcomes"]["provider_executions_completed"] == 16
    assert summary["execution_outcomes"]["schema_valid_outputs"] == 16
    assert summary["completed_runs"] == 16
    assert summary["failed_runs"] == 0
    assert len(summary["variant_metrics"]) == 2
    assert summary["recommendation"] is not None

    for variant in summary["variant_metrics"]:
        assert variant["total_runs"] == 8
        assert variant["schema_validity_rate"] == 1.0


def test_export_is_atomic_on_write_failure(db_session, export_root, monkeypatch):
    from app.benchmarks import export as export_module
    from app.db.seed import run_seed

    run_seed(db_session)
    dry_run = describe_benchmark_plan(db_session, PORTFOLIO_BENCHMARK_V1)
    outcomes = [make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    provider = ScriptedProvider(outcomes=outcomes)

    original_write_csv = export_module._write_results_csv

    def failing_write_csv(path, variant_metrics):
        raise OSError("simulated write failure")

    monkeypatch.setattr(export_module, "_write_results_csv", failing_write_csv)

    with pytest.raises(OSError, match="simulated write failure"):
        run_live_benchmark(db_session, plan=PORTFOLIO_BENCHMARK_V1, provider=provider)

    final_dir = export_root / "benchmarks" / "results" / PORTFOLIO_BENCHMARK_V1.benchmark_id
    results_parent = final_dir.parent
    assert not final_dir.exists()
    assert list(results_parent.glob(f".{PORTFOLIO_BENCHMARK_V1.benchmark_id}-*")) == []

    monkeypatch.setattr(export_module, "_write_results_csv", original_write_csv)
    fresh_provider = ScriptedProvider(
        outcomes=[make_result(VALID_OUTPUT) for _ in range(dry_run.planned_run_count)]
    )
    run_live_benchmark(db_session, plan=PORTFOLIO_BENCHMARK_V1, provider=fresh_provider)
    assert final_dir.exists()
    assert len(list(final_dir.iterdir())) == 4
