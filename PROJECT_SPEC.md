# PROJECT_SPEC.md — LLM Decision Reliability Lab (v0.1)

## Problem

Teams building LLM-powered features have no consistent way to answer "is this
prompt/model combination actually reliable?" Manual spot-checks catch obvious
failures but miss variance across repeated runs, silently invalid JSON output,
cost regressions, and quality drift between prompt versions. There is no
lightweight tool to run a fixed task repeatedly across prompt/model variants
and produce a comparable reliability score.

## Target User

An individual developer or small team iterating on a prompt or model choice
for a structured-output task (e.g., classification, extraction, structured
recommendations) who wants objective, repeatable evidence for which
prompt/model version to ship — without standing up a full eval platform.

## User Workflow

1. Define a small evaluation dataset (fixed set of inputs with expected
   properties) for a single task.
2. Define 2–3 prompt versions to test against that dataset.
3. Select a model (OpenAI to start) and a number of repetitions per
   input/prompt pair.
4. Run the experiment: the backend calls the LLM runner for every
   (input × prompt version × repetition) combination.
5. The evaluation service scores each output for schema validity, task
   quality, and consistency across repeated runs, and categorizes failures.
6. View results in the dashboard: an experiment list, and a detail page that
   compares prompt versions side by side on reliability score, latency,
   token usage/cost, and failure breakdown.

## Required Features (v0.1 MVP)

- Small, fixed evaluation dataset (checked into the repo, not uploaded)
- 2–3 prompt versions per experiment
- At least one OpenAI model integration
- Repeated runs per (input, prompt version) pair
- Structured JSON output from the model
- Schema-validity measurement
- Latency measurement per run
- Token-usage and estimated-cost tracking
- Task-quality scoring
- Consistency scoring across repeated runs
- Failure categorization (e.g., invalid JSON, schema mismatch, low quality)
- Combined reliability score (single comparable metric per prompt version)
- Experiment list page and experiment detail/comparison page
- SQLite persistence
- Alembic migrations
- Backend tests
- Frontend lint and build checks
- GitHub Actions CI

## Explicitly Excluded from v0.1

- Authentication
- Redis
- Celery
- Microservices (single FastAPI backend, monolithic frontend)
- Multiple mandatory model providers (OpenAI only is sufficient)
- Production deployment
- Complex dataset upload systems (dataset is fixed/local for v0.1)
- Human team collaboration features
- Billing
- Enterprise integrations

## Architecture

```
Next.js dashboard
  → FastAPI backend
    → experiment service   (owns experiment/run lifecycle)
    → LLM runner           (calls the model provider, captures latency/tokens)
    → evaluation service   (schema validity, quality, consistency, failure category, reliability score)
  → SQLite (via SQLAlchemy + Alembic migrations)
  → experiment comparison dashboard (list + detail views, reads via FastAPI)
```

- **backend/**: FastAPI app. `app/experiments` orchestrates runs, `app/llm`
  wraps the model provider call, `app/evaluation` scores outputs, `app/db` +
  `app/models` handle SQLite persistence, `app/schemas` defines API/data
  contracts, `app/api` exposes HTTP endpoints. `alembic/` manages schema
  migrations. `tests/` holds backend tests.
- **frontend/**: Next.js app. `app/experiments` holds the list and detail
  routes, `components/` holds shared UI, `lib/` holds API client and
  formatting helpers.

## Success Criteria

- A user can define a dataset + 2–3 prompt versions, run an experiment
  against a real OpenAI model, and see per-run results persisted in SQLite.
- The detail page shows, per prompt version: reliability score, schema
  validity rate, average latency, token usage/estimated cost, quality score,
  consistency score, and a failure-category breakdown.
- Repeated runs of the same experiment produce comparable, persisted results
  (not recomputed from scratch each view).
- `alembic upgrade head` reproduces the schema from a clean database.
- Backend tests pass locally and in CI.
- Frontend lints and builds cleanly in CI.
- GitHub Actions CI runs backend tests and frontend lint/build on every push.
