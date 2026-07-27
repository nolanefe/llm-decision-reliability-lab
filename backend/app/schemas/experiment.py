from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ExperimentStatus
from app.schemas.validators import require_non_blank, require_non_empty, require_unique


class ExperimentCreate(BaseModel):
    name: str
    dataset_item_ids: list[int]
    prompt_version_ids: list[int]
    model_names: list[str]
    repeat_count: int = Field(ge=1, le=10)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        return require_non_blank(value)

    @field_validator("model_names")
    @classmethod
    def _model_names_not_blank(cls, values: list[str]) -> list[str]:
        return [require_non_blank(value) for value in values]

    @field_validator("dataset_item_ids", "prompt_version_ids", "model_names")
    @classmethod
    def _non_empty(cls, values: list) -> list:
        return require_non_empty(values)

    @field_validator("dataset_item_ids", "prompt_version_ids", "model_names")
    @classmethod
    def _unique(cls, values: list) -> list:
        return require_unique(values)


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: ExperimentStatus
    repeat_count: int
    dataset_item_ids: list[int]
    prompt_version_ids: list[int]
    model_names: list[str]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
