from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.experiments import executor
from app.llm.provider import LLMProvider
from app.schemas.execution import ExecutionSummary
from app.schemas.experiment import ExperimentCreate, ExperimentRead
from app.schemas.run import RunRead
from app.services import experiments as service
from app.services import runs as runs_service

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


@router.post("/{experiment_id}/execute", response_model=ExecutionSummary)
def execute_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    provider: LLMProvider | None = Depends(executor.get_llm_provider),
) -> ExecutionSummary:
    return executor.execute_experiment(db, experiment_id, provider=provider)


@router.get("/{experiment_id}/runs", response_model=list[RunRead])
def list_experiment_runs(
    experiment_id: int, db: Session = Depends(get_db)
) -> list[RunRead]:
    return runs_service.list_runs_for_experiment(db, experiment_id)
