"""Variant comparison metrics.

A comparison variant is one (prompt_version_id, model_name) pair.
``compute_variant_metrics`` aggregates every Run/Evaluation for an
experiment into one ``VariantMetrics`` per variant actually present in
that experiment's Runs, with deterministic ordering across variants.
"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import IncompleteExperimentDataError
from app.models.enums import RunStatus
from app.models.evaluation import Evaluation
from app.models.experiment import Experiment
from app.models.prompt_version import PromptVersion
from app.models.run import Run
from app.schemas.metrics import VariantMetrics

VariantKey = tuple[int, str]  # prompt_version_id, model_name


def compute_variant_metrics(db: Session, experiment: Experiment) -> list[VariantMetrics]:
    rows = _load_rows(db, experiment.id)
    _assert_data_is_complete(db, experiment.id, rows)
    prompt_versions_by_id = _load_prompt_versions(db, experiment.prompt_version_ids)

    groups: dict[VariantKey, list[tuple[Run, Evaluation]]] = defaultdict(list)
    for run, evaluation in rows:
        groups[(run.prompt_version_id, run.model_name)].append((run, evaluation))

    metrics = [
        _build_variant_metrics(key, members, prompt_versions_by_id)
        for key, members in groups.items()
    ]
    metrics.sort(key=_sort_key)
    return metrics


def _load_rows(db: Session, experiment_id: int) -> list[tuple[Run, Evaluation]]:
    return list(
        db.execute(
            select(Run, Evaluation)
            .join(Evaluation, Evaluation.run_id == Run.id)
            .where(Run.experiment_id == experiment_id)
            .order_by(Run.id)
        ).all()
    )


def _assert_data_is_complete(
    db: Session, experiment_id: int, rows: list[tuple[Run, Evaluation]]
) -> None:
    total_runs = db.scalar(
        select(func.count()).select_from(Run).where(Run.experiment_id == experiment_id)
    )
    if (total_runs or 0) != len(rows):
        raise IncompleteExperimentDataError(
            f"Experiment {experiment_id} has {total_runs} Run(s) but only "
            f"{len(rows)} associated Evaluation(s)."
        )
    unscored = [
        evaluation.id for _run, evaluation in rows if evaluation.quality_score is None
    ]
    if unscored:
        raise IncompleteExperimentDataError(
            f"Experiment {experiment_id} has unscored Evaluation(s): {unscored}. "
            "Scoring must complete before metrics can be computed."
        )


def _load_prompt_versions(
    db: Session, prompt_version_ids: list[int]
) -> dict[int, PromptVersion]:
    rows = db.scalars(
        select(PromptVersion).where(PromptVersion.id.in_(prompt_version_ids))
    ).all()
    return {row.id: row for row in rows}


def _build_variant_metrics(
    key: VariantKey,
    members: list[tuple[Run, Evaluation]],
    prompt_versions_by_id: dict[int, PromptVersion],
) -> VariantMetrics:
    prompt_version_id, model_name = key
    prompt_version = prompt_versions_by_id[prompt_version_id]

    total_runs = len(members)
    completed_runs = sum(1 for run, _ in members if run.status == RunStatus.COMPLETED)
    failed_runs = sum(1 for run, _ in members if run.status == RunStatus.FAILED)
    schema_valid_runs = sum(1 for _, ev in members if ev.schema_valid)
    schema_validity_rate = schema_valid_runs / total_runs if total_runs else 0.0

    category_correct_count = sum(
        1 for _, ev in members if ev.schema_valid and ev.category_correct
    )
    priority_correct_count = sum(
        1 for _, ev in members if ev.schema_valid and ev.priority_correct
    )
    category_accuracy = (
        category_correct_count / schema_valid_runs if schema_valid_runs else None
    )
    priority_accuracy = (
        priority_correct_count / schema_valid_runs if schema_valid_runs else None
    )

    quality_scores = [
        ev.quality_score for _, ev in members if ev.quality_score is not None
    ]
    consistency_scores = [
        ev.consistency_score for _, ev in members if ev.consistency_score is not None
    ]
    reliability_scores = [
        ev.reliability_score for _, ev in members if ev.reliability_score is not None
    ]
    latencies = [run.latency_ms for run, _ in members if run.latency_ms is not None]

    total_prompt_tokens = sum(
        run.prompt_tokens for run, _ in members if run.prompt_tokens is not None
    )
    total_completion_tokens = sum(
        run.completion_tokens for run, _ in members if run.completion_tokens is not None
    )
    total_tokens = sum(
        run.total_tokens for run, _ in members if run.total_tokens is not None
    )
    total_estimated_cost_usd = sum(
        (
            Decimal(str(run.estimated_cost_usd))
            for run, _ in members
            if run.estimated_cost_usd is not None
        ),
        start=Decimal("0"),
    )
    failure_count = sum(1 for _, ev in members if ev.failure_category is not None)

    return VariantMetrics(
        prompt_version_id=prompt_version_id,
        prompt_version_name=prompt_version.name,
        prompt_version_version=prompt_version.version,
        model_name=model_name,
        total_runs=total_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        schema_valid_runs=schema_valid_runs,
        schema_validity_rate=schema_validity_rate,
        category_accuracy=category_accuracy,
        priority_accuracy=priority_accuracy,
        average_quality_score=_average(quality_scores),
        average_consistency_score=_average(consistency_scores),
        average_reliability_score=_average(reliability_scores),
        average_latency_ms=_average(latencies),
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
        total_tokens=total_tokens,
        total_estimated_cost_usd=total_estimated_cost_usd,
        failure_count=failure_count,
    )


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _sort_key(metrics: VariantMetrics) -> tuple:
    """average_reliability_score desc, total_estimated_cost_usd asc,
    average_latency_ms asc, prompt_version_id asc, model_name asc."""
    reliability_desc = (
        -metrics.average_reliability_score
        if metrics.average_reliability_score is not None
        else float("inf")
    )
    latency_asc = (
        metrics.average_latency_ms if metrics.average_latency_ms is not None else float("inf")
    )
    return (
        reliability_desc,
        metrics.total_estimated_cost_usd,
        latency_asc,
        metrics.prompt_version_id,
        metrics.model_name,
    )
