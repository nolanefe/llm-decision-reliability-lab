# Benchmark evidence: portfolio-v1

Exploratory, limited-sample benchmark results for the LLM Decision Reliability Lab. These figures describe **this controlled setup only** and must not be read as universal model or prompt superiority claims.

## Run summary

- **Executed at:** 2026-08-02T15:24:36.387969
- **Dataset version:** built-in-seed-v1 (4 items)
- **Prompt variants:** baseline-triage, explicit-criteria-triage
- **Model(s):** gpt-5-mini
- **Repetitions:** 2
- **Planned runs:** 16
- **Logical provider invocations:** 16 (benchmark live path uses OpenAI SDK max_retries=0 → one HTTP attempt per invocation)
- **Provider executions completed:** 16/16
- **Provider/infrastructure failures:** 0
- **Schema-valid outputs:** 8/16
- **Schema-validation failures:** 8

**Accuracy note:** Category and priority accuracy in the table below are calculated over **schema-valid runs only**. Use schema validity rate and reliability score to account for failures and invalid outputs.

## Variant comparison

| Prompt | Model | Reliability | Schema valid | Category acc. | Consistency | Latency (avg ms) | Total tokens | Est. cost (USD) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| explicit-criteria-triage | gpt-5-mini | 100.00 | 100.0% | 1.0000 | 1.0000 | 5551.2 | 5345 | 0.00763800 |
| baseline-triage | gpt-5-mini | 10.00 | 0.0% | — | 0.0000 | 11346.0 | 7498 | 0.01386200 |

## Recommendation

Deterministic recommendation for this benchmark: **explicit-criteria-triage** with **gpt-5-mini** (reliability 100.00). Selected for the highest average reliability score (100.00) among 2 tested variant(s).

_Both variants used the same model; this comparison is between prompt variants, not models._

## Failure categories

- `schema_error`: 8

## Files

- `summary.json` — machine-readable aggregate metrics
- `results.csv` — per-variant comparison table
- `methodology.json` — dataset, scoring, and measurement definitions

## Limitations

- Exploratory benchmark with a limited sample size (4 dataset items, 2 prompt variants, 1 model, 2 repetitions).
- Results describe this controlled setup only; they do not prove universal prompt or model superiority.
- Estimated cost uses the dated pricing snapshot in methodology.json applied to observed input/output token counts only; actual billed cost can differ and cached-input discounts are not modeled.
- Category and priority accuracy are calculated over schema-valid runs only; use schema_validity_rate and reliability_score to account for failures and invalid outputs.
- Not statistically significant for production reliability claims.
