envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T13:41:23Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=prompt-standard-and-doctor-rule
recurrence_of=none

# The two finalize row ledgers barely pair, so no single-ledger cost sum is defensible

## Context

`manage-metrics reconcile-ledgers` on this plan reports, for `6-finalize`: **8 of 20 execution-log rows paired** with a dispatch-boundary row.

- **9 `row_absent_from_boundary_ledger`** — `record-step` rows with no boundary partner, including `project:finalize-step-lessons-housekeeping` (113,884 tokens), `project:finalize-step-plugin-doctor` (74,477) and `project:finalize-step-review-retrospective` (119,783).
- **3 `row_absent_from_execution_log`** — terminated dispatches carrying **574,858 tokens** (169,497 + 162,088 + 243,273) that no `record-step` row names. That spend is invisible to any `execution_log` sum.
- `5-execute` adds 3 more one-sided rows (`verify:module-tests`, `verify:quality-gate`, `verify:coverage`).

Independently: the boundary ledger holds **11 rows against 13 dispatched-step firings** implied by `status.metadata.phase_steps` (lessons-housekeeping 1 + plugin-doctor 2 + pre-submission-self-review 5 + simplify 2 + create-pr 1 + automatic-review 1 + review-retrospective 1). Only **4 rows are attributable to `pre-submission-self-review`'s 5 firings** — round 3 (findings filed 23:14:19–23:14:35) has no boundary row between the 23:03:41 and 23:28:03 rows. Its spend sits in the phase total and in neither row ledger.

`channel_completeness` reports `ratio: 0.409` and `confidence: low` — the audit already knows the channel is sparse; what it does not say is that the sparseness is two-sided.

## Root cause

The two ledgers are written by independent call sites with no shared transaction and no shared key (a boundary row carries no `step_id`), so a dispatch can land in one and not the other in both directions — which `reconcile-ledgers`' own contract states. What this plan shows is that the failure is not rare: on a normal run only 40% of rows pair, and the shortfall is not explained by the declared `dispatch_boundary_excluded_classes` (none of which is a finalize step).

The consequence is that every per-step cost figure in a retrospective is drawn from whichever ledger the reader happened to open, and none of them is the population.

## Proposed action

1. Give the dispatch-boundary row a `step_id`, so the join stops being a 300-second timestamp window and starts being a key. That alone converts most of the 12 one-sided rows into either a genuine pair or a genuine gap.
2. Make `union_rows` the figure the retrospective renders for a phase's dispatch population, and mark any single-ledger sum as a floor when `paired_rows < union_rows`. `reconcile-ledgers` already publishes `union_rows`; nothing currently reads it.
3. Find why a dispatch terminates without recording a boundary — the missed round-3 write is the concrete instance to trace.

## Evidence

- `manage-metrics reconcile-ledgers --plan-id prompt-standard-and-doctor-rule`: `union_rows: 24`, `execution_log_rows: 20`, `boundary_rows: 12`, `findings_count: 17`; `6-finalize` `paired_rows: 8` of 20
- `work/metrics-dispatch-boundaries-6-finalize.toon`: 11 rows; `status.metadata.phase_steps` implies 13 dispatched-step firings
- qgate finding timestamps `45f9f0` / `977805` / `4804a5` at 23:14:19–23:14:35 with no boundary row in that window
- aspect: execution_context_dispatch_audit — `channel_completeness.ratio: 0.409`, `confidence: low`
