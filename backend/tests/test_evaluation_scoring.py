"""Unit tests for the centralized scoring formulas in
app.evaluation.scoring. Pure functions -- no DB, no provider, no network."""

import pytest

from app.evaluation.scoring import (
    compute_group_consistency_score,
    compute_quality_score,
    compute_reliability_score,
)
from app.models.enums import RunStatus


class TestQualityScore:
    def test_both_labels_correct_gives_one(self):
        assert (
            compute_quality_score(
                schema_valid=True, category_correct=True, priority_correct=True
            )
            == 1.0
        )

    def test_one_label_correct_gives_half(self):
        assert (
            compute_quality_score(
                schema_valid=True, category_correct=True, priority_correct=False
            )
            == 0.5
        )
        assert (
            compute_quality_score(
                schema_valid=True, category_correct=False, priority_correct=True
            )
            == 0.5
        )

    def test_neither_label_correct_gives_zero(self):
        assert (
            compute_quality_score(
                schema_valid=True, category_correct=False, priority_correct=False
            )
            == 0.0
        )

    def test_schema_invalid_gives_zero(self):
        assert (
            compute_quality_score(
                schema_valid=False, category_correct=None, priority_correct=None
            )
            == 0.0
        )

    def test_provider_failure_gives_zero(self):
        # _fail_run always records schema_valid=False with no correctness
        # flags -- exercised at the executor level too, but the formula
        # itself must treat it identically to any other invalid output.
        assert (
            compute_quality_score(
                schema_valid=False, category_correct=None, priority_correct=None
            )
            == 0.0
        )


class TestConsistencyScore:
    def test_identical_repeated_outputs_give_one(self):
        outcomes = [("billing", "high")] * 3
        assert (
            compute_group_consistency_score(
                valid_outcomes=outcomes, total_planned_runs=3
            )
            == 1.0
        )

    def test_mixed_valid_outcomes_produce_correct_modal_fraction(self):
        outcomes = [("billing", "high"), ("billing", "high"), ("bug", "low")]
        score = compute_group_consistency_score(
            valid_outcomes=outcomes, total_planned_runs=3
        )
        assert score == pytest.approx(2 / 3, abs=1e-4)

    def test_invalid_outputs_lower_consistency_through_denominator(self):
        # 3 planned runs but only 2 produced a (matching) valid outcome.
        outcomes = [("billing", "high"), ("billing", "high")]
        score = compute_group_consistency_score(
            valid_outcomes=outcomes, total_planned_runs=3
        )
        assert score == pytest.approx(2 / 3, abs=1e-4)

    def test_provider_failures_lower_consistency(self):
        # 4 planned runs, 2 of them provider failures with no outcome at all.
        outcomes = [("billing", "high"), ("billing", "high")]
        score = compute_group_consistency_score(
            valid_outcomes=outcomes, total_planned_runs=4
        )
        assert score == 0.5

    def test_no_valid_outputs_gives_zero(self):
        assert (
            compute_group_consistency_score(valid_outcomes=[], total_planned_runs=3)
            == 0.0
        )

    def test_repeat_count_one_valid_output_gives_one(self):
        assert (
            compute_group_consistency_score(
                valid_outcomes=[("billing", "high")], total_planned_runs=1
            )
            == 1.0
        )

    def test_ties_are_deterministic(self):
        outcomes_forward = [("billing", "high"), ("bug", "low")]
        outcomes_reversed = [("bug", "low"), ("billing", "high")]
        score_forward = compute_group_consistency_score(
            valid_outcomes=outcomes_forward, total_planned_runs=2
        )
        score_reversed = compute_group_consistency_score(
            valid_outcomes=outcomes_reversed, total_planned_runs=2
        )
        assert score_forward == score_reversed == 0.5

    def test_zero_planned_runs_gives_zero(self):
        assert (
            compute_group_consistency_score(valid_outcomes=[], total_planned_runs=0)
            == 0.0
        )


class TestReliabilityScore:
    def test_exact_formula_all_components_present(self):
        score = compute_reliability_score(
            quality_score=1.0,
            consistency_score=1.0,
            schema_valid=True,
            run_status=RunStatus.COMPLETED,
        )
        assert score == 100.0

    def test_exact_formula_partial_components(self):
        score = compute_reliability_score(
            quality_score=0.5,
            consistency_score=0.5,
            schema_valid=True,
            run_status=RunStatus.COMPLETED,
        )
        # 100 * (0.6*0.5 + 0.2*0.5 + 0.1*1 + 0.1*1) = 100 * 0.6 = 60.0
        assert score == 60.0

    def test_invalid_output_does_not_receive_consistency_component(self):
        score = compute_reliability_score(
            quality_score=0.0,
            consistency_score=0.9,
            schema_valid=False,
            run_status=RunStatus.COMPLETED,
        )
        # schema invalid -> consistency_component=0, schema_component=0;
        # run itself still completed -> provider_component=1.
        # 100 * (0 + 0 + 0 + 0.1) = 10.0
        assert score == 10.0

    def test_provider_failure_receives_no_provider_component(self):
        score = compute_reliability_score(
            quality_score=0.0,
            consistency_score=0.0,
            schema_valid=False,
            run_status=RunStatus.FAILED,
        )
        assert score == 0.0

    def test_score_is_clamped_to_0_100(self):
        score = compute_reliability_score(
            quality_score=1.0,
            consistency_score=1.0,
            schema_valid=True,
            run_status=RunStatus.COMPLETED,
        )
        assert 0.0 <= score <= 100.0

    def test_rounds_to_two_decimal_places(self):
        score = compute_reliability_score(
            quality_score=1.0,
            consistency_score=1 / 3,
            schema_valid=True,
            run_status=RunStatus.COMPLETED,
        )
        # 100 * (0.6 + 0.2*(1/3) + 0.1 + 0.1) = 100 * 0.86666... = 86.67
        assert score == 86.67

    def test_uses_decimal_for_intermediate_arithmetic(self):
        # 0.1 and 0.2 are not exactly representable in binary float; if the
        # formula used raw float math this could drift off 30.0.
        score = compute_reliability_score(
            quality_score=0.1,
            consistency_score=0.2,
            schema_valid=True,
            run_status=RunStatus.COMPLETED,
        )
        assert score == 30.0
