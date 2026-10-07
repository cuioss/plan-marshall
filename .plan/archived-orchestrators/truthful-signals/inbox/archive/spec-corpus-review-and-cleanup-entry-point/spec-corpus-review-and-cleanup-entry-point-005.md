envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:17:48Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=spec-corpus-review-and-cleanup-entry-point
source_aspects=execution_context_dispatch_audit,log_analysis

# Dispatch shape-violation check has no left-hand side: zero effort resolve-target records

## Context

`check-dispatch-audit` pairs two surfaces to detect dispatch-shape violations: Surface B, the `effort resolve-target` records in `decision.log` (the resolve/intent side), against Surface A, the `[DISPATCH]` work-log lines (the observable side). For this plan it reported:

```
shape_violation:
  status: not_evaluated
  evaluated_population: 0
  violations: 0
  reason: "no `effort resolve-target` records in decision.log — Surface B ... is empty,
           so the shape-violation check has no left-hand side to evaluate."
```

Surface A was healthy: 31 `[DISPATCH]` lines against 25 completions, ratio 1.24, `confidence: nominal`, and coverage classified all 16 terminal finalize steps cleanly (7 dispatched, 9 inline, 0 no-evidence, 0 `missing_dispatch_emission`). The plan's `decision.log` holds 187 entries. Not one of them is an `effort resolve-target` record.

## Root cause

The effort-resolution side emits nothing. Whether the emission was never wired, or is conditional on a path this plan did not take, is not established here — but the observable consequence is that a check with a documented purpose ran over an empty population for an entire 5.4M-token plan, and would do so for any plan whose Surface B is silent.

## Why this is worth an epic slot

The check itself is exemplary about it — it reports `not_evaluated` and spells out that "a bare 0 here would be a never-evaluated verdict wearing an evaluated-clean face." That is precisely the discipline this epic exists to enforce, and it worked: nobody was misled. The residual defect is one level up. A check that is structurally unevaluable is not a check; if Surface B is never emitted, the shape-violation arm is dead code that reports its own deadness once per plan and is otherwise ignored. Either the emission gets wired, or the arm should be retired so the audit stops carrying a permanently `not_evaluated` block.

## Proposed action

1. Determine whether `effort resolve-target` decision-log emission exists at all in the current dispatch path, or whether it is conditional and this plan simply never met the condition.
2. If it is missing, wire it — the pairing is the only mechanism that can detect a dispatch whose resolved target disagrees with the target it actually ran against.
3. If it is deliberately conditional, have `check-dispatch-audit` publish *why* Surface B was empty in terms of the condition (rather than only that it was empty), so a reader can tell "this plan took the other path" from "this emission does not exist".

## Evidence

- aspect: execution_context_dispatch_audit — `shape_violation.status: not_evaluated`, `evaluated_population: 0`, with the reason quoted above
- aspect: execution_context_dispatch_audit — Surface A is healthy by contrast: `dispatch_line_count: 31`, `completion_count: 25`, `confidence: nominal`, `missing_dispatch_emission: 0`
- aspect: log_analysis — `decision_entries: 187`, so `decision.log` was actively written throughout; the absence is specific to this record type, not a dead log
