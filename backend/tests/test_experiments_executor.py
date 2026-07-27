"""Executor tests. All provider calls go through ScriptedProvider — a fake
LLMProvider — so no test in this file makes a network call."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    OrchestrationError,
    ProviderUnavailableError,
    UnprocessableEntityError,
)
from app.experiments.executor import execute_experiment
from app.llm.provider import ProviderError, ProviderTimeoutError
from app.models.dataset_item import DatasetItem
from app.models.enums import ExperimentStatus, FailureCategory, RunStatus
from app.models.evaluation import Evaluation
from app.models.experiment import Experiment
from app.models.prompt_version import PromptVersion
from app.models.run import Run
from tests.fakes import ScriptedProvider, make_result

VALID_OUTPUT = (
    '{"category": "billing", "priority": "high", "summary": "s", '
    '"recommended_action": "a"}'
)
MISMATCHED_OUTPUT = (
    '{"category": "bug", "priority": "low", "summary": "s", '
    '"recommended_action": "a"}'
)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_dataset_item(db: Session, **overrides) -> DatasetItem:
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


def _make_prompt_version(db: Session, **overrides) -> PromptVersion:
    defaults = dict(name="prompt", version=1, template_text="Classify: {ticket_text}")
    defaults.update(overrides)
    prompt = PromptVersion(**defaults)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def _make_experiment(
    db: Session,
    *,
    dataset_item_ids: list[int],
    prompt_version_ids: list[int],
    model_names: list[str],
    repeat_count: int = 1,
    status: ExperimentStatus = ExperimentStatus.DRAFT,
) -> Experiment:
    experiment = Experiment(
        name="experiment",
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


def _runs_for(db: Session, experiment_id: int) -> list[Run]:
    return list(
        db.scalars(
            select(Run).where(Run.experiment_id == experiment_id).order_by(Run.id)
        ).all()
    )


class TestPlannedRunCartesianProduct:
    def test_run_count_matches_cartesian_product(self, db_session: Session) -> None:
        item_a = _make_dataset_item(db_session, name="a")
        item_b = _make_dataset_item(db_session, name="b")
        prompt_a = _make_prompt_version(db_session, name="p-a")
        prompt_b = _make_prompt_version(db_session, name="p-b")
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item_a.id, item_b.id],
            prompt_version_ids=[prompt_a.id, prompt_b.id],
            model_names=["gpt-5-mini"],
            repeat_count=2,
        )
        provider = ScriptedProvider(outcomes=[make_result(VALID_OUTPUT) for _ in range(8)])

        execute_experiment(db_session, experiment.id, provider=provider)

        assert len(_runs_for(db_session, experiment.id)) == 8

    def test_one_based_repetition_indexes(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=3,
        )
        provider = ScriptedProvider(outcomes=[make_result(VALID_OUTPUT) for _ in range(3)])

        execute_experiment(db_session, experiment.id, provider=provider)

        runs = _runs_for(db_session, experiment.id)
        assert [run.repetition_index for run in runs] == [1, 2, 3]

    def test_run_ordering_is_deterministic_by_selection_order(
        self, db_session: Session
    ) -> None:
        item_a = _make_dataset_item(db_session, name="a")
        item_b = _make_dataset_item(db_session, name="b")
        prompt_a = _make_prompt_version(db_session, name="p-a")
        prompt_b = _make_prompt_version(db_session, name="p-b")
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item_a.id, item_b.id],
            prompt_version_ids=[prompt_a.id, prompt_b.id],
            model_names=["gpt-5-mini", "gpt-5-nano"],
            repeat_count=1,
        )
        provider = ScriptedProvider(outcomes=[make_result(VALID_OUTPUT) for _ in range(8)])

        execute_experiment(db_session, experiment.id, provider=provider)

        runs = _runs_for(db_session, experiment.id)
        actual = [
            (run.dataset_item_id, run.prompt_version_id, run.model_name)
            for run in runs
        ]
        expected = [
            (item_a.id, prompt_a.id, "gpt-5-mini"),
            (item_a.id, prompt_a.id, "gpt-5-nano"),
            (item_a.id, prompt_b.id, "gpt-5-mini"),
            (item_a.id, prompt_b.id, "gpt-5-nano"),
            (item_b.id, prompt_a.id, "gpt-5-mini"),
            (item_b.id, prompt_a.id, "gpt-5-nano"),
            (item_b.id, prompt_b.id, "gpt-5-mini"),
            (item_b.id, prompt_b.id, "gpt-5-nano"),
        ]
        assert actual == expected


class TestSuccessfulExecution:
    def test_status_and_timestamp_transitions(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)])

        summary = execute_experiment(db_session, experiment.id, provider=provider)

        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.started_at is not None
        assert experiment.completed_at is not None
        assert experiment.started_at <= experiment.completed_at
        assert summary.status == ExperimentStatus.COMPLETED
        assert summary.experiment_id == experiment.id

    def test_run_persists_latency_tokens_and_cost(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(
            outcomes=[
                make_result(
                    VALID_OUTPUT, input_tokens=1_000_000, output_tokens=1_000_000, latency_ms=321
                )
            ]
        )

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        assert run.status == RunStatus.COMPLETED
        assert run.raw_response == VALID_OUTPUT
        assert run.latency_ms == 321
        assert run.prompt_tokens == 1_000_000
        assert run.completion_tokens == 1_000_000
        assert run.total_tokens == 2_000_000
        assert run.estimated_cost_usd == pytest.approx(2.25)
        assert run.completed_at is not None

    def test_valid_matching_output_is_scored_correct(self, db_session: Session) -> None:
        item = _make_dataset_item(
            db_session, expected_category="billing", expected_priority="high"
        )
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert evaluation.schema_valid is True
        assert evaluation.category_correct is True
        assert evaluation.priority_correct is True
        assert evaluation.failure_category is None
        assert evaluation.quality_score == 1.0
        assert evaluation.consistency_score == 1.0
        assert evaluation.reliability_score == 100.0

    def test_content_mismatch_is_classified(self, db_session: Session) -> None:
        item = _make_dataset_item(
            db_session, expected_category="billing", expected_priority="high"
        )
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[make_result(MISMATCHED_OUTPUT)])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert evaluation.schema_valid is True
        assert evaluation.category_correct is False
        assert evaluation.priority_correct is False
        assert evaluation.failure_category == FailureCategory.CONTENT_MISMATCH

    def test_invalid_json_is_classified_and_run_stays_completed(
        self, db_session: Session
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[make_result("not json at all")])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert run.status == RunStatus.COMPLETED
        assert evaluation.schema_valid is False
        assert evaluation.failure_category == FailureCategory.INVALID_JSON
        assert evaluation.category_correct is None
        assert evaluation.priority_correct is None

    def test_fenced_json_remains_invalid(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        fenced = f"```json\n{VALID_OUTPUT}\n```"
        provider = ScriptedProvider(outcomes=[make_result(fenced)])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert run.raw_response == fenced
        assert evaluation.schema_valid is False
        assert evaluation.failure_category == FailureCategory.INVALID_JSON

    def test_valid_json_invalid_schema_is_classified(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[make_result('{"foo": "bar"}')])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert run.status == RunStatus.COMPLETED
        assert evaluation.schema_valid is False
        assert evaluation.failure_category == FailureCategory.SCHEMA_ERROR

    def test_timeout_marks_run_failed(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[ProviderTimeoutError("timed out")])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert run.status == RunStatus.FAILED
        assert run.error_message
        assert evaluation.schema_valid is False
        assert evaluation.failure_category == FailureCategory.TIMEOUT

    def test_provider_error_marks_run_failed(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[ProviderError("boom")])

        execute_experiment(db_session, experiment.id, provider=provider)

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        assert run.status == RunStatus.FAILED
        assert run.error_message
        assert evaluation.schema_valid is False
        assert evaluation.failure_category == FailureCategory.PROVIDER_ERROR


class TestPartialFailureDoesNotStopExecution:
    def test_one_invalid_output_does_not_stop_later_runs(
        self, db_session: Session
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=2,
        )
        provider = ScriptedProvider(
            outcomes=[make_result("not json"), make_result(VALID_OUTPUT)]
        )

        execute_experiment(db_session, experiment.id, provider=provider)

        runs = _runs_for(db_session, experiment.id)
        assert [run.status for run in runs] == [RunStatus.COMPLETED, RunStatus.COMPLETED]
        evaluations = [
            db_session.scalar(select(Evaluation).where(Evaluation.run_id == run.id))
            for run in runs
        ]
        assert evaluations[0].schema_valid is False
        assert evaluations[1].schema_valid is True

    def test_one_provider_failure_does_not_stop_later_runs(
        self, db_session: Session
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=2,
        )
        provider = ScriptedProvider(
            outcomes=[ProviderError("boom"), make_result(VALID_OUTPUT)]
        )

        execute_experiment(db_session, experiment.id, provider=provider)

        runs = _runs_for(db_session, experiment.id)
        assert [run.status for run in runs] == [RunStatus.FAILED, RunStatus.COMPLETED]

    def test_experiment_completes_when_all_runs_fail(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=2,
        )
        provider = ScriptedProvider(
            outcomes=[ProviderError("boom"), ProviderTimeoutError("timeout")]
        )

        summary = execute_experiment(db_session, experiment.id, provider=provider)

        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.COMPLETED
        assert summary.failed_runs == 2
        assert summary.completed_runs == 0

    def test_every_run_gets_exactly_one_evaluation(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=4,
        )
        provider = ScriptedProvider(
            outcomes=[
                make_result(VALID_OUTPUT),
                make_result("not json"),
                ProviderError("boom"),
                ProviderTimeoutError("timeout"),
            ]
        )

        execute_experiment(db_session, experiment.id, provider=provider)

        runs = _runs_for(db_session, experiment.id)
        assert len(runs) == 4
        for run in runs:
            evaluations = list(
                db_session.scalars(select(Evaluation).where(Evaluation.run_id == run.id))
            )
            assert len(evaluations) == 1


class TestExecutionGuardrails:
    def test_missing_dataset_item_id_rejected_before_run_creation(
        self, db_session: Session
    ) -> None:
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[999],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )

        with pytest.raises(UnprocessableEntityError):
            execute_experiment(db_session, experiment.id, provider=ScriptedProvider(outcomes=[]))

        assert _runs_for(db_session, experiment.id) == []
        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.DRAFT

    def test_missing_prompt_version_id_rejected_before_run_creation(
        self, db_session: Session
    ) -> None:
        item = _make_dataset_item(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[999],
            model_names=["gpt-5-mini"],
        )

        with pytest.raises(UnprocessableEntityError):
            execute_experiment(db_session, experiment.id, provider=ScriptedProvider(outcomes=[]))

        assert _runs_for(db_session, experiment.id) == []

    def test_unsupported_model_rejected_before_run_creation(
        self, db_session: Session
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-4o-mini"],
        )

        with pytest.raises(UnprocessableEntityError):
            execute_experiment(db_session, experiment.id, provider=ScriptedProvider(outcomes=[]))

        assert _runs_for(db_session, experiment.id) == []
        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.DRAFT

    def test_too_many_planned_runs_rejected_before_run_creation(
        self, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setenv("MAX_RUNS_PER_EXPERIMENT", "2")
        get_settings.cache_clear()

        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=3,
        )

        with pytest.raises(UnprocessableEntityError):
            execute_experiment(db_session, experiment.id, provider=ScriptedProvider(outcomes=[]))

        assert _runs_for(db_session, experiment.id) == []

    def test_repeated_execution_is_rejected(self, db_session: Session) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        execute_experiment(
            db_session, experiment.id, provider=ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)])
        )

        with pytest.raises(ConflictError):
            execute_experiment(db_session, experiment.id, provider=ScriptedProvider(outcomes=[]))

    @pytest.mark.parametrize(
        "status",
        [ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED, ExperimentStatus.FAILED],
    )
    def test_non_draft_experiment_is_rejected(
        self, db_session: Session, status: ExperimentStatus
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            status=status,
        )

        with pytest.raises(ConflictError):
            execute_experiment(db_session, experiment.id, provider=ScriptedProvider(outcomes=[]))

    def test_missing_api_key_rejected_before_run_creation(
        self, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        get_settings.cache_clear()

        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )

        with pytest.raises(ProviderUnavailableError):
            execute_experiment(db_session, experiment.id)

        assert _runs_for(db_session, experiment.id) == []
        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.DRAFT


class TestOrchestrationFailure:
    def test_unexpected_provider_failure_marks_experiment_failed(
        self, db_session: Session
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[RuntimeError("unexpected bug")])

        with pytest.raises(OrchestrationError):
            execute_experiment(db_session, experiment.id, provider=provider)

        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.FAILED

    def test_scoring_failure_marks_experiment_failed_and_leaves_no_partial_scores(
        self, db_session: Session, monkeypatch
    ) -> None:
        item = _make_dataset_item(db_session)
        prompt = _make_prompt_version(db_session)
        experiment = _make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        provider = ScriptedProvider(outcomes=[make_result(VALID_OUTPUT)])

        def _boom(db, experiment_id):
            raise RuntimeError("scoring exploded")

        monkeypatch.setattr("app.experiments.executor.score_experiment", _boom)

        with pytest.raises(OrchestrationError):
            execute_experiment(db_session, experiment.id, provider=provider)

        db_session.refresh(experiment)
        assert experiment.status == ExperimentStatus.FAILED

        run = _runs_for(db_session, experiment.id)[0]
        evaluation = db_session.scalar(
            select(Evaluation).where(Evaluation.run_id == run.id)
        )
        # The Run/Evaluation created before scoring ran are untouched by
        # the (mocked) scoring failure -- no partially-applied scores.
        assert run.status == RunStatus.COMPLETED
        assert evaluation.quality_score is None
        assert evaluation.consistency_score is None
        assert evaluation.reliability_score is None
