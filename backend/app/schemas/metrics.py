from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ExperimentStatus


class VariantMetrics(BaseModel):
    """Aggregated comparison metrics for one (prompt_version_id, model_name)
    variant across all selected dataset items and repetitions in an
    experiment."""

    prompt_version_id: int
    prompt_version_name: str
    prompt_version_version: int
    model_name: str
    total_runs: int
    completed_runs: int
    failed_runs: int
    schema_valid_runs: int
    schema_validity_rate: float
    category_accuracy: float | None
    priority_accuracy: float | None
    average_quality_score: float | None
    average_consistency_score: float | None
    average_reliability_score: float | None
    average_latency_ms: float | None
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: Decimal
    failure_count: int


class RecommendationRead(BaseModel):
    """A single deterministic variant recommendation for a completed
    experiment. Does not claim production suitability -- only that this
    variant scored best on the criteria below."""

    recommended_prompt_version_id: int
    recommended_model_name: str
    reason: str
    reliability_score: float
    estimated_cost_usd: Decimal
    average_latency_ms: float | None


class ExperimentMetricsResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    status: ExperimentStatus
    total_runs: int
    variant_metrics: list[VariantMetrics]
    recommendation: RecommendationRead | None
