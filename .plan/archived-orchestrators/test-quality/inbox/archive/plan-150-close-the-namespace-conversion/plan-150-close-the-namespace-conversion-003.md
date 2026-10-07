envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:53:29Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=plan-150-close-the-namespace-conversion

# Run enrich during finalize so billing and inline-phase tokens are not lost

## Context

`manage-metrics enrich` is the only writer of the four-field usage view
(`input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`)
and of the derived `billing_weighted_total`. It is also the writer that folds a
zero-dispatch phase's inline main-context spend into `total_tokens` so the phase stays
countable.

It did not run for this plan. Consequences, all measured:

- `totals_billing_weighted_total: 0` with `totals_billing_weighted_total_population_count: 0`;
  the `Billing (cost)` column renders `-` on every phase row and on the Total.
- `1-init` carries no token figure and no worked figure at all — 32m1s of wall clock, 100
  percent of it recorded as idle — because it dispatched nothing and nothing folded its
  inline spend in.
- Every column Total in `metrics.md` is therefore marked `(n=5/6)` and is a floor rather
  than a total.

The plan-efficiency aspect's `[BUDGET]` error findings fired on 3,952,297 tokens, a figure
that excludes a whole phase. The verdicts hold a fortiori — the real number is higher — but
they were reached on an incomplete measurement, which is luck rather than design.

## Root cause

Nothing in the finalize step sequence invokes `enrich`, so a plan reaches `record-metrics`
with its four-field view never populated and its inline-only phase never attributed. The
retrospective's own Step 2.5 reconcile calls `generate`, which backfills accumulators but
explicitly does not perform the transcript walks `enrich` owns.

## Proposed action

Invoke `manage-metrics enrich --plan-id {plan_id} --session-id {session_id}` as part of the
finalize sequence, before `record-metrics` performs its authoritative close. The session id
is already captured and stored (`status.metadata.session_ids`), so no new input is needed.

## Evidence

- aspect: plan_efficiency — `totals_coverage`: `totals_tokens_population_count: 5` over `totals_population_denominator: 6`; note that every Total is a FLOOR
- aspect: logging_gap_analysis — `instrumentation_observations`: enrich never ran; `billing_weighted_total` is 0 with population_count 0 on every row
- `metrics.md` Phase Breakdown — the `1-init` row renders `-` for Worked, Tokens and Tool Uses; the `Billing (cost)` column is `-` throughout
