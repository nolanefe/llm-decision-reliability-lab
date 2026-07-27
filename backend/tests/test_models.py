import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    DatasetItem,
    Evaluation,
    Experiment,
    ExperimentStatus,
    FailureCategory,
    PromptVersion,
    Run,
    RunStatus,
)


def make_dataset_item(**overrides) -> DatasetItem:
    defaults = dict(
        name="billing-refund",
        input_text="I was charged twice for my subscription.",
        expected_category="billing",
        expected_priority="high",
    )
    defaults.update(overrides)
    return DatasetItem(**defaults)


def make_prompt_version(**overrides) -> PromptVersion:
    defaults = dict(
        name="triage-baseline",
        version=1,
        template_text="Classify this ticket: {ticket_text}",
    )
    defaults.update(overrides)
    return PromptVersion(**defaults)


def make_experiment(**overrides) -> Experiment:
    defaults = dict(
        name="baseline-comparison",
        repeat_count=3,
        dataset_item_ids=[1],
        prompt_version_ids=[1],
        model_names=["gpt-4o-mini"],
    )
    defaults.update(overrides)
    return Experiment(**defaults)


def make_run(experiment, dataset_item, prompt_version, **overrides) -> Run:
    defaults = dict(
        experiment=experiment,
        dataset_item=dataset_item,
        prompt_version=prompt_version,
        model_name="gpt-4o-mini",
        repetition_index=0,
    )
    defaults.update(overrides)
    return Run(**defaults)


class TestDatasetItem:
    def test_create_and_read(self, db_session: Session) -> None:
        item = make_dataset_item()
        db_session.add(item)
        db_session.commit()

        fetched = db_session.get(DatasetItem, item.id)
        assert fetched is not None
        assert fetched.name == "billing-refund"
        assert fetched.expected_category == "billing"
        assert fetched.expected_priority == "high"
        assert fetched.reference_summary is None
        assert fetched.reference_action is None
        assert fetched.created_at is not None


class TestPromptVersion:
    def test_create_and_read(self, db_session: Session) -> None:
        prompt = make_prompt_version()
        db_session.add(prompt)
        db_session.commit()

        fetched = db_session.get(PromptVersion, prompt.id)
        assert fetched is not None
        assert fetched.name == "triage-baseline"
        assert fetched.version == 1
        assert "{ticket_text}" in fetched.template_text

    def test_unique_name_and_version_constraint(self, db_session: Session) -> None:
        db_session.add(make_prompt_version(name="dup", version=1))
        db_session.commit()

        db_session.add(make_prompt_version(name="dup", version=1))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_same_name_different_version_allowed(self, db_session: Session) -> None:
        db_session.add(make_prompt_version(name="dup", version=1))
        db_session.add(make_prompt_version(name="dup", version=2))
        db_session.commit()


class TestExperiment:
    def test_create_and_read(self, db_session: Session) -> None:
        experiment = make_experiment()
        db_session.add(experiment)
        db_session.commit()

        fetched = db_session.get(Experiment, experiment.id)
        assert fetched is not None
        assert fetched.status == ExperimentStatus.DRAFT
        assert fetched.repeat_count == 3
        assert fetched.started_at is None
        assert fetched.completed_at is None

    @pytest.mark.parametrize("repeat_count", [0, 11, -1])
    def test_repeat_count_out_of_range_rejected(
        self, db_session: Session, repeat_count: int
    ) -> None:
        db_session.add(make_experiment(repeat_count=repeat_count))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.parametrize("repeat_count", [1, 10])
    def test_repeat_count_boundary_allowed(
        self, db_session: Session, repeat_count: int
    ) -> None:
        db_session.add(make_experiment(repeat_count=repeat_count))
        db_session.commit()


