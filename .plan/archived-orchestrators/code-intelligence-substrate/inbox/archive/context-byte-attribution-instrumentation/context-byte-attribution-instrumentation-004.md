envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:41:54Z

# Record a dispatch boundary for every dispatch, including 2-refine and q-gate

component: plan-marshall:plan-marshall
category: bug
confidence: high
source_plan: context-byte-attribution-instrumentation
source_pr: 1086

## Context

The dispatch-boundary ledger is the store this epic's own spec designated as the ground truth when
phase rows are wrong — PLAN-CIS-030's URGENT section states the missing tokens "survive only in
`work/metrics-dispatch-boundaries-*.toon`" and instructs D1 to "reconcile phase rows against the
dispatch-boundaries ledger, not merely re-read the phase rows".

That ledger is itself incomplete. Enumerated over the full `work.log` (383 lines, not sampled):

| Phase | `[DISPATCH]` lines | boundary rows | gap |
|---|---|---|---|
| 2-refine | 1 | 0 (**no file at all**) | 1 |
| 3-outline | 2 | 1 | 1 |
| 4-plan | 2 | 1 | 1 |
| 5-execute | 2 logged (3 actual) | 4 | — |
| 6-finalize | 10 | 9 | 1 (in-flight, expected) |

17 `[DISPATCH]` lines produced 15 rows.

## Root cause

Three distinct holes:

1. **2-refine never calls `record-dispatch-boundary`.** No
   `metrics-dispatch-boundaries-2-refine.toon` is created, so a 174,204-token dispatch leaves zero
   per-dispatch trace.
2. **q-gate-validation dispatches are never recorded.** Both q-gate spawns (3-outline 07:48:35,
   4-plan 08:40:17) rode a proper `execution-context` envelope but produced no row — hence 2
   dispatches vs 1 row in each of those phases.
3. **One phase-5 re-dispatch emitted no `[DISPATCH]` line.** `work.log` carries three
   `execution-context.phase-5-execute Complete` markers (09:38:55, 10:29:46, 10:40:05) but only two
   `[DISPATCH]` lines. The third re-entry is invisible to the dispatch-logging contract.

## Proposed action

Treat "every dispatch emits exactly one `[DISPATCH]` line and exactly one boundary row" as an
invariant and assert it. A deterministic reconciliation — count `[DISPATCH]` lines per phase, compare
to boundary rows, fail loud on a mismatch — is cheap and would have caught all three holes. Add the
`record-dispatch-boundary` call to the 2-refine and q-gate-validation dispatch sites.

An always-incomplete ledger cannot serve as the reconciliation ground truth the epic assigned it.

## Evidence

- aspect: execution_context_dispatch_audit — full-population enumeration of 17 `[DISPATCH]` lines vs 15 rows, per-phase gap table above
- aspect: logging_gap_analysis — `metrics-dispatch-boundaries-2-refine.toon` absent from the 92-file plan artifact manifest
- Direction A of the same audit is fully CLEAN (17/17 rode `execution-context-{level}`), so this is a recording gap, not an envelope-discipline failure
