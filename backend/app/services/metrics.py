from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.evaluation.metrics import compute_variant_metrics
from app.evaluation.recommendation import build_recommendation
from app.models.enums import ExperimentStatus
from app.models.experiment import Experiment
from app.schemas.metrics import ExperimentMetricsResponse


def get_experiment_metrics(db: Session, experiment_id: int) -> ExperimentMetricsResponse:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")
    if experiment.status != ExperimentStatus.COMPLETED:
        raise ConflictError(
            f"Experiment {experiment_id} has not completed execution "
            f"(status='{experiment.status.value}')"
        )

    variant_metrics = compute_variant_metrics(db, experiment)
    recommendation = build_recommendation(variant_metrics)
    total_runs = sum(variant.total_runs for variant in variant_metrics)

    return ExperimentMetricsResponse(
        experiment_id=experiment.id,
        experiment_name=experiment.name,
        status=experiment.status,
        total_runs=total_runs,
        variant_metrics=variant_metrics,
        recommendation=recommendation,
    )
