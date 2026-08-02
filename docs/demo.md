# Demo walkthrough (45–90 seconds)

This guide supports a short recruiter or interview demonstration of the **LLM Decision Reliability Lab**. It distinguishes **mock/demo results** (used in screenshots and Playwright tests) from **real tracked benchmark evidence** (generated only after an explicit live run).

## Before you start

**Option A — Mock/demo (no API key, no cost):** Use the Playwright fixture path or open a completed experiment whose metrics are mocked in E2E tests. Reliability scores of **75** and **40** in screenshots are deterministic demo values, not live-model output.

**Option B — Real evidence:** Run the portfolio benchmark after setting `OPENAI_API_KEY` (see [benchmarks/README.md](../benchmarks/README.md)). Results land in `benchmarks/results/portfolio-v1/`.

Local app:

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:3000`.

---

## Script (~60 seconds)

### 1. Overview (5 s)

Land on the home page. Point out the workflow: fixed dataset → prompt variants → repeated runs → deterministic scoring → comparison dashboard.

> "This compares prompt and model configurations on a structured support-ticket task using exact-label scoring, not an LLM judge."

### 2. Fixed evaluation dataset (10 s)

Navigate to **Datasets**. Show the version-controlled items with expected category and priority labels.

> "The dataset is checked into the repo — fictional tickets with known correct labels so correctness is an exact match."

### 3. Create an experiment (15 s)

Go to **Experiments → New experiment**.

- Name the experiment (e.g. "Demo comparison").
- Select 2–4 dataset items.
- Select **two prompt variants** (e.g. `baseline-triage` and `explicit-criteria-triage`).
- Select one model (`gpt-5-mini`).
- Set repetitions to **2** and note the **planned run count** updating live.

> "The plan size is bounded upfront — items × prompts × models × repeats."

### 4. Live execution is explicit and paid (10 s)

Save the draft, open the experiment detail page, and click **Execute**. The confirmation dialog shows the planned run count.

> "Nothing hits OpenAI until I confirm here. CI and tests never call the provider — they use a fake provider or mocked API responses."

**For demo without spending:** Stop before confirming, or show a **completed** experiment (mock or real).

### 5. Compare reliability and consistency (15 s)

On a **completed** experiment detail page:

- **Executive summary** — total runs, schema-valid rate, average reliability.
- **Recommendation panel** — deterministic cascade (not LLM-generated): highest reliability, then cost, then latency.
- **Reliability comparison chart** — side-by-side variant scores.
- **Variant comparison table** — category/priority accuracy, consistency, latency, tokens, estimated cost.

> "Reliability combines exact-match quality, repetition consistency, schema validity, and provider success. Cost and latency are reported separately — they don't inflate the reliability score."

### 6. Failures and limitations (10 s)

Scroll to the **Failure explorer** if any failures exist. Categories: invalid JSON, schema error, content mismatch, provider error, timeout.

Close with limitations:

> "This is exact-match scoring on a small fixed task — exploratory, not production certification. Playwright screenshots use mocked metrics; real numbers live under benchmarks/results/ after an explicit live run."

---

## Quick reference: mock vs real

| Aspect | Mock / demo | Real benchmark |
| --- | --- | --- |
| Reliability scores 75 / 40 in README screenshot | Playwright `page.route()` fixtures | Not used |
| Provider invocations | None | 16 logical invocations for portfolio-v1 (SDK max_retries=0 on benchmark path) |
| Evidence location | `frontend/e2e/fixtures/completed-experiment.ts` | `benchmarks/results/portfolio-v1/` |
| When to use | Visual CI, offline demo | Portfolio evidence after `--confirm-live` |

---

## Optional: run real benchmark after demo

```bash
cd backend
python scripts/run_benchmark.py --dry-run      # verify plan
python scripts/run_benchmark.py --confirm-live # paid execution
```

Then link reviewers to `benchmarks/results/portfolio-v1/README.md`.

## Interrupted live runs

If live execution is interrupted (Ctrl+C, process crash, network drop), the local Experiment row may remain in `running` status with partial Run records. Such a run cannot be exported as completed benchmark evidence. Review the local database state and start a fresh benchmark with `--confirm-live` rather than attempting to resume the interrupted experiment.
