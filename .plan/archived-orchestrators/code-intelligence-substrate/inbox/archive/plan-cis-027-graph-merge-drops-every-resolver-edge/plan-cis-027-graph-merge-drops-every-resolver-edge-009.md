envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T15:03:49Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-08-02
bundle=plan-marshall

# shape_violation cannot fire: its resolve-target evidence surface is never written

The execution-context dispatch audit's `shape_violation` check reported zero violations. It
reported zero because it has **no population to evaluate**, not because dispatch was clean.

## Context

`execution-context-dispatch-audit.md` specifies two evidence surfaces:

- **Surface A** — `logs/work.log` `[DISPATCH]` lines (the *observable*)
- **Surface B** — `logs/decision.log` `(plan-marshall:manage-config)` `effort resolve-target`
  entries (the *intent*)

`shape_violation` is defined as a Surface-B record with no matching Surface-A line, and the pairing
rule says "an unmatched resolve at end of pairing is a `shape_violation`."

On this plan:

- Surface A: **20** `[DISPATCH]` lines, all well-formed, all carrying canonical
  `execution-context-level-{3,5}` targets.
- Surface B: **0** records. Across all **95** decision-log entries, not one is an
  `effort resolve-target` record.

With zero resolves, there is nothing to leave unmatched. The check is structurally incapable of
producing a finding regardless of what the dispatcher does.

## Why this is worth filing

The clean result is indistinguishable from a genuine pass. Direction 1 of the same aspect
(envelope conformance) **is** genuinely clean — 20 dispatches, 20 canonical emissions, a populated
set that really passed. Direction `shape_violation` produced the same `0` from an empty set. Both
render identically in the report, and a reader has no way to tell which zero means what.

This is the **fifth recorded instance of the vacuous-guard archetype** in this codebase: a
predicate that never fires reads identically to a predicate that always passes. One prior instance
was introduced *by a fix for* the same archetype.

## Root cause

Surface B is specified as evidence but **nothing writes it**. Dispatch sites emit `[DISPATCH]` to
`work.log` and record nothing to `decision.log`, so the pairing rule the check depends on has one
permanently empty side. The aspect's spec and the dispatcher's instrumentation were never
reconciled.

## Proposed action

Pick one, and in either case fix the reporting:

1. **Populate Surface B** — have `effort resolve-target` emit its decision-log record at every
   dispatch site, so the pairing has both sides and `shape_violation` becomes a live check. This is
   the option consistent with the aspect's stated design (intent paired to observable).
2. **Retire `shape_violation`** and replace it with a check that runs off a populated surface.

**Regardless of which:** the aspect must distinguish *"zero violations over a populated set"* from
*"zero violations over an empty set"* in its own output. Emit the evaluated-population size
alongside every count, so a vacuous pass can never be read as a clean pass. That reporting change
is the durable fix — it makes the next vacuous guard self-announcing.

## Detection heuristic for the archetype

A guard's clean result is only trustworthy when its input population is non-empty **and** reported.
Any check that can return `0` from an empty population must publish the population size next to the
count. This generalises beyond this one aspect and is the reusable half of this lesson.

## Evidence

- aspect `execution_context_dispatch_audit` — `detector_vacuity` finding; `0` resolve-target entries across 95 decision entries against 20 observed dispatches
- `execution-context-dispatch-audit.md` § Inputs, Surface B — specifies decision.log `effort resolve-target` entries as the intent record
- `execution-context-dispatch-audit.md` § Pairing rule — "an unmatched resolve at end of pairing is a `shape_violation`"
- aspect `log_analysis` — `top_tags: DISPATCH,20`; `decision_entries: 95`
- Contrast case: direction-1 envelope conformance passed over a populated set of 20, and is reported with the same `0`
