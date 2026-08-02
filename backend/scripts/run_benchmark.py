"""Run the controlled portfolio benchmark (opt-in live OpenAI execution).

Usage (from ``backend/`` with virtualenv active):

    # Preview plan bounds — no API key, no provider calls
    python scripts/run_benchmark.py --dry-run

    # Execute live benchmark after setting OPENAI_API_KEY in backend/.env
    python scripts/run_benchmark.py --confirm-live

    # Re-export evidence from an already-completed experiment
    python scripts/run_benchmark.py --export-only --experiment-id 42

Live execution requires ``--confirm-live`` and a configured ``OPENAI_API_KEY``.
This script is never imported by the application, CI, or tests.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.benchmarks.plan import DEFAULT_BENCHMARK_PLAN, BenchmarkPlan
from app.benchmarks.runner import (
    BenchmarkConfigurationError,
    describe_benchmark_plan,
    export_existing_benchmark,
    run_live_benchmark,
)
from app.benchmarks.validation import InvalidBenchmarkIdError, validate_benchmark_id
from app.core.config import get_settings
from app.core.exceptions import ProviderUnavailableError
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or export the portfolio benchmark (live execution is opt-in)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the benchmark plan and resolved seed IDs without executing.",
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required flag to make paid OpenAI provider calls.",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Export sanitized evidence from an existing completed experiment.",
    )
    parser.add_argument(
        "--experiment-id",
        type=int,
        help="Experiment id for --export-only.",
    )
    parser.add_argument(
        "--benchmark-id",
        default=DEFAULT_BENCHMARK_PLAN.benchmark_id,
        help="Benchmark id used for the export directory name.",
    )
    return parser


def _plan_from_args(args: argparse.Namespace) -> BenchmarkPlan:
    validate_benchmark_id(args.benchmark_id)
    if args.benchmark_id != DEFAULT_BENCHMARK_PLAN.benchmark_id:
        return BenchmarkPlan(
            benchmark_id=args.benchmark_id,
            experiment_name=f"Portfolio benchmark ({args.benchmark_id})",
            dataset_version=DEFAULT_BENCHMARK_PLAN.dataset_version,
            dataset_item_names=DEFAULT_BENCHMARK_PLAN.dataset_item_names,
            prompt_version_names=DEFAULT_BENCHMARK_PLAN.prompt_version_names,
            model_names=DEFAULT_BENCHMARK_PLAN.model_names,
            repeat_count=DEFAULT_BENCHMARK_PLAN.repeat_count,
        )
    return DEFAULT_BENCHMARK_PLAN


def _print_dry_run(summary) -> None:
    plan = summary.plan
    print("Portfolio benchmark dry run")
    print(f"  benchmark_id:        {plan.benchmark_id}")
    print(f"  dataset_version:     {plan.dataset_version}")
    print(f"  dataset_items:       {len(plan.dataset_item_names)}")
    print(f"  prompt_variants:     {len(plan.prompt_version_names)}")
    print(f"  models:              {', '.join(plan.model_names)}")
    print(f"  repeat_count:        {plan.repeat_count}")
    print(f"  planned_runs:        {summary.planned_run_count}")
    print(
        "  logical invocations: "
        f"{summary.planned_run_count} (benchmark live path uses SDK max_retries=0)"
    )
    print(f"  dataset_item_ids:    {summary.dataset_item_ids}")
    print(f"  prompt_version_ids:  {summary.prompt_version_ids}")
    print(
        "  OPENAI_API_KEY:      "
        + ("configured" if summary.openai_api_key_configured else "not configured")
    )
    print()
    print(
        "To execute live: set OPENAI_API_KEY in backend/.env, then run "
        "`python scripts/run_benchmark.py --confirm-live`"
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args()
    plan = _plan_from_args(args)

    if not args.dry_run and not args.confirm_live and not args.export_only:
        parser.error("One of --dry-run, --confirm-live, or --export-only is required.")

    if args.confirm_live and args.dry_run:
        parser.error("--confirm-live and --dry-run cannot be used together.")

    if args.export_only:
        if args.experiment_id is None:
            parser.error("--export-only requires --experiment-id.")
        db = SessionLocal()
        try:
            export_dir = export_existing_benchmark(
                db,
                experiment_id=args.experiment_id,
                plan=plan,
                benchmark_id=plan.benchmark_id,
            )
        except (
            BenchmarkConfigurationError,
            FileExistsError,
            ValueError,
            InvalidBenchmarkIdError,
        ) as exc:
            print(f"Export failed: {exc}", file=sys.stderr)
            return 1
        finally:
            db.close()
        print(f"Exported benchmark evidence to {export_dir}")
        return 0

    db = SessionLocal()
    try:
        if args.dry_run:
            summary = describe_benchmark_plan(db, plan)
            _print_dry_run(summary)
            return 0

        get_settings.cache_clear()
        settings = get_settings()
        if not settings.openai_api_key:
            print(
                "OPENAI_API_KEY is not configured. Set it in backend/.env before "
                "running a live benchmark.",
                file=sys.stderr,
            )
            return 1

        print(
            f"Starting live benchmark: {plan.planned_run_count} logical provider "
            f"invocation(s) ({len(plan.dataset_item_names)} items × "
            f"{len(plan.prompt_version_names)} prompts × "
            f"{len(plan.model_names)} model(s) × {plan.repeat_count} repeats; "
            "benchmark path uses OpenAI SDK max_retries=0)"
        )
        result = run_live_benchmark(db, plan=plan)
    except ProviderUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except BenchmarkConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (FileExistsError, InvalidBenchmarkIdError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()

    print()
    print("Benchmark complete")
    print(f"  experiment_id:   {result.experiment_id}")
    print(f"  planned_runs:    {result.planned_runs}")
    print(f"  completed_runs:  {result.completed_runs}")
    print(f"  failed_runs:     {result.failed_runs}")
    print(f"  export_dir:      {result.export_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
