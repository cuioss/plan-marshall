envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:34Z

# Candidate lesson L3 — The four per-dispatch context-load columns are declared, wired and zero on every row

- component: `plan-marshall:manage-metrics`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

`record-dispatch-boundary` accepts four context-load flags — `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens` — documented as "the per-DISPATCH counterpart to the four-field view `enrich` writes", and appends them as four columns at the end of each row.

Across this plan's **20 dispatch-boundary rows in 3 phases** (`4-plan` 1 row, `5-execute` 4 rows, `6-finalize` 15 rows), **all four columns are 0 on every single row**. The `total_tokens` / `tool_uses` / `duration_ms` columns are populated normally on the same rows, so the writer is being called and the payload is real — only the four context-load values are never supplied by any call site.

## Why this is a truthful-signals instance

Billing composition is dominated by `cache_read_input_tokens` (the epic's own re-derived figure puts `cache_read` at ~73-76% of billing weight). A per-dispatch ledger whose cache columns are structurally zero cannot surface that composition, yet it presents as a fully-populated table with a canonical column schema. Any consumer computing a cache-weighted cost from this ledger gets a confident **zero** for the largest component of the real bill.

The defect is invisible from the schema side: the columns exist, the writer accepts them, the docs describe them, and the rows parse cleanly. Only counting non-zero values across the population reveals it.

## Proposed remedy

1. Identify the `record-dispatch-boundary` call sites (the phase-5/phase-6 dispatch-return paths) and forward the dispatched agent's four-field `message.usage` view, which is the same data `enrich` already extracts per phase.
2. Until then, have `record-dispatch-boundary` report a population-derived coverage figure — e.g. a `context_load_rows_populated: 0/20` marker — so a fully-zero ledger cannot read as a measured zero. A column that is always zero must not be indistinguishable from a column that is measured and happens to be zero.
