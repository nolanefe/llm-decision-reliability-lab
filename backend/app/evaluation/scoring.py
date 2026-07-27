"""Centralized, deterministic scoring formulas for the reliability lab.

This module is the single source of truth for how a Run/Evaluation's
quality, consistency, and reliability scores are computed. No other module
may re-derive or hard-code these weights.

Every score is computed only from data already produced by the experiment
executor (schema validity, category/priority correctness, the run's
terminal status, and the modal outcome within a repetition group) -- never
by asking another model to judge the output. This keeps scoring
deterministic, reproducible, and fully explainable from persisted data.

--------------------------------------------------------------------------
Quality score (per run, 0.0-1.0)
--------------------------------------------------------------------------
    schema-invalid output           -> 0.0
    schema-valid, both labels wrong -> 0.0
    schema-valid, one label right   -> 0.5
    schema-valid, both labels right -> 1.0

A Run whose provider call failed always carries schema_valid=False (see
``executor._fail_run``), so provider failures are already covered by the
"schema-invalid" case above.

--------------------------------------------------------------------------
Consistency score (per group, 0.0-1.0)
--------------------------------------------------------------------------
A group is every Run sharing (dataset_item_id, prompt_version_id,
model_name) within one experiment -- i.e. all repetitions of the same
input/prompt/model combination.

    consistency_score = (count of the group's most common schema-valid
                          (category, priority) outcome)
                         / (total planned Runs in the group)

Invalid JSON, schema errors, and provider failures stay in the
denominator (they count against consistency) but never in the numerator.
If a group has zero schema-valid Runs, consistency_score = 0.0. The same
value is assigned to every Evaluation in the group, including invalid
ones -- the reliability formula below is what excludes it for those.

--------------------------------------------------------------------------
Reliability score (per run, 0.0-100.0)
--------------------------------------------------------------------------
    quality_component     = quality_score
    consistency_component = consistency_score if schema_valid else 0.0
    schema_component      = 1.0 if schema_valid else 0.0
    provider_component    = 1.0 if Run.status == completed else 0.0

    reliability_score = 100 * (
          0.60 * quality_component
        + 0.20 * consistency_component
        + 0.10 * schema_component
        + 0.10 * provider_component
    )

Clamped to [0.0, 100.0] and rounded to two decimal places. Latency and
estimated cost are never inputs to this formula -- they measure
efficiency, not dependability, and are reported alongside it instead.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import RunStatus

QUALITY_WEIGHT = Decimal("0.60")
CONSISTENCY_WEIGHT = Decimal("0.20")
SCHEMA_WEIGHT = Decimal("0.10")
PROVIDER_WEIGHT = Decimal("0.10")

_TWO_PLACES = Decimal("0.01")
_FOUR_PLACES = Decimal("0.0001")


def compute_quality_score(
    *, schema_valid: bool, category_correct: bool | None, priority_correct: bool | None
) -> float:
    """0.0 for schema-invalid output; otherwise 0.5 per correct label."""
    if not schema_valid:
        return 0.0
    score = Decimal("0")
    if category_correct:
        score += Decimal("0.5")
    if priority_correct:
        score += Decimal("0.5")
    return float(score)


def compute_group_consistency_score(
    *, valid_outcomes: list[tuple[str, str]], total_planned_runs: int
) -> float:
    """Fraction of ``total_planned_runs`` sharing the group's most common
    schema-valid (category, priority) outcome. Ties in outcome frequency
    never affect the score, since the score depends only on the winning
    count -- not on which outcome achieved it."""
    if total_planned_runs <= 0 or not valid_outcomes:
        return 0.0

    counts: dict[tuple[str, str], int] = {}
    for outcome in valid_outcomes:
        counts[outcome] = counts.get(outcome, 0) + 1

    # Deterministic selection even though only the winning count is scored:
    # break count ties by outcome value so the "most common outcome" is
    # reproducible if ever surfaced elsewhere.
    top_count = max(counts.values())

    ratio = Decimal(top_count) / Decimal(total_planned_runs)
    return float(ratio.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP))


def compute_reliability_score(
    *,
    quality_score: float,
    consistency_score: float,
    schema_valid: bool,
    run_status: RunStatus,
) -> float:
    """The single centralized reliability formula. See module docstring."""
    quality_component = Decimal(str(quality_score))
    consistency_component = (
        Decimal(str(consistency_score)) if schema_valid else Decimal("0")
    )
    schema_component = Decimal("1") if schema_valid else Decimal("0")
    provider_component = (
        Decimal("1") if run_status == RunStatus.COMPLETED else Decimal("0")
    )

    raw_score = Decimal(100) * (
        QUALITY_WEIGHT * quality_component
        + CONSISTENCY_WEIGHT * consistency_component
        + SCHEMA_WEIGHT * schema_component
        + PROVIDER_WEIGHT * provider_component
    )
    clamped = max(Decimal("0"), min(Decimal("100"), raw_score))
    return float(clamped.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))
