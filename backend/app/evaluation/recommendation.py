"""Deterministic experiment recommendation.

Selects one variant from a completed experiment's ``VariantMetrics`` using
a fixed, documented tie-break cascade -- never an LLM:

    1. highest average_reliability_score
    2. among variants within 0.50 points of the top score, lower
       total_estimated_cost_usd
    3. if still tied, lower average_latency_ms
    4. if still tied, deterministic (prompt_version_id, model_name) ordering

The "within 0.50 points" comparison is always relative to the single
highest average_reliability_score across all variants, not a pairwise
comparison -- so every variant within 0.50 of the top score competes on
cost, even if it isn't the top scorer itself. The generated reason string
is built from fixed templates describing which rule decided the outcome;
it never claims the recommendation proves production suitability.
"""

from decimal import Decimal

from app.schemas.metrics import RecommendationRead, VariantMetrics

_TIE_THRESHOLD = Decimal("0.50")


def build_recommendation(
    variant_metrics: list[VariantMetrics],
) -> RecommendationRead | None:
    scored = [v for v in variant_metrics if v.average_reliability_score is not None]
    if not scored:
        return None

    top_score = max(v.average_reliability_score for v in scored)
    candidates = [
        v
        for v in scored
        if Decimal(str(top_score)) - Decimal(str(v.average_reliability_score))
        <= _TIE_THRESHOLD
    ]
    candidates.sort(
        key=lambda v: (
            v.total_estimated_cost_usd,
            v.average_latency_ms if v.average_latency_ms is not None else float("inf"),
            v.prompt_version_id,
            v.model_name,
        )
    )

    winner = candidates[0]
    reason = _build_reason(
        winner=winner,
        candidates=candidates,
        total_variants=len(variant_metrics),
        top_score=top_score,
    )

    return RecommendationRead(
        recommended_prompt_version_id=winner.prompt_version_id,
        recommended_model_name=winner.model_name,
        reason=reason,
        reliability_score=winner.average_reliability_score,
        estimated_cost_usd=winner.total_estimated_cost_usd,
        average_latency_ms=winner.average_latency_ms,
    )


def _deciding_factor(candidates: list[VariantMetrics]) -> str:
    """Which rule actually discriminated the winner from its closest
    competitor. Sound for stable multi-key sorts: the runner-up already
    reflects the next active discriminator once earlier keys tie."""
    if len(candidates) < 2:
        return "sole"
    winner, runner_up = candidates[0], candidates[1]
    if winner.total_estimated_cost_usd != runner_up.total_estimated_cost_usd:
        return "cost"
    if winner.average_latency_ms != runner_up.average_latency_ms:
        return "latency"
    return "order"


def _build_reason(
    *,
    winner: VariantMetrics,
    candidates: list[VariantMetrics],
    total_variants: int,
    top_score: float,
) -> str:
    is_top_score = winner.average_reliability_score == top_score
    factor = _deciding_factor(candidates)

    if is_top_score:
        reliability_clause = (
            f"the highest average reliability score ({winner.average_reliability_score:.2f}) "
            f"among {total_variants} tested variant(s)"
        )
    else:
        reliability_clause = (
            f"an average reliability score ({winner.average_reliability_score:.2f}) within "
            f"0.50 points of the top score ({top_score:.2f})"
        )

    if factor == "sole":
        return f"Selected for {reliability_clause}."

    if factor == "cost":
        return (
            f"Selected for {reliability_clause}, with the lowest estimated cost "
            f"(${winner.total_estimated_cost_usd:.6f}) among variants in that range."
        )

    if factor == "latency":
        latency = winner.average_latency_ms
        latency_text = f"{latency:.1f} ms" if latency is not None else "no recorded latency"
        return (
            f"Selected for {reliability_clause}; estimated cost was tied with the next "
            f"best variant, so the lower average latency ({latency_text}) was the "
            f"deciding factor."
        )

    return (
        f"Selected for {reliability_clause}; estimated cost and average latency were "
        f"both tied, so deterministic prompt-version/model ordering was the deciding "
        f"factor."
    )
