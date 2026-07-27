# Scoring Methodology

This document explains how the reliability lab scores a run of the fixed
customer-support triage task, and why. It describes v0.1 behavior only.

## The task

Every dataset item is a support ticket with a known, fixed expected
`category` and `priority`. Each Run asks a model to return structured JSON
(`category`, `priority`, `summary`, `recommended_action`) for one ticket
under one prompt version. Because the correct `category`/`priority` are
known in advance, correctness can be checked by exact comparison instead
of judgment — which is what makes every score below fully deterministic,
reproducible from the persisted data, and explainable without re-running
anything. There is no LLM judge, no semantic-similarity model, and no
embeddings anywhere in this pipeline.

## Quality score (per run, 0.0–1.0)

```
schema-invalid output           -> 0.0
schema-valid, both labels wrong -> 0.0
schema-valid, one label right   -> 0.5
schema-valid, both labels right -> 1.0
```

A provider failure (timeout, request error) always produces
`schema_valid = False`, so it already falls under the first case — there
is no separate "provider failure" branch in the formula.

## Consistency score (per group, 0.0–1.0)

A **group** is every Run in one experiment that shares
`(dataset_item_id, prompt_version_id, model_name)` — i.e. all repetitions
of one input under one prompt/model combination.

```
consistency_score = (count of the group's most common schema-valid
                      (category, priority) outcome)
                     / (total planned Runs in the group)
```

Invalid JSON, schema errors, and provider failures stay in the
denominator — they count against consistency — but can never contribute
to the numerator. A group with zero schema-valid Runs scores `0.0`. The
same `consistency_score` is assigned to every Evaluation in the group,
including the invalid ones; the reliability formula below is what
excludes it for those. A model that is *consistently wrong* still scores
well on consistency (it reliably reproduces the same outcome) — that is
intentional. Consistency measures reproducibility, not correctness;
quality measures correctness. A model needs both to be trustworthy.

Ties in outcome frequency never change the score, since the score depends
only on the winning count, not on which outcome achieved it.

## Reliability score (per run, 0.0–100.0)

The single formula lives in `app/evaluation/scoring.py` and nowhere else:

```
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
```

Clamped to `[0.0, 100.0]`, computed with `Decimal` throughout, and rounded
to two decimal places at the end. The weights favor quality (does it get
the right answer) while still rewarding schema compliance, reproducible
behavior, and the provider simply not failing outright.

## Why latency and cost are reported separately

Reliability measures **output dependability** — will this prompt/model
combination keep giving correct, well-formed, reproducible answers.
Latency and estimated cost measure **efficiency** — how fast and how
expensive it is to get those answers. Folding efficiency into the
reliability score would hide a real trade-off (a slow, expensive model
that is very dependable vs. a fast, cheap one that is less so) behind a
single number. Both are reported alongside reliability in
`VariantMetrics` so they can be compared directly.

## Recommendation tie-breakers

Given a completed experiment's per-variant metrics, one variant is
recommended using a fixed cascade — never an LLM:

1. Highest `average_reliability_score`.
2. Among variants within **0.50 points** of the top score (the
   threshold is always measured against the single highest score, not
   pairwise), prefer lower `total_estimated_cost_usd`.
3. If still tied, prefer lower `average_latency_ms`.
4. If still tied, use deterministic `(prompt_version_id, model_name)`
   ordering.

The generated `reason` string is built from fixed templates that name
which rule decided the outcome — it is never model-generated text, and it
never claims the recommendation proves production suitability.

## Limitations of deterministic scoring

- **Exact-match only.** Quality scoring is exact string comparison against
  the expected `category`/`priority`. It cannot detect an output that is
  *substantively* correct but phrased differently, nor can it evaluate the
  free-text `summary`/`recommended_action` fields at all.
- **Small samples.** Consistency and accuracy are computed over whatever
  `repeat_count` and dataset size an experiment used; a low repeat count
  makes both figures noisy.
- **Fixed task only.** These formulas assume a task with a known correct
  label per item. They do not generalize to open-ended generation tasks
  without a redesign.
- **A good score is evidence, not a guarantee.** It reflects behavior on
  this fixed dataset under these conditions — it is not a certification
  of production readiness for a different, unmeasured workload.
