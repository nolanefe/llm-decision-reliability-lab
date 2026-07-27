from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnprocessableEntityError
from app.models.dataset_item import DatasetItem
from app.models.enums import ExperimentStatus
from app.models.experiment import Experiment
from app.models.prompt_version import PromptVersion
from app.schemas.experiment import ExperimentCreate


def list_experiments(db: Session) -> list[Experiment]:
    return list(db.scalars(select(Experiment).order_by(Experiment.id)).all())


def get_experiment(db: Session, experiment_id: int) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")
    return experiment


def create_experiment(db: Session, payload: ExperimentCreate) -> Experiment:
    _ensure_dataset_items_exist(db, payload.dataset_item_ids)
    _ensure_prompt_versions_exist(db, payload.prompt_version_ids)

    experiment = Experiment(
        name=payload.name,
        status=ExperimentStatus.DRAFT,
        repeat_count=payload.repeat_count,
        dataset_item_ids=payload.dataset_item_ids,
        prompt_version_ids=payload.prompt_version_ids,
        model_names=payload.model_names,
    )
    db.add(experiment)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(experiment)
    return experiment


def _ensure_dataset_items_exist(db: Session, dataset_item_ids: list[int]) -> None:
    found_ids = set(
        db.scalars(
            select(DatasetItem.id).where(DatasetItem.id.in_(dataset_item_ids))
        ).all()
    )
    missing = sorted(set(dataset_item_ids) - found_ids)
    if missing:
        raise UnprocessableEntityError(f"Unknown dataset_item_ids: {missing}")


def _ensure_prompt_versions_exist(db: Session, prompt_version_ids: list[int]) -> None:
    found_ids = set(
        db.scalars(
            select(PromptVersion.id).where(
                PromptVersion.id.in_(prompt_version_ids)
            )
        ).all()
    )
    missing = sorted(set(prompt_version_ids) - found_ids)
    if missing:
        raise UnprocessableEntityError(f"Unknown prompt_version_ids: {missing}")
