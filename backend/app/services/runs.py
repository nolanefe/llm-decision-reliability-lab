from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.models.experiment import Experiment
from app.models.run import Run


def list_runs_for_experiment(db: Session, experiment_id: int) -> list[Run]:
    if db.get(Experiment, experiment_id) is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")

    return list(
        db.scalars(
            select(Run)
            .where(Run.experiment_id == experiment_id)
            .options(selectinload(Run.evaluation))
            .order_by(Run.id)
        ).all()
    )


def get_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise NotFoundError(f"Run {run_id} not found")
    return run
