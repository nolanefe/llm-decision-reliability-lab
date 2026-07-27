from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.dataset_item import DatasetItem
from app.schemas.dataset_item import DatasetItemCreate


def list_dataset_items(db: Session) -> list[DatasetItem]:
    return list(db.scalars(select(DatasetItem).order_by(DatasetItem.id)).all())


def get_dataset_item(db: Session, dataset_item_id: int) -> DatasetItem:
    item = db.get(DatasetItem, dataset_item_id)
    if item is None:
        raise NotFoundError(f"Dataset item {dataset_item_id} not found")
    return item


def create_dataset_item(db: Session, payload: DatasetItemCreate) -> DatasetItem:
    item = DatasetItem(
        name=payload.name,
        input_text=payload.input_text,
        expected_category=payload.expected_category.value,
        expected_priority=payload.expected_priority.value,
        reference_summary=payload.reference_summary,
        reference_action=payload.reference_action,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
