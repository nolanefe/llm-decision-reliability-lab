"""Idempotent seeding of built-in dataset items and prompt versions.

Run via: ``python -m app.db.seed`` (from the ``backend/`` directory, with the
virtualenv active and ``alembic upgrade head`` already applied).

This module is intentionally not imported or executed during application
startup — seeding is an explicit, operator-triggered action.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed_data import DATASET_ITEMS, PROMPT_VERSIONS
from app.models.dataset_item import DatasetItem
from app.models.prompt_version import PromptVersion


@dataclass
class SeedSummary:
    dataset_items_inserted: int
    dataset_items_skipped: int
    prompt_versions_inserted: int
    prompt_versions_skipped: int


def seed_dataset_items(db: Session) -> tuple[int, int]:
    """Insert built-in dataset items that don't already exist, matched by name.

    Existing rows (including user-created ones) are never modified.
    """
    inserted = 0
    skipped = 0
    for item in DATASET_ITEMS:
        exists = db.scalar(
            select(DatasetItem.id).where(DatasetItem.name == item["name"])
        )
        if exists is not None:
            skipped += 1
            continue
        db.add(DatasetItem(**item))
        inserted += 1
    return inserted, skipped


def seed_prompt_versions(db: Session) -> tuple[int, int]:
    """Insert built-in prompt versions that don't already exist, matched by
    (name, version) — the same key the table's unique constraint enforces.

    Existing rows (including user-created ones) are never modified.
    """
    inserted = 0
    skipped = 0
    for prompt in PROMPT_VERSIONS:
        exists = db.scalar(
            select(PromptVersion.id).where(
                PromptVersion.name == prompt["name"],
                PromptVersion.version == prompt["version"],
            )
        )
        if exists is not None:
            skipped += 1
            continue
        db.add(PromptVersion(**prompt))
        inserted += 1
    return inserted, skipped


def run_seed(db: Session) -> SeedSummary:
    """Seed built-in dataset items and prompt versions. Safe to call repeatedly."""
    dataset_inserted, dataset_skipped = seed_dataset_items(db)
    prompt_inserted, prompt_skipped = seed_prompt_versions(db)
    db.commit()
    return SeedSummary(
        dataset_items_inserted=dataset_inserted,
        dataset_items_skipped=dataset_skipped,
        prompt_versions_inserted=prompt_inserted,
        prompt_versions_skipped=prompt_skipped,
    )


def main() -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        summary = run_seed(db)
    finally:
        db.close()

    print(
        "Seed complete: "
        f"dataset_items inserted={summary.dataset_items_inserted} "
        f"skipped={summary.dataset_items_skipped}; "
        f"prompt_versions inserted={summary.prompt_versions_inserted} "
        f"skipped={summary.prompt_versions_skipped}"
    )


if __name__ == "__main__":
    main()
