envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:08:38Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_aspects=execution-context-dispatch-audit,plan-efficiency

# Three token ledgers report three different totals for one phase with no population labels

## Context

Three files in the same plan directory each claim to account for `6-finalize` token spend, and all three disagree:

| Mechanism | File | 6-finalize total | Population |
|---|---|---|---|
| `execution_log` | `execution.toon` | 1,039,208 | 8 non-zero of 15 rows |
| dispatch-boundary ledger | `work/metrics-dispatch-boundaries-6-finalize.toon` | 1,563,107 | 10 rows |
| accumulator | `work/metrics-accumulator-6-finalize.toon` | 1,664,610 | 11 samples |

Spread is 1.60x. The LOWEST of the three is the one `check-routing-decisions` consumes as `cost_preview.actual_tokens` — the figure feeding the recalibration loop.

The gaps are structural, not rounding. `execution_log` has no row at all for `project:finalize-step-deploy-target` (1131 files emitted) or `project:finalize-step-sync-plugin-cache` (10 bundles synced), both of which completed with real work. The accumulator counted 11 samples where the boundary ledger recorded 10 rows, so one dispatched step worth ~101,503 tokens is in one ledger and not the other.

Two further gaps in the same family: `verify:module-tests` — the manifest's SOLE phase-5 verification step — has no `execution_log` row, while `verify:quality-gate`, which the decision matrix explicitly dropped, does have one. And all 13 dispatch-boundary rows across three phases carry `0` for every one of the four context-load columns, so the per-dispatch billing view is empty for the entire plan.

## Root cause

Three producers each emit "the total" for the same phase without publishing the population it summed, so no consumer can tell which number is a floor and which is complete. `metrics.md` gets this right — it stamps `partial: true` and `n=4/6` — but that discipline was never extended to the three underlying stores.

## Proposed action

Add a reconciliation verb that reads all three stores for a phase, publishes each total ALONGSIDE its population (row count / sample count / step count), and flags a spread above a threshold. Make every producer stamp its own population next to its figure — the `n=k/6` convention `generate` already uses. Until then, `cost_preview.actual_tokens` should name `execution_log` as its source rather than presenting itself as the plan's actual spend.

## Evidence

- `execution.toon` `execution_log[16]` — 6-finalize rows sum to 1,039,208; `check-routing-decisions` emits exactly `actual_tokens: 1039208`
- `work/metrics-accumulator-6-finalize.toon` — `total_tokens: 1664610`, `samples: 11`
- `analyze-logs` `dispatch_boundaries.6-finalize` — 10 rows summing 1,563,107, every context-load column `0`
- `status.metadata.phase_steps` records both `deploy-target` and `sync-plugin-cache` as `outcome: done` with substantive `display_detail`
