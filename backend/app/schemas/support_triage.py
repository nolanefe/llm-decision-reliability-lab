from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.enums import TicketCategory, TicketPriority
from app.schemas.validators import require_non_blank


class SupportTriageOutput(BaseModel):
    """The structured JSON shape every model response must conform to."""

    model_config = ConfigDict(extra="forbid")

    category: TicketCategory
    priority: TicketPriority
    summary: str
    recommended_action: str

    @field_validator("summary", "recommended_action")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        return require_non_blank(value)
