"""Tests for app.evaluation.failures.build_failure_entries: every failure
category is surfaced, successful Runs are excluded, previews are bounded,
no ticket text/prompt/raw provider exception details leak, and ordering
is deterministic."""

from sqlalchemy.orm import Session

from app.evaluation.failures import build_failure_entries
from app.models.enums import FailureCategory, RunStatus
from tests.factories import make_dataset_item, make_evaluation, make_experiment, make_prompt_version, make_run


def _setup(db: Session):
    item = make_dataset_item(
        db,
        name="secret-ticket-name",
        input_text="Extremely sensitive ticket text that must never leak.",
        expected_category="billing",
        expected_priority="high",
    )
    prompt = make_prompt_version(db, name="prompt", version=1)
    experiment = make_experiment(
        db,
        dataset_item_ids=[item.id],
        prompt_version_ids=[prompt.id],
        model_names=["gpt-5-mini"],
        repeat_count=6,
    )
    return item, prompt, experiment


class TestFailureCategoryCoverage:
    def test_includes_every_failure_category(self, db_session: Session) -> None:
        item, prompt, experiment = _setup(db_session)

        run_invalid_json = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1, raw_response="not json",
        )
        make_evaluation(
            db_session, run=run_invalid_json, schema_valid=False,
            failure_category=FailureCategory.INVALID_JSON,
        )

        run_schema_error = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=2, raw_response='{"foo": "bar"}',
        )
        make_evaluation(
            db_session, run=run_schema_error, schema_valid=False,
            failure_category=FailureCategory.SCHEMA_ERROR,
        )

        run_content_mismatch = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=3,
            raw_response='{"category": "bug", "priority": "low"}',
            parsed_output={"category": "bug", "priority": "low"},
        )
        make_evaluation(
            db_session, run=run_content_mismatch, schema_valid=True,
            category_correct=False, priority_correct=False,
            failure_category=FailureCategory.CONTENT_MISMATCH,
        )

        run_timeout = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=4, status=RunStatus.FAILED, raw_response=None,
            latency_ms=None, prompt_tokens=None, completion_tokens=None, total_tokens=None,
            estimated_cost_usd=None, error_message="Request timed out",
        )
        make_evaluation(
            db_session, run=run_timeout, schema_valid=False,
            failure_category=FailureCategory.TIMEOUT,
        )

        run_provider_error = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=5, status=RunStatus.FAILED, raw_response=None,
            latency_ms=None, prompt_tokens=None, completion_tokens=None, total_tokens=None,
            estimated_cost_usd=None, error_message="Provider request failed",
        )
        make_evaluation(
            db_session, run=run_provider_error, schema_valid=False,
            failure_category=FailureCategory.PROVIDER_ERROR,
        )

        run_other = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=6, raw_response='{"category": "billing"}',
        )
        make_evaluation(
            db_session, run=run_other, schema_valid=False,
            failure_category=FailureCategory.OTHER,
        )

        entries = build_failure_entries(db_session, experiment.id)

        categories = {entry.failure_category for entry in entries}
        assert categories == {
            FailureCategory.INVALID_JSON,
            FailureCategory.SCHEMA_ERROR,
            FailureCategory.CONTENT_MISMATCH,
            FailureCategory.TIMEOUT,
            FailureCategory.PROVIDER_ERROR,
            FailureCategory.OTHER,
        }
        assert len(entries) == 6

    def test_content_mismatch_entry_reflects_which_labels_were_wrong(
        self, db_session: Session
    ) -> None:
        item, prompt, experiment = _setup(db_session)
        run = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1,
            raw_response='{"category": "bug", "priority": "high"}',
            parsed_output={"category": "bug", "priority": "high"},
        )
        make_evaluation(
            db_session, run=run, schema_valid=True,
            category_correct=False, priority_correct=True,
            failure_category=FailureCategory.CONTENT_MISMATCH,
        )

        entries = build_failure_entries(db_session, experiment.id)

        assert len(entries) == 1
        assert entries[0].failure_category == FailureCategory.CONTENT_MISMATCH
        assert entries[0].category_correct is False
        assert entries[0].priority_correct is True
        assert entries[0].schema_valid is True


