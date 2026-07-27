from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import FailureCategory


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    schema_valid: bool
    category_correct: bool | None
    priority_correct: bool | None
    quality_score: float | None
    consistency_score: float | None
    failure_category: FailureCategory | None
    reliability_score: float | None
    notes: str | None
    created_at: datetime

    @field_validator("quality_score", "consistency_score")
    @classmethod
    def _validate_unit_score(cls, value: float | None) -> float | None:
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("must be between 0.0 and 1.0")
        return value

    @field_validator("reliability_score")
    @classmethod
    def _validate_reliability_score(cls, value: float | None) -> float | None:
        if value is not None and not (0.0 <= value <= 100.0):
            raise ValueError("must be between 0.0 and 100.0")
        return value
