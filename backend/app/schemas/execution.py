from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ExperimentStatus


class ExecutionSummary(BaseModel):
    experiment_id: int
    status: ExperimentStatus
    planned_runs: int
    completed_runs: int
    failed_runs: int
    schema_valid_runs: int
    schema_invalid_runs: int
    started_at: datetime | None
    completed_at: datetime | None
