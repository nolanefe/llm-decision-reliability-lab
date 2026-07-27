from pydantic import BaseModel

from app.models.enums import FailureCategory, RunStatus


class FailureEntry(BaseModel):
    """One failed/imperfect Run surfaced by the failure explorer. Deliberately
    excludes ticket text, rendered prompts, and raw provider exception
    details -- only sanitized, bounded fields are exposed."""

    run_id: int
    dataset_item_id: int
    dataset_item_name: str
    prompt_version_id: int
    prompt_version_name: str
    model_name: str
    repetition_index: int
    run_status: RunStatus
    failure_category: FailureCategory
    schema_valid: bool
    category_correct: bool | None
    priority_correct: bool | None
    sanitized_error_message: str | None
    raw_response_preview: str | None
