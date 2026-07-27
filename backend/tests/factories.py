"""Shared DB row builders for Stage 6 evaluation/metrics/failures tests.

These construct Dataset/PromptVersion/Experiment/Run/Evaluation rows
directly (bypassing the executor), so tests can set up precise scoring
scenarios -- including ones the executor itself would never produce, like
a Run with no Evaluation -- without duplicating the same boilerplate in
every test module.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.dataset_item import DatasetItem
from app.models.enums import ExperimentStatus, FailureCategory, RunStatus
from app.models.evaluation import Evaluation
from app.models.experiment import Experiment
from app.models.prompt_version import PromptVersion
from app.models.run import Run


def make_dataset_item(db: Session, **overrides) -> DatasetItem:
    defaults = dict(
        name="ticket",
        input_text="A ticket.",
        expected_category="billing",
        expected_priority="high",
    )
    defaults.update(overrides)
    item = DatasetItem(**defaults)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def make_prompt_version(db: Session, **overrides) -> PromptVersion:
    defaults = dict(name="prompt", version=1, template_text="Classify: {ticket_text}")
    defaults.update(overrides)
    prompt = PromptVersion(**defaults)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def make_experiment(
    db: Session,
    *,
    dataset_item_ids: list[int],
    prompt_version_ids: list[int],
    model_names: list[str],
    repeat_count: int = 1,
    status: ExperimentStatus = ExperimentStatus.COMPLETED,
    name: str = "experiment",
) -> Experiment:
    experiment = Experiment(
        name=name,
        status=status,
        repeat_count=repeat_count,
        dataset_item_ids=dataset_item_ids,
        prompt_version_ids=prompt_version_ids,
        model_names=model_names,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def make_run(
    db: Session,
    *,
    experiment: Experiment,
    dataset_item: DatasetItem,
    prompt_version: PromptVersion,
    model_name: str = "gpt-5-mini",
    repetition_index: int = 1,
    status: RunStatus = RunStatus.COMPLETED,
    raw_response: str | None = None,
    parsed_output: dict | None = None,
    latency_ms: int | None = 100,
    prompt_tokens: int | None = 10,
    completion_tokens: int | None = 20,
    total_tokens: int | None = 30,
    estimated_cost_usd: float | None = 0.001,
    error_message: str | None = None,
) -> Run:
    run = Run(
        experiment_id=experiment.id,
        dataset_item_id=dataset_item.id,
        prompt_version_id=prompt_version.id,
        model_name=model_name,
        repetition_index=repetition_index,
        status=status,
        raw_response=raw_response,
        parsed_output=parsed_output,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        error_message=error_message,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def make_evaluation(
    db: Session,
    *,
    run: Run,
    schema_valid: bool,
    category_correct: bool | None = None,
    priority_correct: bool | None = None,
    failure_category: FailureCategory | None = None,
    quality_score: float | None = None,
    consistency_score: float | None = None,
    reliability_score: float | None = None,
) -> Evaluation:
    evaluation = Evaluation(
        run_id=run.id,
        schema_valid=schema_valid,
        category_correct=category_correct,
        priority_correct=priority_correct,
        failure_category=failure_category,
        quality_score=quality_score,
        consistency_score=consistency_score,
        reliability_score=reliability_score,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation
