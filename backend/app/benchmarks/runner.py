"""Benchmark orchestration: resolve seed IDs, create experiment, execute, export."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.benchmarks.export import export_benchmark_evidence
from app.benchmarks.plan import BenchmarkPlan, DEFAULT_BENCHMARK_PLAN
from app.benchmarks.validation import validate_benchmark_id
from app.core.config import get_settings
from app.core.exceptions import ProviderUnavailableError
from app.db.seed import run_seed
from app.experiments.executor import execute_experiment
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMProvider
from app.models.dataset_item import DatasetItem
from app.models.experiment import Experiment
from app.models.prompt_version import PromptVersion
from app.schemas.experiment import ExperimentCreate
from app.services.experiments import create_experiment

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkDryRunSummary:
    plan: BenchmarkPlan
    planned_run_count: int
    dataset_item_ids: list[int]
    prompt_version_ids: list[int]
    openai_api_key_configured: bool


@dataclass(frozen=True)
class BenchmarkRunSummary:
    plan: BenchmarkPlan
    experiment_id: int
    planned_runs: int
    completed_runs: int
    failed_runs: int
    export_dir: str


class BenchmarkConfigurationError(Exception):
    """Raised when seed data required by a benchmark plan is missing."""


def describe_benchmark_plan(
    db: Session, plan: BenchmarkPlan = DEFAULT_BENCHMARK_PLAN
) -> BenchmarkDryRunSummary:
    """Validate that seed entities exist and return the resolved plan."""
    run_seed(db)
    dataset_item_ids = _resolve_dataset_item_ids(db, plan)
    prompt_version_ids = _resolve_prompt_version_ids(db, plan)
    settings = get_settings()

    return BenchmarkDryRunSummary(
        plan=plan,
        planned_run_count=plan.planned_run_count,
        dataset_item_ids=dataset_item_ids,
        prompt_version_ids=prompt_version_ids,
        openai_api_key_configured=bool(settings.openai_api_key),
    )


def run_live_benchmark(
    db: Session,
    *,
    plan: BenchmarkPlan = DEFAULT_BENCHMARK_PLAN,
    provider: LLMProvider | None = None,
) -> BenchmarkRunSummary:
    """Create, execute, and export a live benchmark experiment.

    ``provider`` is accepted for tests only. When ``None``, the executor
    uses ``OPENAI_API_KEY`` from environment configuration.
    """
    validate_benchmark_id(plan.benchmark_id)
    dry_run = describe_benchmark_plan(db, plan)
    settings = get_settings()
    if provider is None:
        if not settings.openai_api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured")
        provider = OpenAIProvider(
            api_key=settings.openai_api_key,
            timeout_seconds=settings.openai_request_timeout_seconds,
            max_retries=0,
        )

    experiment = create_experiment(
        db,
        ExperimentCreate(
            name=plan.experiment_name,
            dataset_item_ids=dry_run.dataset_item_ids,
            prompt_version_ids=dry_run.prompt_version_ids,
            model_names=list(plan.model_names),
            repeat_count=plan.repeat_count,
        ),
    )
    logger.info(
        "benchmark experiment created experiment_id=%s planned_runs=%s",
        experiment.id,
        plan.planned_run_count,
    )

    execution = execute_experiment(db, experiment.id, provider=provider)
    db.refresh(experiment)

    export_dir = export_benchmark_evidence(
        db,
        experiment=experiment,
        plan=plan,
        benchmark_id=plan.benchmark_id,
    )

    return BenchmarkRunSummary(
        plan=plan,
        experiment_id=experiment.id,
        planned_runs=execution.planned_runs,
        completed_runs=execution.completed_runs,
        failed_runs=execution.failed_runs,
        export_dir=str(export_dir),
    )


def export_existing_benchmark(
    db: Session,
    *,
    experiment_id: int,
    plan: BenchmarkPlan = DEFAULT_BENCHMARK_PLAN,
    benchmark_id: str | None = None,
) -> str:
    """Export evidence for an already-completed experiment."""
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise BenchmarkConfigurationError(f"Experiment {experiment_id} not found")

    resolved_benchmark_id = validate_benchmark_id(benchmark_id or plan.benchmark_id)
    export_dir = export_benchmark_evidence(
        db,
        experiment=experiment,
        plan=plan,
        benchmark_id=resolved_benchmark_id,
    )
    return str(export_dir)


def _resolve_dataset_item_ids(db: Session, plan: BenchmarkPlan) -> list[int]:
    rows = db.scalars(
        select(DatasetItem).where(DatasetItem.name.in_(plan.dataset_item_names))
    ).all()
    by_name = {row.name: row.id for row in rows}
    missing = [name for name in plan.dataset_item_names if name not in by_name]
    if missing:
        raise BenchmarkConfigurationError(
            f"Missing dataset items for benchmark plan: {missing}. "
            "Run `python -m app.db.seed` first."
        )
    return [by_name[name] for name in plan.dataset_item_names]


def _resolve_prompt_version_ids(db: Session, plan: BenchmarkPlan) -> list[int]:
    rows = db.scalars(
        select(PromptVersion).where(PromptVersion.name.in_(plan.prompt_version_names))
    ).all()
    by_name = {row.name: row.id for row in rows}
    missing = [name for name in plan.prompt_version_names if name not in by_name]
    if missing:
        raise BenchmarkConfigurationError(
            f"Missing prompt versions for benchmark plan: {missing}. "
            "Run `python -m app.db.seed` first."
        )
    return [by_name[name] for name in plan.prompt_version_names]
