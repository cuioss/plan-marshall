envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:54:10Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=logging_gap_analysis,log_analysis

# Forward the four context-load fields to record-dispatch-boundary

## Context

`manage-metrics record-dispatch-boundary` accepts four per-dispatch context-load flags — `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens` — and correctly writes the literal `unmeasured` into each column when its flag is omitted, so "no measurement was passed" stays distinguishable from "this dispatch loaded zero context". The recorder side of the contract holds.

No call site populates them. Across this plan's three dispatch-boundary files:

- `4-plan`: 1 row, all four columns `unmeasured`
- `5-execute`: 3 rows, all four columns `unmeasured`
- `6-finalize`: 15 rows, all four columns `unmeasured`

`context_position_cost` therefore reports `total_rows: 19`, `measured_rows: 0`, `unmeasured_rows: 19`, `position_multiple: unmeasured`, and `cache_read_per_tool_use: unmeasured` for every phase.

Separately and consistently, `manage-metrics generate` reports `totals_billing_weighted_total_population_count: 0` — no phase row carries a four-field `message.usage` view either, so the `Billing (cost)` column of `metrics.md` renders as `-` on every row including the Total.

The net effect: a plan that spent at least 6.44M dispatched tokens across 19 dispatches cannot say what any single dispatch cost to re-load, and cannot say what the run cost to buy.

## Root cause

The per-dispatch context-load view was added to the recorder without the dispatcher being changed to forward it. The four-field `message.usage` view is available at the dispatch boundary — it is the same source `enrich` reads from the transcripts — but the finalize dispatcher passes only `--total-tokens`, `--tool-uses`, and `--duration-ms`.

Because the columns declare their own absence honestly, nothing fails and nothing warns. The measurement simply is not taken, on every plan.

## Proposed action

- Forward the four `message.usage` fields from the dispatched agent's return envelope to `record-dispatch-boundary` at the finalize dispatcher's call site (and at the `5-execute` and `4-plan` equivalents).
- Surface `measured_rows / total_rows` as a first-class line in the retrospective's log-analysis section, so a run where the ratio is 0/N is visible rather than buried in a per-phase `unmeasured` literal.

## Why this matters beyond bookkeeping

Context re-load is the dominant billing component of a run, and `cache_read_per_tool_use` / `position_multiple` are the only per-dispatch handles on it. With 0 of 19 rows measured, no plan in this corpus can be used to size a context-reduction lever against its own dispatches — the measurement that would justify or refute such a lever does not exist.

## Evidence

- aspect: logging_gap_analysis — `context_load_attribution: total_rows: 19, measured_rows: 0, unmeasured_rows: 19, position_multiple: unmeasured`
- aspect: log_analysis — every dispatch row carries `unmeasured_columns: ["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]`, `unrecognised_columns: []`, `indeterminate_columns: []`
- `manage-metrics generate` → `totals_billing_weighted_total: 0`, `totals_billing_weighted_total_population_count: 0`
- `metrics.md` Phase Breakdown — `Billing (cost)` is `-` on all six phase rows and on the Total
