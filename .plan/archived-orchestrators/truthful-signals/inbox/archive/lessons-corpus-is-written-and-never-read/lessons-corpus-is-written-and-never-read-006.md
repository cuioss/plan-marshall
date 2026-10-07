envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T19:25:45Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-28

# The dispatch audit's `shape_violation` check is vacuous — its intent surface never fires

`standards/execution-context-dispatch-audit.md` defines the `shape_violation`
check over **two** surfaces:

- **Surface A** — `logs/work.log` `[DISPATCH]` lines (the *observable*).
- **Surface B** — `logs/decision.log` `(plan-marshall:manage-config)` `effort
  resolve-target` entries (the *intent*).

The pairing rule matches each Surface-B resolve to the next chronologically
following Surface-A `[DISPATCH]` line carrying the same `role`; "an unmatched
resolve at end of pairing is a `shape_violation`". The check exists to catch the
case where a caller resolved a target but never emitted the canonical dispatch
line.

**On this plan: 14 `[DISPATCH]` lines, 102 decision-log entries, and ZERO
`effort resolve-target` entries.** Surface B is completely empty. The pairing
loop iterates an empty set and returns `shape_violation: 0`.

That zero is not evidence of clean dispatch instrumentation. It is evidence that
the surface the check depends on was never written. Because a `shape_violation`
can only be produced by an *unmatched Surface-B row*, a plan with zero Surface-B
rows can never produce one — the check is structurally incapable of failing.

## Root cause

The `effort resolve-target` script logs no decision entry (or the phase
dispatchers resolve their target without calling it). Either way the audit's
declared two-surface design is running on one surface, and nothing reports the
degradation.

## Solution

1. Emit the intent record: `manage-config effort resolve-target` should write a
   decision-log entry naming the resolved `--phase` / `--role` / `target`, per
   the audit standard's own Surface-B description.
2. Independently, make the audit **fail loudly on an absent surface**: when
   Surface B has zero rows while Surface A has N > 0, report
   `shape_violation: unmeasured` (or a `surface_unavailable` finding), never
   `shape_violation: 0`. A check that cannot fail must say so rather than pass.

## Impact

This is the fourth member of the epic's vacuous-guard archetype, and it is
sitting inside the very aspect built to police dispatch discipline. On this same
run the audit's *other* half found a real `dispatch_coverage_violation`
(`automatic-review` ran inline) — so the aspect is valuable, which is exactly why
its silently-inert half is worth repairing rather than tolerating.

## Related, same run

One cosmetic role-label drift compounds the risk: `work.log:36` emits
`role=phase-3-outline` for `workflow=plan-marshall/workflow/q-gate-validation.md`,
while the sibling dispatch at `work.log:68` emits `role=q-gate-validation` for the
same workflow. `role` is the pairing key. If Surface B ever starts emitting, that
inconsistency will produce a false `shape_violation` on the first run.
