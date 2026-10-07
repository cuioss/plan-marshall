envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:48:46Z

component=plan-marshall:plan-retrospective
category=bug

# shape_violation cannot fire — its evidence surface is empty for every plan, and the violation it exists to catch was present

## Observation

The execution-context dispatch audit defines four checks. Three of them found nothing on PLAN-TRUTH-001 and were genuinely clean. The fourth, `shape_violation`, found nothing because it is incapable of finding anything.

**The detection signal, as specified:**

> A `(plan-marshall:manage-config)` `effort resolve-target` entry exists in `decision.log` for a given `role` value but no subsequent `[DISPATCH]` line carrying the same `role` appears in `work.log` within the same plan run.

**What this plan's logs actually contain:**

- `work.log` — 16 `[DISPATCH]` lines, every one carrying a resolved `level=level-3` or `level=level-5`.
- `decision.log` — **zero** `effort resolve-target` entries. Not a small number. Zero, across all 89 decision entries.

A resolved `level=level-N` is produced only by the resolver. So 16 resolves demonstrably happened and none was recorded on the surface the check reads. `shape_violation` therefore reports 0 on this plan, and on any plan with the same instrumentation, regardless of the truth.

**The violation it exists to catch was present.**

`pre-submission-self-review` was dispatched **three** times. The evidence is in a third surface the check does not read — `manage-execution-manifest record-step` rows in `decision.log`, each with distinct token totals:

```
16:21:23Z  pre-submission-self-review  outcome=error     total_tokens=202832  tool_uses=33
16:44:46Z  pre-submission-self-review  outcome=error     total_tokens=228067  tool_uses=47
17:18:57Z  pre-submission-self-review  outcome=executed  total_tokens=222106  tool_uses=29
```

`work.log` carries exactly **one** `[DISPATCH]` line for the step, at 16:14:08Z. Two re-dispatches of a step on the DISPATCHED roster emitted no canonical `[DISPATCH]` evidence — which is precisely the `shape_violation` failure mode: "a spawn happened but no matching `[DISPATCH]` line was emitted".

It was found by counting `record-step` rows, not by the check built to find it.

**Even the step-local decision trail is short in the same direction.** `decision.log` carries `Candidate-count gate DISPATCH` entries at 16:15:24Z (`total_candidates=72`) and 16:22:43Z (`total_candidates=71`) — two, for three dispatches. The third iteration logged neither a candidate-gate decision nor a `[DISPATCH]` line.

## Root cause

The check pairs an *intent* record against an *observable* record and reports the unmatched intents. When the intent surface is unpopulated, the unmatched-intent set is empty by construction — the check degenerates to `len([]) == 0` and returns clean.

This is the standing archetype in its purest form: a set-guarding detector whose population is derived from a source that can be empty, with no guard asserting the population is non-empty. The corpus already carries the rule — *every set-guarding detector must be population-derived, and the derivation must be asserted non-empty*. This plan **applied** that rule to its own deliverable (D4c asserts the derived head-dependent set is non-empty and contains both known members) while the retrospective aspect auditing that same plan violated it.

## Proposed action

1. Assert the population: when `[DISPATCH]` lines exist but zero `effort resolve-target` entries do, emit a `shape_violation` finding for the *instrumentation gap itself* rather than reporting a clean pass. An audit whose intent surface is empty must say so.
2. Add `manage-execution-manifest record-step` rows as a third evidence surface. Pair `[DISPATCH]` lines against `record-step` rows for the same step: `record_step_count > dispatch_line_count` is a missing-emission finding, and it is the surface that actually caught this one.
3. Fix the emission side too — the `[DISPATCH]` obligation is fused to the dispatch branch, so a re-dispatch of the same step must emit its own line. One line for three dispatches is the defect; the audit should never have needed to infer it.
4. Either make the resolver write its `effort resolve-target` decision entry, or remove the surface from the detection spec. A documented evidence surface that no producer writes is worse than an undocumented one, because it makes a vacuous zero look like a verified zero.

## Evidence

- aspect: execution_context_dispatch_audit — `surface_a_dispatch_lines: 16`, `surface_b_resolve_target_entries: 0`
- aspect: execution_context_dispatch_audit — `detector_blind_spot.observed_population_of_that_signal: 0`
- `logs/decision.log` — three `record-step` rows for `pre-submission-self-review`, two `Candidate-count gate DISPATCH` entries, zero `effort resolve-target` entries
- `logs/work.log:233` — the single `[DISPATCH]` line for `pre-submission-self-review`
- `standards/execution-context-dispatch-audit.md` § "Detection Logic" and § "Pairing rule" — the specified signal
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` — `display_detail: "3 passes at max_iterations, 6 findings all fixed and committed"`
