from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import FailureCategory
from app.schemas.dataset_item import DatasetItemCreate
from app.schemas.evaluation import EvaluationRead
from app.schemas.experiment import ExperimentCreate
from app.schemas.prompt_version import PromptVersionCreate
from app.schemas.support_triage import SupportTriageOutput


class TestSupportTriageOutput:
    def test_valid_payload(self) -> None:
        output = SupportTriageOutput(
            category="billing",
            priority="high",
            summary="Customer was double charged.",
            recommended_action="Issue a refund for the duplicate charge.",
        )
        assert output.category.value == "billing"
        assert output.priority.value == "high"

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SupportTriageOutput(
                category="not_a_category",
                priority="high",
                summary="x",
                recommended_action="y",
            )

    def test_invalid_priority_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SupportTriageOutput(
                category="billing",
                priority="not_a_priority",
                summary="x",
                recommended_action="y",
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SupportTriageOutput(
                category="billing",
                priority="high",
                summary="x",
                recommended_action="y",
                confidence=0.9,
            )

    @pytest.mark.parametrize("field", ["summary", "recommended_action"])
    def test_blank_fields_rejected(self, field: str) -> None:
        payload = {
            "category": "billing",
            "priority": "high",
            "summary": "x",
            "recommended_action": "y",
            field: "   ",
        }
        with pytest.raises(ValidationError):
            SupportTriageOutput(**payload)


class TestDatasetItemCreate:
    def test_valid_payload(self) -> None:
        item = DatasetItemCreate(
            name="billing-refund",
            input_text="I was charged twice.",
            expected_category="billing",
            expected_priority="high",
        )
        assert item.name == "billing-refund"

    @pytest.mark.parametrize("field", ["name", "input_text"])
    def test_blank_fields_rejected(self, field: str) -> None:
        payload = {
            "name": "billing-refund",
            "input_text": "I was charged twice.",
            "expected_category": "billing",
            "expected_priority": "high",
            field: "   ",
        }
        with pytest.raises(ValidationError):
            DatasetItemCreate(**payload)


class TestPromptVersionCreate:
    def test_valid_payload(self) -> None:
        prompt = PromptVersionCreate(
            name="baseline",
            version=1,
            template_text="Classify: {ticket_text}",
        )
        assert prompt.version == 1

    def test_missing_ticket_text_placeholder_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PromptVersionCreate(
                name="baseline",
                version=1,
                template_text="Classify this ticket without a placeholder.",
            )

    @pytest.mark.parametrize("field", ["name", "template_text"])
    def test_blank_fields_rejected(self, field: str) -> None:
        payload = {
            "name": "baseline",
            "version": 1,
            "template_text": "Classify: {ticket_text}",
            field: "   ",
        }
        with pytest.raises(ValidationError):
            PromptVersionCreate(**payload)


class TestExperimentCreate:
    def _valid_payload(self, **overrides) -> dict:
        payload = dict(
            name="baseline-comparison",
            dataset_item_ids=[1, 2],
            prompt_version_ids=[1, 2],
            model_names=["gpt-4o-mini"],
            repeat_count=3,
        )
        payload.update(overrides)
        return payload

    def test_valid_payload(self) -> None:
        experiment = ExperimentCreate(**self._valid_payload())
        assert experiment.repeat_count == 3

    def test_blank_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(**self._valid_payload(name="   "))

    @pytest.mark.parametrize(
        "field", ["dataset_item_ids", "prompt_version_ids", "model_names"]
    )
    def test_empty_selection_list_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(**self._valid_payload(**{field: []}))

    def test_duplicate_dataset_item_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(**self._valid_payload(dataset_item_ids=[1, 1]))

    def test_duplicate_prompt_version_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(**self._valid_payload(prompt_version_ids=[2, 2]))

    def test_duplicate_model_names_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(
                **self._valid_payload(model_names=["gpt-4o-mini", "gpt-4o-mini"])
            )

    @pytest.mark.parametrize("repeat_count", [0, 11, -1])
    def test_repeat_count_out_of_range_rejected(self, repeat_count: int) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(**self._valid_payload(repeat_count=repeat_count))

    @pytest.mark.parametrize("repeat_count", [1, 10])
    def test_repeat_count_boundary_allowed(self, repeat_count: int) -> None:
        experiment = ExperimentCreate(
            **self._valid_payload(repeat_count=repeat_count)
        )
        assert experiment.repeat_count == repeat_count


class TestEvaluationRead:
    def _valid_payload(self, **overrides) -> dict:
        payload = dict(
            id=1,
            run_id=1,
            schema_valid=True,
            category_correct=True,
            priority_correct=True,
            quality_score=0.5,
            consistency_score=0.5,
            failure_category=None,
            reliability_score=50.0,
            notes=None,
            created_at=datetime.now(timezone.utc),
        )
        payload.update(overrides)
        return payload

    def test_valid_payload(self) -> None:
        evaluation = EvaluationRead(**self._valid_payload())
        assert evaluation.quality_score == 0.5

    def test_failure_category_enum_accepted(self) -> None:
        evaluation = EvaluationRead(
            **self._valid_payload(failure_category=FailureCategory.INVALID_JSON)
        )
        assert evaluation.failure_category == FailureCategory.INVALID_JSON

    @pytest.mark.parametrize("quality_score", [-0.1, 1.1])
    def test_quality_score_out_of_range_rejected(self, quality_score: float) -> None:
        with pytest.raises(ValidationError):
            EvaluationRead(**self._valid_payload(quality_score=quality_score))

    @pytest.mark.parametrize("consistency_score", [-0.1, 1.1])
    def test_consistency_score_out_of_range_rejected(
        self, consistency_score: float
    ) -> None:
        with pytest.raises(ValidationError):
            EvaluationRead(
                **self._valid_payload(consistency_score=consistency_score)
            )

    @pytest.mark.parametrize("reliability_score", [-0.1, 100.1])
    def test_reliability_score_out_of_range_rejected(
        self, reliability_score: float
    ) -> None:
        with pytest.raises(ValidationError):
            EvaluationRead(
                **self._valid_payload(reliability_score=reliability_score)
            )
