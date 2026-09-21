envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:18Z

component=plan-marshall:manage-metrics
category=improvement
confidence=medium
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=logging_gap_analysis,log_analysis

# Dispatch-boundary ledger covered 19% of finalize spend and 0/4 context columns

## Context

Two coverage gaps in the per-dispatch instrumentation, both visible in this plan:

**1. Boundary rows cover a fifth of the phase.** `6-finalize` recorded 2 dispatch-boundary rows
totalling 238,455 tokens, against a phase accumulator total of 1,233,654 — 19.3%. Seven finalize
steps were token-proven to have dispatched (per `check-dispatch-audit`'s `dispatch_coverage`),
so 2 rows for 7 dispatches. `metrics.md` reports the coverage as "undecidable — the phase carries
no `subagent_samples` to compare against", so the shortfall cannot even be attributed to the
declared-excluded dispatch classes. The largest phase in the plan is the least instrumented.

**2. The context-load columns are unmeasured everywhere.** All 4 boundary rows across all three
dispatching phases report `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
`cache_creation_input_tokens` as unmeasured:

```
context_position_cost:
  total_rows: 4
  measured_rows: 0
  unmeasured_rows: 4
  position_multiple: unmeasured
```

For an epic whose stated priority is token reduction and whose own analysis puts ~73-76% of
billing weight in `cache_read`, the instrument that would measure context position produced no
measurement at all.

## Root cause

The four context columns are optional flags on `record-dispatch-boundary` defaulting to 0, and no
finalize dispatch site forwards them. The boundary-row shortfall is a separate call-site coverage
question: most finalize steps complete without calling `record-dispatch-boundary`.

## Proposed action

Have the phase-6-finalize dispatcher call `record-dispatch-boundary` for every dispatched step
(it already calls `accumulate-agent-usage` for each), and forward the four-field
`message.usage` view on that call. Until the columns are populated, `position_multiple` should
keep reporting `unmeasured` rather than a computed value — that part is already correct and
should be preserved.

## Evidence

- aspect: logging_gap_analysis — 2 gaps recorded with figures
- `metrics.md` 6-finalize: "Dispatch-boundary total: 238,455 ... 2 row(s) recorded, coverage
  undecidable"; phase total 1,233,654
- aspect: log_analysis — `context_position_cost.measured_rows: 0` over `total_rows: 4`
