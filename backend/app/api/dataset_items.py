from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dataset_item import DatasetItemCreate, DatasetItemRead
from app.services import dataset_items as service

router = APIRouter(prefix="/api/v1/dataset-items", tags=["dataset-items"])


@router.get("", response_model=list[DatasetItemRead])
def list_dataset_items(db: Session = Depends(get_db)) -> list[DatasetItemRead]:
    return service.list_dataset_items(db)


@router.get("/{dataset_item_id}", response_model=DatasetItemRead)
def get_dataset_item(
    dataset_item_id: int, db: Session = Depends(get_db)
) -> DatasetItemRead:
    return service.get_dataset_item(db, dataset_item_id)


@router.post(
    "", response_model=DatasetItemRead, status_code=status.HTTP_201_CREATED
)
def create_dataset_item(
    payload: DatasetItemCreate, db: Session = Depends(get_db)
) -> DatasetItemRead:
    return service.create_dataset_item(db, payload)
