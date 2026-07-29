"""Deterministic fixture data for the frontend Playwright suite.

Run via: ``python scripts/e2e_seed.py`` (from ``backend/``, with
``DATABASE_URL`` pointing at a migrated, empty temporary database --
``alembic upgrade head`` must already have been applied).

This is test-support tooling only. It is never imported by the application
and is not wired into any startup path. All content below is fictional
placeholder data, kept separate from ``app/db/seed_data.py`` (the real
development seed content) so E2E fixtures never drift with production
sample data.

Every insert below relies on a fresh, empty database (autoincrement IDs
starting at 1), which is guaranteed by the Playwright config: it always
recreates the SQLite file before running this script.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models  # noqa: E402,F401
from app.db.session import build_engine  # noqa: E402
from app.models.dataset_item import DatasetItem  # noqa: E402
from app.models.enums import ExperimentStatus  # noqa: E402
from app.models.experiment import Experiment  # noqa: E402
from app.models.prompt_version import PromptVersion  # noqa: E402

COMPLETED_EXPERIMENT_NAME = "Seeded completed experiment"


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    engine = build_engine(database_url)
    session_local = sessionmaker(bind=engine)
    db = session_local()
    try:
        item_billing = DatasetItem(
            name="e2e-billing-duplicate-charge",
            input_text=(
                "I was charged twice for my subscription this month. Please "
                "refund the duplicate charge."
            ),
            expected_category="billing",
            expected_priority="high",
            reference_summary="Customer was double-charged and wants a refund.",
            reference_action="Verify the duplicate charge and refund it.",
        )
        item_account = DatasetItem(
            name="e2e-account-locked-out",
            input_text=(
                "I am locked out of my account after too many failed login "
                "attempts and need back in urgently."
            ),
            expected_category="account_access",
            expected_priority="urgent",
            reference_summary="Customer is locked out of their account.",
            reference_action="Verify identity and unlock the account.",
        )
        db.add_all([item_billing, item_account])
        db.commit()
        db.refresh(item_billing)
        db.refresh(item_account)

        prompt_baseline = PromptVersion(
            name="e2e-baseline-triage",
            version=1,
            description="E2E fixture: simple structured triage instruction.",
            template_text="Classify this ticket: {ticket_text}",
        )
        prompt_explicit = PromptVersion(
            name="e2e-explicit-criteria-triage",
            version=1,
            description="E2E fixture: explicit category/priority definitions.",
            template_text="Classify this ticket using explicit criteria: {ticket_text}",
        )
        db.add_all([prompt_baseline, prompt_explicit])
        db.commit()
        db.refresh(prompt_baseline)
        db.refresh(prompt_explicit)

        now = datetime.now(timezone.utc)
        completed_experiment = Experiment(
            name=COMPLETED_EXPERIMENT_NAME,
            status=ExperimentStatus.COMPLETED,
            repeat_count=1,
            dataset_item_ids=[item_billing.id, item_account.id],
            prompt_version_ids=[prompt_baseline.id, prompt_explicit.id],
            model_names=["gpt-5-mini", "gpt-5-nano"],
            started_at=now,
            completed_at=now,
        )
        db.add(completed_experiment)
        db.commit()

        print(
            "E2E seed complete: "
            f"dataset_items=[{item_billing.id}, {item_account.id}] "
            f"prompt_versions=[{prompt_baseline.id}, {prompt_explicit.id}] "
            f"completed_experiment_id={completed_experiment.id}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
