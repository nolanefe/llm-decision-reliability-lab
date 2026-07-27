import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import DatasetItem, PromptVersion
from app.schemas.experiment import ExperimentCreate
from app.services import experiments as service


class TestCreateExperimentRollsBackOnPersistenceFailure:
    def test_session_remains_usable_after_a_failed_commit(
        self, db_session: Session
    ) -> None:
        item = DatasetItem(
            name="x",
            input_text="y",
            expected_category="billing",
            expected_priority="low",
        )
        prompt = PromptVersion(name="p", version=1, template_text="{ticket_text}")
        db_session.add_all([item, prompt])
        db_session.commit()

        # Bypass Pydantic validation (which would normally reject this) to
        # force a DB-level CheckConstraint failure on commit, simulating any
        # persistence-time error.
        payload = ExperimentCreate.model_construct(
            name="bad",
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-4o-mini"],
            repeat_count=999,
        )

        with pytest.raises(SQLAlchemyError):
            service.create_experiment(db_session, payload)

        # A clean rollback must leave the session usable for further work,
        # rather than stuck in SQLAlchemy's pending-rollback state.
        assert service.list_experiments(db_session) == []

        # And the session should still accept a legitimate follow-up write.
        good_payload = ExperimentCreate.model_construct(
            name="good",
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-4o-mini"],
            repeat_count=3,
        )
        created = service.create_experiment(db_session, good_payload)
        assert created.id is not None
