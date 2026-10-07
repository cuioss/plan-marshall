envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:31Z

component=plan-marshall:manage-metrics
category=improvement
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Pass the four context-load columns from every dispatcher to record-dispatch-boundary

## Context

`record-dispatch-boundary` accepts `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens` and `--cache-creation-input-tokens` — the per-DISPATCH counterpart to the per-PHASE four-field view `enrich` writes. An omitted flag writes the literal `unmeasured` so a caller-passed-nothing stays distinguishable from a measured zero.

Across this plan, **31 of 31** dispatch-boundary rows wrote `unmeasured` into all four columns:

| Phase | rows | measured |
|---|---:|---:|
| 4-plan | 1 | 0 |
| 5-execute | 10 | 0 |
| 6-finalize | 20 | 0 |

`context_position_cost` consequently reports `position_multiple: unmeasured` and `position_multiple_basis: unmeasured` plan-wide.

## Root cause

The recorder grew the four-column view; no dispatcher call site was updated to pass it. The `unmeasured` sentinel is doing its job — it is correctly reporting that nobody measured — but the population is 100 %, so the capability is inert rather than partial.

## Proposed action

Forward the dispatched leaf's four-field `message.usage` totals at every `record-dispatch-boundary` call site. The three sites are the phase-4-plan, phase-5-execute and phase-6-finalize dispatchers. Until then, `position_multiple` should be read as "never instrumented", not as "no positional cost".

## Evidence

- aspect: log_analysis — `context_position_cost: total_rows: 31, measured_rows: 0, unmeasured_rows: 31, no_tool_use_rows: 0`; per-phase `4-plan 0/1, 5-execute 0/10, 6-finalize 0/20`.
- Every row's `unmeasured_columns` field lists all four names; `unrecognised_columns` and `indeterminate_columns` are empty on all 31, so this is a clean not-passed rather than a parse failure.
- Directly relevant to the standing token-reduction priority: the per-phase read-cost decomposition shows resident context per tool-use rising 209K → 363K → 298K → 524K across the dispatching phases, and the per-dispatch view is the instrument that would attribute that rise.
