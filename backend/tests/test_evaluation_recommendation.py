"""Tests for app.evaluation.recommendation.build_recommendation: the
deterministic tie-break cascade (reliability -> cost -> latency -> id
ordering) and the accuracy of the generated reason text. Builds
VariantMetrics directly rather than through the DB, since recommendation
logic is a pure function of already-aggregated metrics."""

from decimal import Decimal

from app.evaluation.recommendation import build_recommendation
from app.schemas.metrics import VariantMetrics


def _variant(
    *,
    prompt_version_id: int,
    model_name: str = "gpt-5-mini",
    reliability: float,
    cost: str,
    latency: float | None = 100.0,
    prompt_version_name: str | None = None,
) -> VariantMetrics:
    return VariantMetrics(
        prompt_version_id=prompt_version_id,
        prompt_version_name=prompt_version_name or f"prompt-{prompt_version_id}",
        prompt_version_version=1,
        model_name=model_name,
        total_runs=1,
        completed_runs=1,
        failed_runs=0,
        schema_valid_runs=1,
        schema_validity_rate=1.0,
        category_accuracy=1.0,
        priority_accuracy=1.0,
        average_quality_score=1.0,
        average_consistency_score=1.0,
        average_reliability_score=reliability,
        average_latency_ms=latency,
        total_prompt_tokens=10,
        total_completion_tokens=10,
        total_tokens=20,
        total_estimated_cost_usd=Decimal(cost),
        failure_count=0,
    )


class TestHighestReliabilityWins:
    def test_clear_winner_by_reliability_alone(self) -> None:
        variants = [
            _variant(prompt_version_id=1, reliability=70.0, cost="1.00"),
            _variant(prompt_version_id=2, reliability=95.0, cost="10.00"),
        ]

        recommendation = build_recommendation(variants)

        assert recommendation is not None
        assert recommendation.recommended_prompt_version_id == 2
        assert "highest average reliability score" in recommendation.reason
        assert "production" not in recommendation.reason.lower()

    def test_no_variants_returns_none(self) -> None:
        assert build_recommendation([]) is None


class TestCostTieBreak:
    def test_within_half_point_prefers_lower_cost(self) -> None:
        variants = [
            _variant(prompt_version_id=1, reliability=90.0, cost="5.00"),
            _variant(prompt_version_id=2, reliability=90.3, cost="1.00"),
        ]

        recommendation = build_recommendation(variants)

        assert recommendation.recommended_prompt_version_id == 2
        assert recommendation.estimated_cost_usd == Decimal("1.00")
        assert "lowest estimated cost" in recommendation.reason

    def test_outside_half_point_the_top_scorer_wins_despite_higher_cost(self) -> None:
        variants = [
            _variant(prompt_version_id=1, reliability=90.0, cost="50.00"),
            _variant(prompt_version_id=2, reliability=89.4, cost="1.00"),
        ]

        recommendation = build_recommendation(variants)

        # 90.0 - 89.4 = 0.6 > 0.50, so variant 2 is not in the tie band.
        assert recommendation.recommended_prompt_version_id == 1
        assert recommendation.reliability_score == 90.0


class TestLatencyTieBreak:
    def test_latency_breaks_a_cost_tie(self) -> None:
        variants = [
            _variant(prompt_version_id=1, reliability=90.0, cost="2.00", latency=300.0),
            _variant(prompt_version_id=2, reliability=90.0, cost="2.00", latency=100.0),
        ]

        recommendation = build_recommendation(variants)

        assert recommendation.recommended_prompt_version_id == 2
        assert recommendation.average_latency_ms == 100.0
        assert "latency" in recommendation.reason.lower()


class TestDeterministicFinalTieBreak:
    def test_prompt_version_id_and_model_name_break_remaining_ties(self) -> None:
        variants = [
            _variant(
                prompt_version_id=5, model_name="gpt-5-nano", reliability=90.0, cost="2.00", latency=100.0
            ),
            _variant(
                prompt_version_id=3, model_name="gpt-5-mini", reliability=90.0, cost="2.00", latency=100.0
            ),
        ]

        recommendation = build_recommendation(variants)

        assert recommendation.recommended_prompt_version_id == 3
        assert recommendation.recommended_model_name == "gpt-5-mini"
        assert "deterministic" in recommendation.reason.lower()


class TestNoProductionClaims:
    def test_reason_never_claims_production_suitability(self) -> None:
        variants = [
            _variant(prompt_version_id=1, reliability=70.0, cost="1.00"),
            _variant(prompt_version_id=2, reliability=95.0, cost="10.00"),
        ]

        recommendation = build_recommendation(variants)

        forbidden = ["production-ready", "production ready", "safe to ship", "guarantee"]
        assert not any(phrase in recommendation.reason.lower() for phrase in forbidden)


class TestReasonAccuracy:
    def test_reason_cites_the_actual_reliability_score(self) -> None:
        variants = [
            _variant(prompt_version_id=1, reliability=70.0, cost="1.00"),
            _variant(prompt_version_id=2, reliability=95.0, cost="10.00"),
        ]

        recommendation = build_recommendation(variants)

        assert "95.00" in recommendation.reason

    def test_variants_with_no_reliability_score_are_ignored(self) -> None:
        variants = [
            VariantMetrics(
                prompt_version_id=1,
                prompt_version_name="no-runs",
                prompt_version_version=1,
                model_name="gpt-5-mini",
                total_runs=0,
                completed_runs=0,
                failed_runs=0,
                schema_valid_runs=0,
                schema_validity_rate=0.0,
                category_accuracy=None,
                priority_accuracy=None,
                average_quality_score=None,
                average_consistency_score=None,
                average_reliability_score=None,
                average_latency_ms=None,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_tokens=0,
                total_estimated_cost_usd=Decimal("0"),
                failure_count=0,
            ),
            _variant(prompt_version_id=2, reliability=80.0, cost="1.00"),
        ]

        recommendation = build_recommendation(variants)

        assert recommendation.recommended_prompt_version_id == 2
