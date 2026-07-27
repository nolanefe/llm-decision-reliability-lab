"""Tests for app.evaluation.metrics.compute_variant_metrics: aggregation
across dataset items/repetitions, rate/accuracy denominators, token and
cost totals, latency averaging, variant isolation, and deterministic
ordering."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.evaluation.metrics import compute_variant_metrics
from app.evaluation.scorer import score_experiment
from app.models.enums import FailureCategory, RunStatus
from tests.factories import make_dataset_item, make_evaluation, make_experiment, make_prompt_version, make_run


class TestAggregationAccuracyAndTotals:
    """One experiment with two variants (p1, p2) sharing the same two
    dataset items. p1 has 4 runs (2 items x 2 reps, one schema-invalid,
    one provider failure); p2 has 2 runs (1 per item). Real scoring runs
    first so quality/consistency/reliability reflect the actual formulas,
    then metrics aggregation is checked against hand-computed numbers.
    """

    def _build_experiment(self, db: Session):
        item_a = make_dataset_item(
            db, name="a", expected_category="billing", expected_priority="high"
        )
        item_b = make_dataset_item(
            db, name="b", expected_category="bug", expected_priority="low"
        )
        p1 = make_prompt_version(db, name="p1", version=1)
        p2 = make_prompt_version(db, name="p2", version=2)
        experiment = make_experiment(
            db,
            dataset_item_ids=[item_a.id, item_b.id],
            prompt_version_ids=[p1.id, p2.id],
            model_names=["gpt-5-mini"],
            repeat_count=2,
        )

        # --- variant (p1, gpt-5-mini): 4 runs ---
        run1 = make_run(
            db,
            experiment=experiment,
            dataset_item=item_a,
            prompt_version=p1,
            repetition_index=1,
            parsed_output={"category": "billing", "priority": "high"},
            latency_ms=100,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            estimated_cost_usd=0.0001,
        )
        make_evaluation(
            db, run=run1, schema_valid=True, category_correct=True, priority_correct=True
        )
        run2 = make_run(
            db,
            experiment=experiment,
            dataset_item=item_a,
            prompt_version=p1,
            repetition_index=2,
            raw_response="not json",
            latency_ms=150,
            prompt_tokens=10,
            completion_tokens=15,
            total_tokens=25,
            estimated_cost_usd=0.00007,
        )
        make_evaluation(
            db, run=run2, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )
        run3 = make_run(
            db,
            experiment=experiment,
            dataset_item=item_b,
            prompt_version=p1,
            repetition_index=1,
            parsed_output={"category": "bug", "priority": "high"},
            latency_ms=120,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            estimated_cost_usd=0.0001,
        )
        make_evaluation(
            db,
            run=run3,
            schema_valid=True,
            category_correct=True,
            priority_correct=False,
            failure_category=FailureCategory.CONTENT_MISMATCH,
        )
        run4 = make_run(
            db,
            experiment=experiment,
            dataset_item=item_b,
            prompt_version=p1,
            repetition_index=2,
            status=RunStatus.FAILED,
            latency_ms=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            estimated_cost_usd=None,
            error_message="boom",
        )
        make_evaluation(
            db, run=run4, schema_valid=False, failure_category=FailureCategory.PROVIDER_ERROR
        )

        # --- variant (p2, gpt-5-mini): 2 runs ---
        run5 = make_run(
            db,
            experiment=experiment,
            dataset_item=item_a,
            prompt_version=p2,
            repetition_index=1,
            parsed_output={"category": "billing", "priority": "high"},
            latency_ms=200,
            prompt_tokens=5,
            completion_tokens=5,
            total_tokens=10,
            estimated_cost_usd=0.00002,
        )
        make_evaluation(
            db, run=run5, schema_valid=True, category_correct=True, priority_correct=True
        )
        run6 = make_run(
            db,
            experiment=experiment,
            dataset_item=item_b,
            prompt_version=p2,
            repetition_index=1,
            raw_response="not json",
            latency_ms=210,
            prompt_tokens=5,
            completion_tokens=5,
            total_tokens=10,
            estimated_cost_usd=0.00002,
        )
        make_evaluation(
            db, run=run6, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )

        score_experiment(db, experiment.id)
        return experiment

    def test_aggregation_across_dataset_items_and_repetitions(
        self, db_session: Session
    ) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        assert p1_metrics.total_runs == 4
        assert p1_metrics.completed_runs == 3
        assert p1_metrics.failed_runs == 1

    def test_schema_validity_rate_uses_total_runs_denominator(
        self, db_session: Session
    ) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        assert p1_metrics.schema_valid_runs == 2
        assert p1_metrics.schema_validity_rate == 0.5

    def test_category_and_priority_accuracy_use_schema_valid_denominator(
        self, db_session: Session
    ) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        # schema_valid_runs=2 (run1, run3); both category-correct, only
        # run1 priority-correct.
        assert p1_metrics.category_accuracy == 1.0
        assert p1_metrics.priority_accuracy == 0.5

    def test_token_totals_exclude_null_contributions(self, db_session: Session) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        assert p1_metrics.total_prompt_tokens == 30
        assert p1_metrics.total_completion_tokens == 55
        assert p1_metrics.total_tokens == 85

    def test_cost_totals_use_decimal(self, db_session: Session) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        assert isinstance(p1_metrics.total_estimated_cost_usd, Decimal)
        assert p1_metrics.total_estimated_cost_usd == Decimal("0.0001") + Decimal(
            "0.00007"
        ) + Decimal("0.0001")

    def test_latency_averages_only_runs_with_latency_values(
        self, db_session: Session
    ) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        # run4 (provider failure) has no latency and must not count toward
        # the denominator.
        assert p1_metrics.average_latency_ms == (100 + 150 + 120) / 3

    def test_failure_count_counts_every_categorized_failure(
        self, db_session: Session
    ) -> None:
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")

        # run2 (invalid_json), run3 (content_mismatch), run4 (provider_error)
        assert p1_metrics.failure_count == 3

    def test_variant_isolation(self, db_session: Session) -> None:
        """p1 and p2 share both dataset items; their aggregates must not
        cross-contaminate."""
        experiment = self._build_experiment(db_session)

        metrics = compute_variant_metrics(db_session, experiment)
        p1_metrics = next(m for m in metrics if m.prompt_version_name == "p1")
        p2_metrics = next(m for m in metrics if m.prompt_version_name == "p2")

        assert p1_metrics.total_runs == 4
        assert p2_metrics.total_runs == 2
        assert p1_metrics.total_estimated_cost_usd != p2_metrics.total_estimated_cost_usd
        assert p2_metrics.total_estimated_cost_usd == Decimal("0.00002") + Decimal("0.00002")
        assert p2_metrics.schema_valid_runs == 1
        assert p2_metrics.category_accuracy == 1.0
        assert p2_metrics.priority_accuracy == 1.0


class TestNullAccuracyWhenNoValidOutputsExist:
    def test_accuracy_is_null_when_zero_schema_valid_runs(self, db_session: Session) -> None:
        item = make_dataset_item(db_session)
        prompt = make_prompt_version(db_session)
        experiment = make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[prompt.id],
            model_names=["gpt-5-mini"],
            repeat_count=2,
        )
        run1 = make_run(
            db_session,
            experiment=experiment,
            dataset_item=item,
            prompt_version=prompt,
            repetition_index=1,
            raw_response="not json",
        )
        make_evaluation(
            db_session, run=run1, schema_valid=False, failure_category=FailureCategory.INVALID_JSON
        )
        run2 = make_run(
            db_session,
            experiment=experiment,
            dataset_item=item,
            prompt_version=prompt,
            repetition_index=2,
            status=RunStatus.FAILED,
            latency_ms=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            estimated_cost_usd=None,
        )
        make_evaluation(
            db_session, run=run2, schema_valid=False, failure_category=FailureCategory.PROVIDER_ERROR
        )
        score_experiment(db_session, experiment.id)

        metrics = compute_variant_metrics(db_session, experiment)

        assert len(metrics) == 1
        assert metrics[0].schema_valid_runs == 0
        assert metrics[0].schema_validity_rate == 0.0
        assert metrics[0].category_accuracy is None
        assert metrics[0].priority_accuracy is None


class TestDeterministicSorting:
    def test_full_tie_break_cascade(self, db_session: Session) -> None:
        item = make_dataset_item(db_session)

        # Created in this order so "pW1" gets the lower prompt_version_id
        # than "pW2" -- both otherwise tied on reliability/cost/latency.
        p_z = make_prompt_version(db_session, name="pZ", version=1)
        p_y = make_prompt_version(db_session, name="pY", version=1)
        p_x = make_prompt_version(db_session, name="pX", version=1)
        p_w1 = make_prompt_version(db_session, name="pW1", version=1)
        p_w2 = make_prompt_version(db_session, name="pW2", version=1)
        p_shared = make_prompt_version(db_session, name="pShared", version=1)

        experiment = make_experiment(
            db_session,
            dataset_item_ids=[item.id],
            prompt_version_ids=[p.id for p in (p_z, p_y, p_x, p_w1, p_w2, p_shared)],
            model_names=["gpt-5-mini", "gpt-5-nano"],
        )

        def _variant(
            *, prompt, model: str, reliability: float, cost: float, latency: float
        ) -> None:
            run = make_run(
                db_session,
                experiment=experiment,
                dataset_item=item,
                prompt_version=prompt,
                model_name=model,
                latency_ms=latency,
                estimated_cost_usd=cost,
                parsed_output={"category": "billing", "priority": "high"},
            )
            make_evaluation(
                db_session,
                run=run,
                schema_valid=True,
                category_correct=True,
                priority_correct=True,
                quality_score=1.0,
                consistency_score=1.0,
                reliability_score=reliability,
            )

        _variant(prompt=p_z, model="gpt-5-mini", reliability=95.0, cost=100.0, latency=999)
        _variant(prompt=p_y, model="gpt-5-mini", reliability=90.0, cost=2.0, latency=100)
        _variant(prompt=p_x, model="gpt-5-mini", reliability=90.0, cost=5.0, latency=100)
        _variant(prompt=p_w1, model="gpt-5-mini", reliability=85.0, cost=1.0, latency=50)
        _variant(prompt=p_w2, model="gpt-5-mini", reliability=85.0, cost=1.0, latency=50)
        _variant(prompt=p_shared, model="gpt-5-mini", reliability=80.0, cost=3.0, latency=40)
        _variant(prompt=p_shared, model="gpt-5-nano", reliability=80.0, cost=3.0, latency=40)

        metrics = compute_variant_metrics(db_session, experiment)

        assert [m.prompt_version_name for m in metrics] == [
            "pZ",  # highest reliability wins outright
            "pY",  # tied at 90 with pX, lower cost wins
            "pX",
            "pW1",  # tied at 85/cost 1.0/latency 50 with pW2, lower prompt_version_id wins
            "pW2",
            "pShared",  # gpt-5-mini row: tied with the nano row on everything but model_name
            "pShared",  # gpt-5-nano row
        ]
        assert [m.model_name for m in metrics[-2:]] == ["gpt-5-mini", "gpt-5-nano"]