class TestRun:
    def test_create_and_read(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(experiment, dataset_item, prompt_version)
        db_session.add(run)
        db_session.commit()

        fetched = db_session.get(Run, run.id)
        assert fetched is not None
        assert fetched.status == RunStatus.PENDING
        assert fetched.model_name == "gpt-4o-mini"
        assert fetched.parsed_output is None

    def test_parsed_output_json_round_trip(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(
            experiment,
            dataset_item,
            prompt_version,
            parsed_output={"category": "billing", "priority": "high"},
        )
        db_session.add(run)
        db_session.commit()
        db_session.expire_all()

        fetched = db_session.get(Run, run.id)
        assert fetched.parsed_output == {"category": "billing", "priority": "high"}

    def test_uniqueness_constraint_on_run_identity(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        db_session.add_all(
            [
                make_run(experiment, dataset_item, prompt_version),
                make_run(experiment, dataset_item, prompt_version),
            ]
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_different_repetition_index_allowed(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        db_session.add_all(
            [
                make_run(
                    experiment, dataset_item, prompt_version, repetition_index=0
                ),
                make_run(
                    experiment, dataset_item, prompt_version, repetition_index=1
                ),
            ]
        )
        db_session.commit()


class TestRelationships:
    def test_experiment_has_many_runs(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run_a = make_run(
            experiment, dataset_item, prompt_version, repetition_index=0
        )
        run_b = make_run(
            experiment, dataset_item, prompt_version, repetition_index=1
        )
        db_session.add_all([run_a, run_b])
        db_session.commit()
        db_session.refresh(experiment)

        assert {r.id for r in experiment.runs} == {run_a.id, run_b.id}
        assert run_a.experiment is experiment

    def test_dataset_item_has_many_runs(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(experiment, dataset_item, prompt_version)
        db_session.add(run)
        db_session.commit()
        db_session.refresh(dataset_item)

        assert dataset_item.runs == [run]
        assert run.dataset_item is dataset_item

    def test_prompt_version_has_many_runs(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(experiment, dataset_item, prompt_version)
        db_session.add(run)
        db_session.commit()
        db_session.refresh(prompt_version)

        assert prompt_version.runs == [run]
        assert run.prompt_version is prompt_version

    def test_experiment_delete_cascades_to_runs(self, db_session: Session) -> None:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(experiment, dataset_item, prompt_version)
        db_session.add(run)
        db_session.commit()
        run_id = run.id

        db_session.delete(experiment)
        db_session.commit()

        assert db_session.get(Run, run_id) is None
        assert db_session.get(DatasetItem, dataset_item.id) is not None
        assert db_session.get(PromptVersion, prompt_version.id) is not None


class TestRunEvaluation:
    def _make_persisted_run(self, db_session: Session) -> Run:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(experiment, dataset_item, prompt_version)
        db_session.add(run)
        db_session.commit()
        return run

    def test_run_has_zero_evaluations_by_default(self, db_session: Session) -> None:
        run = self._make_persisted_run(db_session)
        db_session.refresh(run)
        assert run.evaluation is None

    def test_run_to_evaluation_one_to_one(self, db_session: Session) -> None:
        run = self._make_persisted_run(db_session)
        evaluation = Evaluation(run=run, schema_valid=True)
        db_session.add(evaluation)
        db_session.commit()
        db_session.refresh(run)

        assert run.evaluation is not None
        assert run.evaluation.id == evaluation.id
        assert evaluation.run is run

    def test_run_id_uniqueness_on_evaluation(self, db_session: Session) -> None:
        run = self._make_persisted_run(db_session)
        db_session.add(Evaluation(run=run, schema_valid=True))
        db_session.commit()

        db_session.add(Evaluation(run_id=run.id, schema_valid=False))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_deleting_run_cascades_to_evaluation(self, db_session: Session) -> None:
        run = self._make_persisted_run(db_session)
        evaluation = Evaluation(run=run, schema_valid=True)
        db_session.add(evaluation)
        db_session.commit()
        evaluation_id = evaluation.id

        db_session.delete(run)
        db_session.commit()

        assert db_session.get(Evaluation, evaluation_id) is None


class TestEvaluationConstraints:
    def _make_persisted_run(self, db_session: Session) -> Run:
        experiment = make_experiment()
        dataset_item = make_dataset_item()
        prompt_version = make_prompt_version()
        run = make_run(experiment, dataset_item, prompt_version)
        db_session.add(run)
        db_session.commit()
        return run

    def test_create_and_read_full_evaluation(self, db_session: Session) -> None:
        run = self._make_persisted_run(db_session)
        evaluation = Evaluation(
            run=run,
            schema_valid=True,
            category_correct=True,
            priority_correct=False,
            quality_score=0.8,
            consistency_score=1.0,
            failure_category=FailureCategory.CONTENT_MISMATCH,
            reliability_score=72.5,
            notes="close enough",
        )
        db_session.add(evaluation)
        db_session.commit()

        fetched = db_session.get(Evaluation, evaluation.id)
        assert fetched.quality_score == 0.8
        assert fetched.reliability_score == 72.5
        assert fetched.failure_category == FailureCategory.CONTENT_MISMATCH

    @pytest.mark.parametrize("quality_score", [-0.1, 1.1])
    def test_quality_score_out_of_range_rejected(
        self, db_session: Session, quality_score: float
    ) -> None:
        run = self._make_persisted_run(db_session)
        db_session.add(
            Evaluation(run=run, schema_valid=True, quality_score=quality_score)
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.parametrize("consistency_score", [-0.5, 1.5])
    def test_consistency_score_out_of_range_rejected(
        self, db_session: Session, consistency_score: float
    ) -> None:
        run = self._make_persisted_run(db_session)
        db_session.add(
            Evaluation(
                run=run, schema_valid=True, consistency_score=consistency_score
            )
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.parametrize("reliability_score", [-1.0, 100.1])
    def test_reliability_score_out_of_range_rejected(
        self, db_session: Session, reliability_score: float
    ) -> None:
        run = self._make_persisted_run(db_session)
        db_session.add(
            Evaluation(
                run=run, schema_valid=True, reliability_score=reliability_score
            )
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
