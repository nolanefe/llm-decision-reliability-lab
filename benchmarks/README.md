# Portfolio benchmark evidence

This directory holds **sanitized, tracked benchmark results** from controlled live-model runs.

## Structure

```
benchmarks/
  results/
    <benchmark-id>/
      README.md          Human-readable summary with cautious language
      summary.json       Machine-readable aggregate metrics
      results.csv        Per-variant comparison table
      methodology.json   Dataset, scoring, and measurement definitions
  runs/                  Local-only raw execution artifacts (git-ignored)
```

## Generating evidence

After seeding the database and configuring `OPENAI_API_KEY` in `backend/.env`:

```bash
cd backend
source .venv/bin/activate

# Preview plan bounds (no API calls)
python scripts/run_benchmark.py --dry-run

# Execute live benchmark (16 logical invocations for portfolio-v1)
python scripts/run_benchmark.py --confirm-live
```

The default **portfolio-v1** plan uses:

- 4 built-in dataset items (subset of `app/db/seed_data.py`)
- 2 prompt variants (`baseline-triage`, `explicit-criteria-triage`)
- 1 model (`gpt-5-mini`)
- 2 repetitions per combination → **16 logical provider invocations**

The benchmark live path sets OpenAI SDK `max_retries=0` and `store=False`, so each logical invocation maps to one HTTP attempt under normal SDK behavior. Category and priority accuracy in exported results are calculated over **schema-valid runs only**; use schema validity rate and reliability score to account for failures and invalid outputs.

Re-export from an existing completed experiment:

```bash
python scripts/run_benchmark.py --export-only --experiment-id <id>
```

## What gets tracked

Only portfolio-safe, sanitized summaries are written under `benchmarks/results/`. Raw API responses, API keys, and local absolute paths are never exported.

## Current status

Live benchmark evidence for **portfolio-v1** is tracked under `benchmarks/results/portfolio-v1/`. Regenerate presentation files from the stored completed experiment without provider calls:

```bash
rm -rf ../benchmarks/results/portfolio-v1
python scripts/run_benchmark.py --export-only --experiment-id <id>
```
