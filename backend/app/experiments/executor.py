"""Synchronous, sequential experiment execution (v0.1: no queues/workers).

``execute_experiment`` is the sole entry point. It validates the experiment
is executable, creates the full Cartesian product of Run records, executes
them one at a time against an ``LLMProvider``, and scores each output. A
single Run's provider failure or invalid output never stops the remaining
Runs — those are measurable experiment outcomes, not orchestration errors.
The Experiment is only marked ``failed`` for an unrecoverable orchestration
or database failure encountered while executing.
"""

import json
import logging
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    OrchestrationError,
    ProviderUnavailableError,
    UnprocessableEntityError,
)
from app.evaluation.metrics import compute_variant_metrics
from app.evaluation.recommendation import build_recommendation
from app.evaluation.scorer import score_experiment
from app.llm.openai_provider import OpenAIProvider
from app.llm.pricing import SUPPORTED_MODELS, calculate_cost_usd
from app.llm.prompt import render_prompt
from app.llm.provider import LLMProvider, ProviderError, ProviderTimeoutError
from app.models.dataset_item import DatasetItem
from app.models.enums import ExperimentStatus, FailureCategory, RunStatus
from app.models.evaluation import Evaluation
from app.models.experiment import Experiment
from app.models.prompt_version import PromptVersion
from app.models.run import Run
from app.schemas.execution import ExecutionSummary
from app.schemas.support_triage import SupportTriageOutput

logger = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider | None:
    """FastAPI dependency hook.

    Returns ``None`` by default so ``execute_experiment`` builds the real
    OpenAI-backed provider. Tests override this dependency to inject a fake
    provider so execution never makes a network call.
    """
    return None


def execute_experiment(
    db: Session, experiment_id: int, provider: LLMProvider | None = None
) -> ExecutionSummary:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")

    if experiment.status != ExperimentStatus.DRAFT:
        raise ConflictError(
            f"Experiment {experiment_id} cannot be executed in status "
            f"'{experiment.status.value}'"
        )

    existing_run_count = db.scalar(
        select(func.count()).select_from(Run).where(Run.experiment_id == experiment_id)
    )
    if existing_run_count:
        raise ConflictError(f"Experiment {experiment_id} already has runs")

    dataset_items_by_id = _load_by_id(db, DatasetItem, experiment.dataset_item_ids)
    missing_dataset_items = [
        item_id
        for item_id in experiment.dataset_item_ids
        if item_id not in dataset_items_by_id
    ]
    if missing_dataset_items:
        raise UnprocessableEntityError(
            f"Unknown dataset_item_ids: {sorted(set(missing_dataset_items))}"
        )

    prompt_versions_by_id = _load_by_id(db, PromptVersion, experiment.prompt_version_ids)
    missing_prompt_versions = [
        version_id
        for version_id in experiment.prompt_version_ids
        if version_id not in prompt_versions_by_id
    ]
    if missing_prompt_versions:
        raise UnprocessableEntityError(
            f"Unknown prompt_version_ids: {sorted(set(missing_prompt_versions))}"
        )

    unsupported_models = sorted(
        {name for name in experiment.model_names if name not in SUPPORTED_MODELS}
    )
    if unsupported_models:
        raise UnprocessableEntityError(f"Unsupported model_names: {unsupported_models}")

    settings = get_settings()
    planned_run_count = (
        len(experiment.dataset_item_ids)
        * len(experiment.prompt_version_ids)
        * len(experiment.model_names)
        * experiment.repeat_count
    )
    if planned_run_count > settings.max_runs_per_experiment:
        raise UnprocessableEntityError(
            f"Planned run count {planned_run_count} exceeds the configured "
            f"maximum of {settings.max_runs_per_experiment} runs per experiment"
        )

    if provider is None:
        if not settings.openai_api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured")
        provider = OpenAIProvider(
            api_key=settings.openai_api_key,
            timeout_seconds=settings.openai_request_timeout_seconds,
        )

    try:
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "experiment execution started experiment_id=%s planned_runs=%s",
            experiment.id,
            planned_run_count,
        )

        runs = _build_planned_runs(experiment)
        db.add_all(runs)
        db.commit()

        for run in runs:
            _execute_run(
                db,
                run,
                dataset_item=dataset_items_by_id[run.dataset_item_id],
                prompt_version=prompt_versions_by_id[run.prompt_version_id],
                provider=provider,
            )

        # All Runs are now in a terminal state: score quality, consistency,
        # and reliability and persist them before the Experiment is marked
        # completed. A scoring failure is an orchestration failure (see the
        # except block below), not a per-run outcome.
        score_experiment(db, experiment.id)

        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        logger.exception(
            "Unexpected orchestration failure for experiment_id=%s", experiment_id
        )
        db.rollback()
        try:
            experiment.status = ExperimentStatus.FAILED
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        raise OrchestrationError(
            f"Experiment {experiment_id} execution failed unexpectedly."
        ) from exc

    summary = _build_summary(db, experiment, planned_run_count)
    logger.info(
        "experiment execution completed experiment_id=%s completed_runs=%s "
        "failed_runs=%s",
        experiment.id,
        summary.completed_runs,
        summary.failed_runs,
    )
    return summary


def _load_by_id(db: Session, model: type, ids: list[int]) -> dict[int, object]:
    rows = db.scalars(select(model).where(model.id.in_(ids))).all()
    return {row.id: row for row in rows}


def _build_planned_runs(experiment: Experiment) -> list[Run]:
    runs: list[Run] = []
    for dataset_item_id in experiment.dataset_item_ids:
        for prompt_version_id in experiment.prompt_version_ids:
            for model_name in experiment.model_names:
                for repetition_index in range(1, experiment.repeat_count + 1):
                    runs.append(
                        Run(
                            experiment_id=experiment.id,
                            dataset_item_id=dataset_item_id,
                            prompt_version_id=prompt_version_id,
                            model_name=model_name,
                            repetition_index=repetition_index,
                        )
                    )
    return runs