class TestExcludesSuccesses:
    def test_fully_correct_run_is_excluded(self, db_session: Session) -> None:
        item, prompt, experiment = _setup(db_session)
        run = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1,
            raw_response='{"category": "billing", "priority": "high"}',
            parsed_output={"category": "billing", "priority": "high"},
        )
        make_evaluation(
            db_session, run=run, schema_valid=True,
            category_correct=True, priority_correct=True, failure_category=None,
        )

        entries = build_failure_entries(db_session, experiment.id)

        assert entries == []

    def test_empty_list_for_experiment_with_no_runs(self, db_session: Session) -> None:
        _item, _prompt, experiment = _setup(db_session)

        entries = build_failure_entries(db_session, experiment.id)

        assert entries == []


class TestPreviewAndSanitization:
    def test_preview_is_capped_at_200_characters(self, db_session: Session) -> None:
        item, prompt, experiment = _setup(db_session)
        long_response = "x" * 500
        run = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1, raw_response=long_response,
        )
        make_evaluation(
            db_session, run=run, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )

        entries = build_failure_entries(db_session, experiment.id)

        assert len(entries[0].raw_response_preview) == 200

    def test_no_ticket_text_or_prompt_leakage(self, db_session: Session) -> None:
        item, prompt, experiment = _setup(db_session)
        run = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1, raw_response="not json",
        )
        make_evaluation(
            db_session, run=run, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )

        entries = build_failure_entries(db_session, experiment.id)

        entry = entries[0]
        assert item.input_text not in (entry.raw_response_preview or "")
        assert item.name not in (entry.raw_response_preview or "")
        assert "input_text" not in entry.model_dump_json()

    def test_error_messages_are_sanitized_not_raw_exception_text(
        self, db_session: Session
    ) -> None:
        item, prompt, experiment = _setup(db_session)
        run = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1, status=RunStatus.FAILED, raw_response=None,
            latency_ms=None, prompt_tokens=None, completion_tokens=None, total_tokens=None,
            estimated_cost_usd=None, error_message="Provider request failed",
        )
        make_evaluation(
            db_session, run=run, schema_valid=False, failure_category=FailureCategory.PROVIDER_ERROR
        )

        entries = build_failure_entries(db_session, experiment.id)

        assert entries[0].sanitized_error_message == "Provider request failed"
        assert "Traceback" not in entries[0].sanitized_error_message

    def test_defends_against_an_upstream_message_that_is_not_actually_sanitized(
        self, db_session: Session
    ) -> None:
        """The real OpenAIProvider only ever raises short, fixed, safe
        strings (see app/llm/openai_provider.py) -- but this module is the
        one that promises a *sanitized* message, so it must not blindly
        trust that discipline held upstream. Simulates a misbehaving
        provider that leaked a traceback, an absolute path, and an API key
        straight into error_message."""
        item, prompt, experiment = _setup(db_session)
        leaky_message = (
            'Upstream provider returned HTTP 500: Traceback (most recent call '
            'last): File "/Users/someone/secret/openai_provider.py", line 42, '
            'in generate raise ConnectionError(api_key="sk-should-not-leak")'
        )
        run = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1, status=RunStatus.FAILED, raw_response=None,
            latency_ms=None, prompt_tokens=None, completion_tokens=None, total_tokens=None,
            estimated_cost_usd=None, error_message=leaky_message,
        )
        make_evaluation(
            db_session, run=run, schema_valid=False, failure_category=FailureCategory.PROVIDER_ERROR
        )

        entries = build_failure_entries(db_session, experiment.id)
        sanitized = entries[0].sanitized_error_message

        assert sanitized == "Upstream provider returned HTTP 500:"
        assert "Traceback" not in sanitized
        assert "sk-should-not-leak" not in sanitized
        assert "/Users/" not in sanitized


class TestDeterministicOrdering:
    def test_ordered_by_run_id_ascending(self, db_session: Session) -> None:
        item, prompt, experiment = _setup(db_session)
        run_a = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=1, raw_response="not json",
        )
        make_evaluation(
            db_session, run=run_a, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )
        run_b = make_run(
            db_session, experiment=experiment, dataset_item=item, prompt_version=prompt,
            repetition_index=2, raw_response="also not json",
        )
        make_evaluation(
            db_session, run=run_b, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )

        entries = build_failure_entries(db_session, experiment.id)

        assert [entry.run_id for entry in entries] == sorted(
            entry.run_id for entry in entries
        )
        assert entries[0].run_id == run_a.id
        assert entries[1].run_id == run_b.id
