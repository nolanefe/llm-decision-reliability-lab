"""Deterministic scoring orchestration for an experiment's Runs.

``score_experiment`` is the single entry point. It loads every Run and its
Evaluation for an experiment, computes quality, consistency, and
reliability scores using the formulas in ``app.evaluation.scoring``, and
persists all updates in one transaction.

Scoring is a pure function of already-persisted Run/Evaluation data, so it
is safe to call independently of the executor (e.g. for tests or a future
recalculation tool) and is idempotent: calling it twice on unchanged data
produces the same result.

A failure partway through never leaves partially updated Evaluations: all
computation happens in memory before a single commit, and any exception
rolls the session back before propagating to the caller. The executor
treats a scoring failure as an orchestration failure and marks the
Experiment failed.
"""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import IncompleteExperimentDataError, NotFoundError
from app.evaluation.scoring import (
    compute_group_consistency_score,
    compute_quality_score,
    compute_reliability_score,
)
from app.models.evaluation import Evaluation
from app.models.experiment import Experiment
from app.models.run import Run

GroupKey = tuple[int, int, str]  # dataset_item_id, prompt_version_id, model_name


def score_experiment(db: Session, experiment_id: int) -> None:
    if db.get(Experiment, experiment_id) is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")

    try:
        rows = _load_runs_with_evaluations(db, experiment_id)
        _assert_every_run_has_an_evaluation(db, experiment_id, rows)

        quality_by_evaluation_id = {
            evaluation.id: compute_quality_score(
                schema_valid=evaluation.schema_valid,
                category_correct=evaluation.category_correct,
                priority_correct=evaluation.priority_correct,
            )
            for _run, evaluation in rows
        }
        consistency_by_evaluation_id = _score_consistency_groups(rows)

        for run, evaluation in rows:
            quality_score = quality_by_evaluation_id[evaluation.id]
            consistency_score = consistency_by_evaluation_id[evaluation.id]
            evaluation.quality_score = quality_score
            evaluation.consistency_score = consistency_score
            evaluation.reliability_score = compute_reliability_score(
                quality_score=quality_score,
                consistency_score=consistency_score,
                schema_valid=evaluation.schema_valid,
                run_status=run.status,
            )

        db.commit()
    except Exception:
        db.rollback()
        raise


def _load_runs_with_evaluations(
    db: Session, experiment_id: int
) -> list[tuple[Run, Evaluation]]:
    return list(
        db.execute(
            select(Run, Evaluation)
            .join(Evaluation, Evaluation.run_id == Run.id)
            .where(Run.experiment_id == experiment_id)
            .order_by(Run.id)
        ).all()
    )


def _assert_every_run_has_an_evaluation(
    db: Session, experiment_id: int, rows: list[tuple[Run, Evaluation]]
) -> None:
    total_runs = db.scalar(
        select(func.count()).select_from(Run).where(Run.experiment_id == experiment_id)
    )
    if (total_runs or 0) != len(rows):
        raise IncompleteExperimentDataError(
            f"Experiment {experiment_id} has {total_runs} Run(s) but only "
            f"{len(rows)} associated Evaluation(s); cannot score incomplete data."
        )


def _score_consistency_groups(rows: list[tuple[Run, Evaluation]]) -> dict[int, float]:
    groups: dict[GroupKey, list[tuple[Run, Evaluation]]] = defaultdict(list)
    for run, evaluation in rows:
        key = (run.dataset_item_id, run.prompt_version_id, run.model_name)
        groups[key].append((run, evaluation))

    scores: dict[int, float] = {}
    for members in groups.values():
        valid_outcomes = [
            (run.parsed_output["category"], run.parsed_output["priority"])
            for run, evaluation in members
            if evaluation.schema_valid and run.parsed_output is not None
        ]
        group_score = compute_group_consistency_score(
            valid_outcomes=valid_outcomes, total_planned_runs=len(members)
        )
        for _run, evaluation in members:
            scores[evaluation.id] = group_score
    return scores
