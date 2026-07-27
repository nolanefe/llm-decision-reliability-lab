# LLM Decision Reliability Lab

A full-stack evaluation platform for comparing prompt versions and model
outputs on a fixed task: it runs each variant repeatedly against a small
dataset, measures schema validity, latency, token cost, task quality, and
run-to-run consistency, and rolls those up into a single reliability score
you can compare side by side in a dashboard.

See [PROJECT_SPEC.md](./PROJECT_SPEC.md) for the full v0.1 specification.

## Backend development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

alembic upgrade head        # apply migrations
python -m app.db.seed       # load built-in dataset items + prompt versions (idempotent)
pytest                      # run the backend test suite
```

The seed command only inserts built-in records that don't already exist (matched
by dataset item name, and by prompt version name+version) — it never overwrites
existing rows and is safe to run repeatedly. It is not run automatically on
application startup.
