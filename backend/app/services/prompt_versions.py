from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.prompt_version import PromptVersion
from app.schemas.prompt_version import PromptVersionCreate


def list_prompt_versions(db: Session) -> list[PromptVersion]:
    return list(db.scalars(select(PromptVersion).order_by(PromptVersion.id)).all())


def get_prompt_version(db: Session, prompt_version_id: int) -> PromptVersion:
    prompt_version = db.get(PromptVersion, prompt_version_id)
    if prompt_version is None:
        raise NotFoundError(f"Prompt version {prompt_version_id} not found")
    return prompt_version


def create_prompt_version(db: Session, payload: PromptVersionCreate) -> PromptVersion:
    existing = db.scalar(
        select(PromptVersion.id).where(
            PromptVersion.name == payload.name,
            PromptVersion.version == payload.version,
        )
    )
    if existing is not None:
        raise ConflictError(
            f"Prompt version '{payload.name}' v{payload.version} already exists"
        )

    prompt_version = PromptVersion(
        name=payload.name,
        version=payload.version,
        description=payload.description,
        template_text=payload.template_text,
    )
    db.add(prompt_version)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            f"Prompt version '{payload.name}' v{payload.version} already exists"
        ) from None
    db.refresh(prompt_version)
    return prompt_version
