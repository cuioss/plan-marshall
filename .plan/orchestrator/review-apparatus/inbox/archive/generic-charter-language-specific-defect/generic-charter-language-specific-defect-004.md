envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T16:50:29Z

# shape_violation reports a clean zero over a population that is always empty

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_aspects: execution_context_dispatch_audit

## Context

The dispatch audit's `shape_violation` check pairs two surfaces: Surface B, the `effort resolve-target` entries in `decision.log` (the *intent* record), against Surface A, the `[DISPATCH]` lines in `work.log` (the *observable*). An intent with no matching observable is the finding — a spawn that happened without emitting the canonical dispatch line.

This plan's `decision.log` carries 117 entries and **not one** is an `effort resolve-target` record. Surface B is empty. The pairing rule therefore had nothing to pair, and `shape_violation` reports `0`.

That zero is indistinguishable, in the emitted fragment and in the compiled report, from a genuine clean pass. The only resolve-target evidence anywhere in this plan is prose *inside* a `[DISPATCH]` line body — "effort resolve-target rejected role=research under phase-5-execute (valid subkeys default, verification-feedback)" — which Surface B does not read, because it scans `decision.log` for `(plan-marshall:manage-config)` entries and this text lives in `work.log` under a different tag.

## Root cause

The check's population is the set of resolve records, and nothing establishes that the population is non-empty before the check reports its verdict. If `effort resolve-target` does not write a decision-log entry at all — which is what 117 clean entries suggest — then `shape_violation` can only ever be zero, for every plan, forever. A check that cannot fail is not a guard; and this one reports its structural silence as a pass.

This is the same failure mode the epic already tracks under "a count of 0 whose population is unknown", and it is one the audit's own subject matter is sensitive to: the aspect exists to catch a spawn that produced no evidence, and it is itself blind for exactly that reason.

## Proposed action

1. Have the aspect emit `surface_b_population_state` alongside the count, and forbid grading `shape_violation` as a pass when the population is empty — report `indeterminate`, never `0`.
2. Establish whether `effort resolve-target` writes a decision-log entry at all. If it does not, Surface B as specified does not exist and the check must either be re-anchored on an emission that does exist, or retired; if it does, determine why 17 dispatches in this plan produced none.
3. Generalise: every set-guarding check in the retrospective must publish its population size next to its finding count, so a zero that means "nothing to look at" is never rendered as a zero that means "looked, found nothing".

## Evidence

- aspect: execution_context_dispatch_audit — `surface_b_resolve_target_entries: 0`, `surface_b_population_state: empty`
- `logs/decision.log` — 117 entries read in full; zero `effort resolve-target` records
- `logs/work.log` 2026-08-09T11:18:40Z — the sole resolve-target mention, inside a `[DISPATCH]` body, not on Surface B
- `standards/execution-context-dispatch-audit.md` § Pairing rule — "An unmatched resolve at end of pairing is a `shape_violation`"; with no resolves, there is nothing to leave unmatched
