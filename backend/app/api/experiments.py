from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.experiment import ExperimentCreate, ExperimentRead
from app.services import experiments as service

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentRead])
def list_experiments(db: Session = Depends(get_db)) -> list[ExperimentRead]:
    return service.list_experiments(db)


@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(
    experiment_id: int, db: Session = Depends(get_db)
) -> ExperimentRead:
    return service.get_experiment(db, experiment_id)


@router.post("", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreate, db: Session = Depends(get_db)
) -> ExperimentRead:
    return service.create_experiment(db, payload)
