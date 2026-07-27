from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.prompt_version import PromptVersionCreate, PromptVersionRead
from app.services import prompt_versions as service

router = APIRouter(prefix="/api/v1/prompt-versions", tags=["prompt-versions"])


@router.get("", response_model=list[PromptVersionRead])
def list_prompt_versions(db: Session = Depends(get_db)) -> list[PromptVersionRead]:
    return service.list_prompt_versions(db)


@router.get("/{prompt_version_id}", response_model=PromptVersionRead)
def get_prompt_version(
    prompt_version_id: int, db: Session = Depends(get_db)
) -> PromptVersionRead:
    return service.get_prompt_version(db, prompt_version_id)


@router.post(
    "", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED
)
def create_prompt_version(
    payload: PromptVersionCreate, db: Session = Depends(get_db)
) -> PromptVersionRead:
    return service.create_prompt_version(db, payload)
