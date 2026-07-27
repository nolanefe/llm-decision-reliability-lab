from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.enums import TicketCategory, TicketPriority
from app.schemas.validators import require_non_blank


class DatasetItemBase(BaseModel):
    name: str
    input_text: str
    expected_category: TicketCategory
    expected_priority: TicketPriority
    reference_summary: str | None = None
    reference_action: str | None = None

    @field_validator("name", "input_text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        return require_non_blank(value)


class DatasetItemCreate(DatasetItemBase):
    pass


class DatasetItemRead(DatasetItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
