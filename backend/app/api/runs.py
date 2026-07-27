from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run import RunRead
from app.services import runs as service

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: int, db: Session = Depends(get_db)) -> RunRead:
    return service.get_run(db, run_id)
