"""Sanitized benchmark evidence export.

Writes portfolio-safe artifacts under ``benchmarks/results/<benchmark-id>/``.
Raw experiment databases and provider dumps are never exported.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.benchmarks.plan import BenchmarkPlan
from app.benchmarks.validation import validate_benchmark_id
from app.evaluation.metrics import compute_variant_metrics
from app.evaluation.recommendation import build_recommendation
from app.llm.pricing import (
    PRICING_SNAPSHOT_DATE,
    PRICING_SNAPSHOT_SOURCE,
    PRICING_USD_PER_MILLION_TOKENS,
)
from app.models.enums import ExperimentStatus
from app.models.experiment import Experiment
from app.schemas.metrics import VariantMetrics
from app.services.failures import get_experiment_failures

BENCHMARK_OPENAI_MAX_RETRIES = 0

_SECRET_LIKE_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{6,}")
_ABSOLUTE_PATH_PATTERN = re.compile(r"/(?:[\w.-]+/)+[\w.-]+")


def repo_root() -> Path:
    """Repository root (parent of ``backend/``)."""
    return Path(__file__).resolve().parents[3]


def benchmark_results_dir(benchmark_id: str, *, root: Path | None = None) -> Path:
    safe_id = validate_benchmark_id(benchmark_id)
    base = root or repo_root()
    return base / "benchmarks" / "results" / safe_id


def export_benchmark_evidence(
    db: Session,
    *,
    experiment: Experiment,
    plan: BenchmarkPlan,
    benchmark_id: str,
    output_root: Path | None = None,
) -> Path:
    """Export sanitized evidence for a completed experiment.

    Raises ``ValueError`` if the experiment is not completed or if the
    destination directory already exists (to avoid overwriting tracked
    evidence accidentally).
    """
    safe_benchmark_id = validate_benchmark_id(benchmark_id)
    if experiment.status != ExperimentStatus.COMPLETED:
        raise ValueError(
            f"Experiment {experiment.id} is not completed "
            f"(status={experiment.status.value})."
        )

    out_dir = benchmark_results_dir(safe_benchmark_id, root=output_root)
    if out_dir.exists():
        raise FileExistsError(
            f"Benchmark results directory already exists: {out_dir}. "
            "Remove it or choose a different benchmark id before exporting."
        )

    variant_metrics = compute_variant_metrics(db, experiment)
    recommendation = build_recommendation(variant_metrics)
    failures = get_experiment_failures(db, experiment.id)

    completed_at = experiment.completed_at or datetime.now(timezone.utc)
    summary = _build_summary(
        experiment=experiment,
        plan=plan,
        benchmark_id=safe_benchmark_id,
        completed_at=completed_at,
        variant_metrics=variant_metrics,
        recommendation=recommendation,
        failures=failures,
    )
    methodology = _build_methodology(plan=plan, benchmark_id=safe_benchmark_id)

    parent = out_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{safe_benchmark_id}-", dir=parent)
    )
    try:
        _write_json(temp_dir / "summary.json", summary)
        _write_json(temp_dir / "methodology.json", methodology)
        _write_results_csv(temp_dir / "results.csv", variant_metrics)
        _write_readme(temp_dir / "README.md", summary, plan)
        temp_dir.rename(out_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return out_dir


def _build_summary(
    *,
    experiment: Experiment,
    plan: BenchmarkPlan,
    benchmark_id: str,
    completed_at: datetime,
    variant_metrics: list[VariantMetrics],
    recommendation,
    failures,
) -> dict:
    total_runs = sum(v.total_runs for v in variant_metrics)
    completed_runs = sum(v.completed_runs for v in variant_metrics)
    failed_runs = sum(v.failed_runs for v in variant_metrics)
    schema_valid_outputs = sum(v.schema_valid_runs for v in variant_metrics)
    schema_validation_failures = total_runs - schema_valid_outputs
    failure_categories = Counter(
        entry.failure_category.value for entry in failures if entry.failure_category
    )

    recommended_prompt_version_name = None
    if recommendation is not None:
        for variant in variant_metrics:
            if variant.prompt_version_id == recommendation.recommended_prompt_version_id:
                recommended_prompt_version_name = variant.prompt_version_name
                break

    return _sanitize_dict(
        {
            "benchmark_id": benchmark_id,
            "experiment_id": experiment.id,
            "experiment_name": experiment.name,
            "executed_at": completed_at.isoformat(),
            "dataset_version": plan.dataset_version,
            "dataset_item_count": len(plan.dataset_item_names),
            "dataset_item_names": list(plan.dataset_item_names),
            "prompt_variant_names": list(plan.prompt_version_names),
            "models": list(plan.model_names),
            "repeat_count": plan.repeat_count,
            "planned_runs": plan.planned_run_count,
            "logical_provider_invocations": plan.planned_run_count,
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "execution_outcomes": {
                "provider_executions_completed": completed_runs,
                "provider_infrastructure_failures": failed_runs,
                "schema_valid_outputs": schema_valid_outputs,
                "schema_validation_failures": schema_validation_failures,
            },
            "variant_metrics": [_variant_to_dict(v) for v in variant_metrics],
            "recommendation": (
                {
                    "recommended_prompt_version_id": recommendation.recommended_prompt_version_id,
                    "recommended_prompt_version_name": recommended_prompt_version_name,
                    "recommended_model_name": recommendation.recommended_model_name,
                    "reason": recommendation.reason,
                    "reliability_score": recommendation.reliability_score,
                    "estimated_cost_usd": str(recommendation.estimated_cost_usd),
                    "average_latency_ms": recommendation.average_latency_ms,
                }
                if recommendation is not None
                else None
            ),
            "failure_category_counts": dict(sorted(failure_categories.items())),
            "limitations": [
                "Exploratory benchmark with a limited sample size (4 dataset items, "
                "2 prompt variants, 1 model, 2 repetitions).",
                "Results describe this controlled setup only; they do not prove "
                "universal prompt or model superiority.",
                "Estimated cost uses the dated pricing snapshot in methodology.json "
                "applied to observed input/output token counts only; actual billed "
                "cost can differ and cached-input discounts are not modeled.",
                "Category and priority accuracy are calculated over schema-valid "
                "runs only; use schema_validity_rate and reliability_score to "
                "account for failures and invalid outputs.",
                "Not statistically significant for production reliability claims.",
            ],
        }
    )


def _variant_to_dict(metrics: VariantMetrics) -> dict:
    return {
        "prompt_version_id": metrics.prompt_version_id,
        "prompt_version_name": metrics.prompt_version_name,
        "prompt_version_version": metrics.prompt_version_version,
        "model_name": metrics.model_name,
        "total_runs": metrics.total_runs,
        "completed_runs": metrics.completed_runs,
        "failed_runs": metrics.failed_runs,
        "schema_valid_runs": metrics.schema_valid_runs,
        "schema_validity_rate": metrics.schema_validity_rate,
        "category_accuracy": metrics.category_accuracy,
        "priority_accuracy": metrics.priority_accuracy,
        "average_quality_score": metrics.average_quality_score,
        "average_consistency_score": metrics.average_consistency_score,
        "average_reliability_score": metrics.average_reliability_score,
        "average_latency_ms": metrics.average_latency_ms,
        "total_prompt_tokens": metrics.total_prompt_tokens,
        "total_completion_tokens": metrics.total_completion_tokens,
        "total_tokens": metrics.total_tokens,
        "total_estimated_cost_usd": str(metrics.total_estimated_cost_usd),
        "failure_count": metrics.failure_count,
    }


def _build_methodology(*, plan: BenchmarkPlan, benchmark_id: str) -> dict:
    model_pricing = {
        model: {
            "input_usd_per_million_tokens": str(cfg.input_usd_per_million_tokens),
            "output_usd_per_million_tokens": str(cfg.output_usd_per_million_tokens),
        }
        for model, cfg in PRICING_USD_PER_MILLION_TOKENS.items()
        if model in plan.model_names
    }

    return {
        "benchmark_id": benchmark_id,
        "purpose": (
            "Exploratory, reproducible portfolio evidence for the LLM Decision "
            "Reliability Lab using a fixed subset of the built-in evaluation dataset."
        ),
        "dataset": {
            "source": "backend/app/db/seed_data.py",
            "version": plan.dataset_version,
            "item_names": list(plan.dataset_item_names),
        },
        "prompt_variants": [
            {"name": name, "version": 1, "source": "backend/app/db/seed_data.py"}
            for name in plan.prompt_version_names
        ],
        "models": list(plan.model_names),
        "repeat_count": plan.repeat_count,
        "planned_runs": plan.planned_run_count,
        "provider_invocations": {
            "logical_count": plan.planned_run_count,
            "description": (
                "One provider.generate() invocation per planned run in the executor."
            ),
            "openai_sdk_max_retries": BENCHMARK_OPENAI_MAX_RETRIES,
            "openai_response_store": False,
            "http_attempts_note": (
                "The benchmark live path configures the OpenAI SDK with "
                "max_retries=0, so each logical invocation corresponds to one "
                "HTTP attempt under normal SDK behavior. The normal application "
                "execution path retains the SDK default retry behavior."
            ),
        },
        "scoring": {
            "reference": "docs/reliability-scoring.md",
            "quality": (
                "Exact comparison of model category and priority against fixed "
                "expected labels per dataset item."
            ),
            "consistency": (
                "Fraction of repetitions sharing the most common schema-valid "
                "(category, priority) outcome within each "
                "(dataset_item, prompt_version, model) group."
            ),
            "reliability": (
                "Weighted combination of quality (60%), consistency (20%), "
                "schema validity (10%), and provider completion (10%)."
            ),
            "recommendation": (
                "Deterministic tie-break cascade in app/evaluation/recommendation.py; "
                "not generated by an LLM."
            ),
            "accuracy_denominators": {
                "category_accuracy": "correct category labels / schema-valid runs only",
                "priority_accuracy": "correct priority labels / schema-valid runs only",
                "schema_validity_rate": "schema-valid runs / total attempted runs",
                "note": (
                    "Category and priority accuracy are calculated over schema-valid "
                    "runs only. Use schema_validity_rate and reliability_score to "
                    "account for failures and invalid outputs."
                ),
            },
        },
        "structured_output": {
            "schema": "SupportTriageOutput (category, priority, summary, recommended_action)",
            "validation": "Local JSON parse + Pydantic validation; model output is never trusted as-is.",
        },
        "failure_categories": {
            "invalid_json": "Response is not valid JSON.",
            "schema_error": "JSON parses but fails SupportTriageOutput validation.",
            "content_mismatch": "Schema-valid output with incorrect category and/or priority.",
            "provider_error": "OpenAI API error or missing usage data.",
            "timeout": "OpenAI request exceeded configured timeout.",
        },
        "latency_measurement": "Wall-clock time around provider.generate(), in milliseconds per run.",
        "token_and_cost_measurement": {
            "description": (
                "Observed input_tokens and output_tokens from OpenAI response usage "
                "fields when a provider call completes successfully. Reasoning-token "
                "or cached-input token breakouts are not captured separately."
            ),
            "cost_label": "ESTIMATED",
            "pricing_snapshot": {
                "snapshot_date": PRICING_SNAPSHOT_DATE,
                "source": PRICING_SNAPSHOT_SOURCE,
                "models": model_pricing,
                "limitations": [
                    "Pricing snapshot is not live; OpenAI rates change over time.",
                    "Actual billed cost can differ from estimates.",
                    "Cached-input discounts are not modeled.",
                ],
            },
        },
        "statistical_significance": (
            "Not claimed. Sample size is intentionally small for portfolio demonstration."
        ),
    }


def _write_results_csv(path: Path, variant_metrics: list[VariantMetrics]) -> None:
    fieldnames = [
        "prompt_version_name",
        "model_name",
        "total_runs",
        "completed_runs",
        "failed_runs",
        "schema_validity_rate",
        "category_accuracy",
        "priority_accuracy",
        "average_quality_score",
        "average_consistency_score",
        "average_reliability_score",
        "average_latency_ms",
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_tokens",
        "total_estimated_cost_usd",
        "failure_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for metrics in variant_metrics:
            writer.writerow(
                {
                    "prompt_version_name": metrics.prompt_version_name,
                    "model_name": metrics.model_name,
                    "total_runs": metrics.total_runs,
                    "completed_runs": metrics.completed_runs,
                    "failed_runs": metrics.failed_runs,
                    "schema_validity_rate": metrics.schema_validity_rate,
                    "category_accuracy": metrics.category_accuracy,
                    "priority_accuracy": metrics.priority_accuracy,
                    "average_quality_score": metrics.average_quality_score,
                    "average_consistency_score": metrics.average_consistency_score,
                    "average_reliability_score": metrics.average_reliability_score,
                    "average_latency_ms": metrics.average_latency_ms,
                    "total_prompt_tokens": metrics.total_prompt_tokens,
                    "total_completion_tokens": metrics.total_completion_tokens,
                    "total_tokens": metrics.total_tokens,
                    "total_estimated_cost_usd": str(metrics.total_estimated_cost_usd),
                    "failure_count": metrics.failure_count,
                }
            )


def _write_readme(path: Path, summary: dict, plan: BenchmarkPlan) -> None:
    lines = [
        f"# Benchmark evidence: {summary['benchmark_id']}",
        "",
        "Exploratory, limited-sample benchmark results for the LLM Decision "
        "Reliability Lab. These figures describe **this controlled setup only** "
        "and must not be read as universal model or prompt superiority claims.",
        "",
        "## Run summary",
        "",
        f"- **Executed at:** {summary['executed_at']}",
        f"- **Dataset version:** {plan.dataset_version} ({summary['dataset_item_count']} items)",
        f"- **Prompt variants:** {', '.join(plan.prompt_version_names)}",
        f"- **Model(s):** {', '.join(plan.model_names)}",
        f"- **Repetitions:** {plan.repeat_count}",
        f"- **Planned runs:** {summary['planned_runs']}",
        f"- **Logical provider invocations:** {summary['logical_provider_invocations']} "
        "(benchmark live path uses OpenAI SDK max_retries=0 → one HTTP attempt per invocation)",
    ]
    outcomes = summary.get("execution_outcomes", {})
    if outcomes:
        lines.extend(
            [
                f"- **Provider executions completed:** "
                f"{outcomes['provider_executions_completed']}/{summary['planned_runs']}",
                f"- **Provider/infrastructure failures:** "
                f"{outcomes['provider_infrastructure_failures']}",
                f"- **Schema-valid outputs:** "
                f"{outcomes['schema_valid_outputs']}/{summary['planned_runs']}",
                f"- **Schema-validation failures:** "
                f"{outcomes['schema_validation_failures']}",
            ]
        )
    else:
        lines.append(
            f"- **Completed / failed:** {summary['completed_runs']} / {summary['failed_runs']}"
        )
    lines.extend(
        [
        "",
        "**Accuracy note:** Category and priority accuracy in the table below are "
        "calculated over **schema-valid runs only**. Use schema validity rate and "
        "reliability score to account for failures and invalid outputs.",
        "",
        "## Variant comparison",
        "",
        "| Prompt | Model | Reliability | Schema valid | Category acc. | Consistency | Latency (avg ms) | Total tokens | Est. cost (USD) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for variant in summary["variant_metrics"]:
        reliability = _fmt_optional(variant["average_reliability_score"], decimals=2)
        schema_rate = _fmt_percent(variant["schema_validity_rate"])
        category_acc = _fmt_optional(variant["category_accuracy"])
        consistency = _fmt_optional(variant["average_consistency_score"])
        latency = _fmt_optional(variant["average_latency_ms"], decimals=1)
        lines.append(
            f"| {variant['prompt_version_name']} | {variant['model_name']} | "
            f"{reliability} | {schema_rate} | {category_acc} | {consistency} | "
            f"{latency} | {variant['total_tokens']} | {variant['total_estimated_cost_usd']} |"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
        ]
    )
    rec = summary.get("recommendation")
    if rec is None:
        lines.append("_No recommendation (insufficient scored variants)._")
    else:
        prompt_name = rec.get("recommended_prompt_version_name") or "unknown prompt"
        lines.append(
            f"Deterministic recommendation for this benchmark: "
            f"**{prompt_name}** with **{rec['recommended_model_name']}** "
            f"(reliability {rec['reliability_score']:.2f}). {rec['reason']}"
        )
        if len(summary.get("models", [])) == 1:
            lines.append("")
            lines.append(
                "_Both variants used the same model; this comparison is between "
                "prompt variants, not models._"
            )

    if summary.get("failure_category_counts"):
        lines.extend(["", "## Failure categories", ""])
        for category, count in summary["failure_category_counts"].items():
            lines.append(f"- `{category}`: {count}")

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `summary.json` — machine-readable aggregate metrics",
            "- `results.csv` — per-variant comparison table",
            "- `methodology.json` — dataset, scoring, and measurement definitions",
            "",
            "## Limitations",
            "",
        ]
    )
    for item in summary["limitations"]:
        lines.append(f"- {item}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt_optional(value, *, decimals: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def _fmt_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _write_json(path: Path, payload: dict) -> None:
    sanitized = _sanitize_dict(payload)
    path.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sanitize_dict(value):
    if isinstance(value, dict):
        return {key: _sanitize_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_dict(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str):
        text = _SECRET_LIKE_PATTERN.sub("[redacted]", value)
        return _ABSOLUTE_PATH_PATTERN.sub("[redacted-path]", text)
    return value
