envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:29:51Z

# Phase re-entry accounting never fires on a real loop-back, so loop-back spend lands on the wrong phase

component: plan-marshall:manage-metrics
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

Two ledgers in the same plan disagree about whether a re-entry happened:

- `status.metadata` records `loop_back_iteration: 2` and
  `loop_back_reentry: {from_phase: 6-finalize, to_phase: 5-execute, at: 2026-08-30T20:44:38Z}`.
- `work/metrics.toon` `[5-execute]` records `close_count: 1`,
  `value_scope: single_close`, `end_time: 2026-08-29T23:35:40Z`.
- `manage-metrics generate` reports `re_entered_phases[0]` — empty.

Independent corroboration that 5-execute really did run again: the phase-5
dispatch-boundary ledger carries two rows dated **2026-08-30** (18:31:37 and
21:07:16), and `reconcile-ledgers` reports a phase-5 `record-step` row at
2026-08-30T17:56:02 — all after the row's recorded close.

## Root cause

The accumulate-on-re-entry contract (`close_count`, `value_scope`,
`cumulative_fields` / `last_close_fields`, `re_entered_phases`) is fully
specified and fully implemented in `end-phase` / `phase-boundary`. Nothing calls
it on a loop-back: the orchestrator re-enters 5-execute without closing the phase
again, so the trigger is never pulled. The detector is correct and inert.

## Consequence, stated in tokens

6-finalize opened at 2026-08-29T23:35:40Z and never closed. Every loop-back
execute pass therefore falls inside the open 6-finalize window. The reported
`6-finalize: 3,539,132 tokens` is **not finalize cost** — it is everything after
that timestamp, including two loop-back execute passes. The label and the
population disagree, and no field on the row says so.

## The generalizable rule

A re-entry detector keyed on a counter that only a close increments cannot
observe a re-entry that skips the close. Derive re-entry from the observable that
actually changes — here, a phase row whose dispatch-boundary rows carry
timestamps after its own `end_time` — or make the loop-back path call the close.
Two ledgers that can disagree need a reconciliation that runs by default, not one
a retrospective has to invoke by hand.
