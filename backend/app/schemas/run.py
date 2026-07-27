from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import RunStatus
from app.schemas.evaluation import EvaluationRead


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    dataset_item_id: int
    prompt_version_id: int
    model_name: str
    repetition_index: int
    status: RunStatus
    raw_response: str | None
    parsed_output: dict[str, Any] | None
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    evaluation: EvaluationRead | None
