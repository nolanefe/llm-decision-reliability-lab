from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.validators import require_non_blank

TICKET_TEXT_PLACEHOLDER = "{ticket_text}"


class PromptVersionBase(BaseModel):
    name: str
    version: int
    description: str | None = None
    template_text: str

    @field_validator("name", "template_text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        return require_non_blank(value)

    @field_validator("template_text")
    @classmethod
    def _contains_ticket_text_placeholder(cls, value: str) -> str:
        if TICKET_TEXT_PLACEHOLDER not in value:
            raise ValueError(
                f"template_text must contain the {TICKET_TEXT_PLACEHOLDER} placeholder"
            )
        return value


class PromptVersionCreate(PromptVersionBase):
    pass


class PromptVersionRead(PromptVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
