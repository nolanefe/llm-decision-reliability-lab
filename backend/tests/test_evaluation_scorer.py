"""Tests for app.evaluation.scorer's transactional behavior: independent
callability, idempotency, and rollback-on-failure. Formula correctness is
covered in test_evaluation_scoring.py; end-to-end wiring through
execute_experiment (including "scoring failure marks the experiment
failed") is covered in test_experiments_executor.py."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import IncompleteExperimentDataError, NotFoundError
from app.evaluation.scorer import score_experiment
from app.models.enums import FailureCategory, RunStatus
from app.models.evaluation import Evaluation
from app.models.run import Run
from tests.factories import (
    make_dataset_item,
    make_evaluation,
    make_experiment,
    make_prompt_version,
    make_run,
)


def _setup_two_run_group(db: Session):
    """One dataset_item_id+prompt_version_id+model_name group of 2 Runs:
    one fully correct, one a content mismatch."""
    item = make_dataset_item(db, expected_category="billing", expected_priority="high")
    prompt = make_prompt_version(db)
    experiment = make_experiment(
        db,
        dataset_item_ids=[item.id],
        prompt_version_ids=[prompt.id],
        model_names=["gpt-5-mini"],
        repeat_count=2,
    )
    run1 = make_run(
        db,
        experiment=experiment,
        dataset_item=item,
        prompt_version=prompt,
        repetition_index=1,
        parsed_output={"category": "billing", "priority": "high"},
    )
    ev1 = make_evaluation(
        db, run=run1, schema_valid=True, category_correct=True, priority_correct=True
    )
    run2 = make_run(
        db,
        experiment=experiment,
        dataset_item=item,
        prompt_version=prompt,
        repetition_index=2,
        parsed_output={"category": "bug", "priority": "low"},
    )
    ev2 = make_evaluation(
        db,
        run=run2,
        schema_valid=True,
        category_correct=False,
        priority_correct=False,
        failure_category=FailureCategory.CONTENT_MISMATCH,
    )
    return experiment, [(run1, ev1), (run2, ev2)]


class TestScorerIndependentAndIdempotent:
    def test_scorer_can_run_independently_of_the_executor(self, db_session: Session):
        experiment, rows = _setup_two_run_group(db_session)

        score_experiment(db_session, experiment.id)

        for _run, evaluation in rows:
            db_session.refresh(evaluation)
        assert rows[0][1].quality_score == 1.0
        assert rows[1][1].quality_score == 0.0
        assert rows[0][1].consistency_score == 0.5
        assert rows[1][1].consistency_score == 0.5

    def test_all_evaluations_are_updated(self, db_session: Session):
        experiment, _rows = _setup_two_run_group(db_session)

        score_experiment(db_session, experiment.id)

        evaluations = db_session.scalars(select(Evaluation)).all()
        assert len(evaluations) == 2
        for evaluation in evaluations:
            assert evaluation.quality_score is not None
            assert evaluation.consistency_score is not None
            assert evaluation.reliability_score is not None

    def test_scoring_is_idempotent(self, db_session: Session):
        experiment, rows = _setup_two_run_group(db_session)

        score_experiment(db_session, experiment.id)
        first_pass = {
            evaluation.id: (
                evaluation.quality_score,
                evaluation.consistency_score,
                evaluation.reliability_score,
            )
            for _run, evaluation in rows
        }

        score_experiment(db_session, experiment.id)
        for _run, evaluation in rows:
            db_session.refresh(evaluation)
        second_pass = {
            evaluation.id: (
                evaluation.quality_score,
                evaluation.consistency_score,
                evaluation.reliability_score,
            )
            for _run, evaluation in rows
        }

        assert first_pass == second_pass

    def test_missing_experiment_raises_not_found(self, db_session: Session):
        with pytest.raises(NotFoundError):
            score_experiment(db_session, 999)


class TestScorerRollbackAndDataIntegrity:
    def test_failure_rolls_back_all_partial_updates(
        self, db_session: Session, monkeypatch
    ) -> None:
        experiment, rows = _setup_two_run_group(db_session)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.evaluation.scorer.compute_reliability_score", _boom)

        with pytest.raises(RuntimeError):
            score_experiment(db_session, experiment.id)

        for _run, evaluation in rows:
            db_session.refresh(evaluation)
        for _run, evaluation in rows:
            assert evaluation.quality_score is None
            assert evaluation.consistency_score is None
            assert evaluation.reliability_score is None

    def test_incomplete_data_raises_controlled_error(self, db_session: Session) -> None:
        item = make_dataset_item(db_session)
        prompt = make_prompt_version(db_session)
        experiment = make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
        )
        # A terminal Run with no Evaluation at all: a data-integrity gap
        # the executor's normal flow can never produce, but scoring must
        # still fail in a controlled way rather than silently drop it.
        db_session.add(
            Run(
                experiment_id=experiment.id,
                dataset_item_id=item.id,
                prompt_version_id=prompt.id,
                model_name="gpt-5-mini",
                repetition_index=1,
                status=RunStatus.COMPLETED,
            )
        )
        db_session.commit()

        with pytest.raises(IncompleteExperimentDataError):
            score_experiment(db_session, experiment.id)
