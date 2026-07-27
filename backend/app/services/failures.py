from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.evaluation.failures import build_failure_entries
from app.models.experiment import Experiment
from app.schemas.failure import FailureEntry


def get_experiment_failures(db: Session, experiment_id: int) -> list[FailureEntry]:
    if db.get(Experiment, experiment_id) is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")

    return build_failure_entries(db, experiment_id)
