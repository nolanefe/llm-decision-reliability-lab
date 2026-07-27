from sqlalchemy.orm import Session

from app.db.seed import run_seed
from app.db.seed_data import DATASET_ITEMS, PROMPT_VERSIONS
from app.models import DatasetItem, PromptVersion


class TestSeedInsertsExpectedRecords:
    def test_inserts_all_dataset_items_and_prompt_versions(
        self, db_session: Session
    ) -> None:
        summary = run_seed(db_session)

        assert summary.dataset_items_inserted == len(DATASET_ITEMS)
        assert summary.dataset_items_skipped == 0
        assert summary.prompt_versions_inserted == len(PROMPT_VERSIONS)
        assert summary.prompt_versions_skipped == 0

        assert db_session.query(DatasetItem).count() == len(DATASET_ITEMS)
        assert db_session.query(PromptVersion).count() == len(PROMPT_VERSIONS)

    def test_dataset_items_cover_required_categories_and_priorities(
        self, db_session: Session
    ) -> None:
        run_seed(db_session)

        categories = {item.expected_category for item in db_session.query(DatasetItem)}
        priorities = {item.expected_priority for item in db_session.query(DatasetItem)}

        assert categories == {
            "billing",
            "account_access",
            "bug",
            "feature_request",
            "other",
        }
        assert priorities == {"low", "medium", "high", "urgent"}

    def test_prompt_versions_all_contain_ticket_text_placeholder(
        self, db_session: Session
    ) -> None:
        run_seed(db_session)

        prompts = db_session.query(PromptVersion).all()
        assert len(prompts) == 3
        for prompt in prompts:
            assert "{ticket_text}" in prompt.template_text


class TestSeedIsIdempotent:
    def test_running_seed_twice_does_not_duplicate_rows(
        self, db_session: Session
    ) -> None:
        run_seed(db_session)
        second = run_seed(db_session)

        assert second.dataset_items_inserted == 0
        assert second.dataset_items_skipped == len(DATASET_ITEMS)
        assert second.prompt_versions_inserted == 0
        assert second.prompt_versions_skipped == len(PROMPT_VERSIONS)

        assert db_session.query(DatasetItem).count() == len(DATASET_ITEMS)
        assert db_session.query(PromptVersion).count() == len(PROMPT_VERSIONS)


class TestSeedDoesNotOverwriteExistingRecords:
    def test_existing_dataset_item_with_matching_name_is_preserved(
        self, db_session: Session
    ) -> None:
        seed_item = DATASET_ITEMS[0]
        custom = DatasetItem(
            name=seed_item["name"],
            input_text="A user-edited version of this ticket.",
            expected_category="other",
            expected_priority="low",
        )
        db_session.add(custom)
        db_session.commit()

        run_seed(db_session)

        db_session.refresh(custom)
        assert custom.input_text == "A user-edited version of this ticket."
        assert custom.expected_category == "other"

        matching = (
            db_session.query(DatasetItem)
            .filter(DatasetItem.name == seed_item["name"])
            .all()
        )
        assert len(matching) == 1

    def test_existing_prompt_version_with_matching_key_is_preserved(
        self, db_session: Session
    ) -> None:
        seed_prompt = PROMPT_VERSIONS[0]
        custom = PromptVersion(
            name=seed_prompt["name"],
            version=seed_prompt["version"],
            template_text="A user-edited template with {ticket_text}.",
        )
        db_session.add(custom)
        db_session.commit()

        run_seed(db_session)

        db_session.refresh(custom)
        assert custom.template_text == "A user-edited template with {ticket_text}."

        matching = (
            db_session.query(PromptVersion)
            .filter(
                PromptVersion.name == seed_prompt["name"],
                PromptVersion.version == seed_prompt["version"],
            )
            .all()
        )
        assert len(matching) == 1