def _execute_run(
    db: Session,
    run: Run,
    *,
    dataset_item: DatasetItem,
    prompt_version: PromptVersion,
    provider: LLMProvider,
) -> None:
    run.status = RunStatus.RUNNING
    db.commit()
    logger.info(
        "run started run_id=%s experiment_id=%s model=%s repetition=%s",
        run.id,
        run.experiment_id,
        run.model_name,
        run.repetition_index,
    )

    prompt = render_prompt(prompt_version.template_text, dataset_item.input_text)

    try:
        result = provider.generate(prompt=prompt, model=run.model_name)
    except ProviderTimeoutError as exc:
        _fail_run(db, run, FailureCategory.TIMEOUT, str(exc))
        return
    except ProviderError as exc:
        _fail_run(db, run, FailureCategory.PROVIDER_ERROR, str(exc))
        return

    cost_usd = calculate_cost_usd(
        run.model_name, result.input_tokens, result.output_tokens
    )

    run.raw_response = result.raw_response
    run.latency_ms = result.latency_ms
    run.prompt_tokens = result.input_tokens
    run.completion_tokens = result.output_tokens
    run.total_tokens = result.total_tokens
    run.estimated_cost_usd = float(cost_usd)
    run.status = RunStatus.COMPLETED
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    _evaluate_output(db, run, dataset_item, result.raw_response)
    logger.info("run completed run_id=%s status=completed", run.id)


def _fail_run(
    db: Session, run: Run, failure_category: FailureCategory, error_message: str
) -> None:
    run.status = RunStatus.FAILED
    run.error_message = error_message
    run.completed_at = datetime.now(timezone.utc)
    db.add(Evaluation(run_id=run.id, schema_valid=False, failure_category=failure_category))
    db.commit()
    logger.warning(
        "run failed run_id=%s failure_category=%s", run.id, failure_category.value
    )


def _evaluate_output(
    db: Session, run: Run, dataset_item: DatasetItem, raw_response: str
) -> None:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        db.add(
            Evaluation(
                run_id=run.id,
                schema_valid=False,
                failure_category=FailureCategory.INVALID_JSON,
            )
        )
        db.commit()
        logger.info(
            "run evaluated run_id=%s schema_valid=false failure_category=invalid_json",
            run.id,
        )
        return

    if isinstance(parsed, dict):
        run.parsed_output = parsed

    try:
        output = SupportTriageOutput.model_validate(parsed)
    except ValidationError:
        db.add(
            Evaluation(
                run_id=run.id,
                schema_valid=False,
                failure_category=FailureCategory.SCHEMA_ERROR,
            )
        )
        db.commit()
        logger.info(
            "run evaluated run_id=%s schema_valid=false failure_category=schema_error",
            run.id,
        )
        return

    category_correct = output.category.value == dataset_item.expected_category
    priority_correct = output.priority.value == dataset_item.expected_priority
    failure_category = (
        None
        if category_correct and priority_correct
        else FailureCategory.CONTENT_MISMATCH
    )
    db.add(
        Evaluation(
            run_id=run.id,
            schema_valid=True,
            category_correct=category_correct,
            priority_correct=priority_correct,
            failure_category=failure_category,
        )
    )
    db.commit()
    logger.info(
        "run evaluated run_id=%s schema_valid=true category_correct=%s "
        "priority_correct=%s",
        run.id,
        category_correct,
        priority_correct,
    )


def _build_summary(
    db: Session, experiment: Experiment, planned_run_count: int
) -> ExecutionSummary:
    completed_runs = db.scalar(
        select(func.count())
        .select_from(Run)
        .where(Run.experiment_id == experiment.id, Run.status == RunStatus.COMPLETED)
    )
    failed_runs = db.scalar(
        select(func.count())
        .select_from(Run)
        .where(Run.experiment_id == experiment.id, Run.status == RunStatus.FAILED)
    )
    schema_valid_runs = db.scalar(
        select(func.count())
        .select_from(Evaluation)
        .join(Run, Evaluation.run_id == Run.id)
        .where(Run.experiment_id == experiment.id, Evaluation.schema_valid.is_(True))
    )
    schema_invalid_runs = db.scalar(
        select(func.count())
        .select_from(Evaluation)
        .join(Run, Evaluation.run_id == Run.id)
        .where(Run.experiment_id == experiment.id, Evaluation.schema_valid.is_(False))
    )

    average_reliability_score = None
    recommended_prompt_version_id = None
    recommended_model_name = None
    if experiment.status == ExperimentStatus.COMPLETED:
        variant_metrics = compute_variant_metrics(db, experiment)
        scores = [
            v.average_reliability_score
            for v in variant_metrics
            if v.average_reliability_score is not None
        ]
        if scores:
            average_reliability_score = round(sum(scores) / len(scores), 2)
        recommendation = build_recommendation(variant_metrics)
        if recommendation is not None:
            recommended_prompt_version_id = recommendation.recommended_prompt_version_id
            recommended_model_name = recommendation.recommended_model_name

    return ExecutionSummary(
        experiment_id=experiment.id,
        status=experiment.status,
        planned_runs=planned_run_count,
        completed_runs=completed_runs or 0,
        failed_runs=failed_runs or 0,
        schema_valid_runs=schema_valid_runs or 0,
        schema_invalid_runs=schema_invalid_runs or 0,
        started_at=experiment.started_at,
        completed_at=experiment.completed_at,
        average_reliability_score=average_reliability_score,
        recommended_prompt_version_id=recommended_prompt_version_id,
        recommended_model_name=recommended_model_name,
    )
