> **✅ RESOLVED 2026-07-18 — VERIFIED ALREADY-SHIPPED, NO CODE CHANGE.** Plan `leaf-validator-yield` ran as a discovery/audit (operator re-scope from "implement D1/D2" → "audit for residual gaps") and closed with a CLEAN verdict and ZERO source diff. Both headline datapoints are already resolved in shipped code: D1's sanctioned yield-to-sibling pattern exists at `automatic-review` (PR #920, pure FIND-only + dispatcher-owned sibling triage), `pre-submission-self-review` (PR #493, candidate-count gate dispatches the LLM cognitive core as a sibling `Task:` from the non-leaf finalize dispatcher), and `q-gate-validation` (return-flag + orchestrator sibling dispatch). D2's docs are already consistent — `agents.md` is the SSOT for the leaf/dispatch-topology invariant, `dispatch-inline-split.md` locates every validator `Task:` in the main-context dispatcher; no dispatched-leaf step body documents an impossible nested dispatch across the swept surface (phase-1..6 + execute-task). No PR (nothing to ship). Audit conclusion captured as lesson `2026-07-18-10-001`. Do NOT re-open or re-plan.

# Plan — leaf-validator-yield (execution-context topology cost)

**GROUP: EXEC-CONTEXT** (surface: `execution-context` dispatch topology + step body/topology docs + persona) — disjoint from MANIFEST, FINALIZE, and DOCS surfaces; runs in parallel with all three.

**Error class:** dispatch-topology contradiction that is now a COST driver, not just a correctness workaround.

> **Frozen-source caveat:** re-ground the lesson IDs and step-topology citations at outline.

## Why (evidence — this one is a quantified cost, not a datapoint)

A dispatched leaf cannot sub-dispatch its adversarial validator, so the validator runs INLINE inside the leaf. Two faces of one class:

1. **`automatic-review` leaf-topology contradiction** (lesson `2026-07-13-00-001`, 3× — #882/#883/#884): the step is classified dispatched-leaf but its body documents a nested verification-feedback dispatch it cannot perform; it works via sanctioned-yield every run.
2. **NEW cost datapoint (#893):** because a dispatched leaf can't sub-dispatch, **self-review ran INLINE for 6 passes = 1.44M tokens (52% of a 4.2M plan)**. Value-bearing (5 real structural fixes) but the overshoot is real and recurring.

§2 of the roadmap contract lists adversarial validators (q-gates, automatic-review, self-review, security-audit) as sanctioned *sibling* dispatches — but when the HOST phase is itself a dispatched leaf, that guarantee does not hold, and the validator collapses inline.

## Deliverables

### D1 — give the leaf-hosted validator a sanctioned yield-to-sibling path

So that self-review / automatic-review hosted inside a dispatched-leaf phase do NOT run inline but yield to a sanctioned sibling dispatch (the same mechanism the orchestrator-tier build yield uses). **Acceptance:** a dispatched-leaf phase whose body invokes an adversarial validator produces a sibling-dispatched validator run, not an inline one; measure the token delta on a representative plan against the #893 inline baseline (1.44M for 6 passes).

### D2 — align step body/topology docs with reality

The `automatic-review` (and any peer) step body currently documents a nested dispatch it cannot perform. Reconcile the body/topology docs so the documented behavior matches the sanctioned-yield path D1 establishes (no step claims a sub-dispatch it can't do). **Acceptance:** grep confirms no dispatched-leaf step body documents an impossible nested dispatch; the frontmatter topology and the body agree.

## Do NOT
- Do NOT resurrect the dropped D4 "reachability→gating" flip (plan-6): the reachability analyzer over-approximates dispatched-leaf (`2026-07-13-17-001`), which is why that gating was dropped. This plan changes the *yield path*, not the analyzer.
- Do NOT fold in the manifest execution_tier guard (#897) — that is the separate `manifest-compose-gaps` plan (different files).

## Absorbs
- HANDOVER §5 "Dispatched-leaf can't sub-dispatch its adversarial validator — now a COST driver" (lessons `2026-07-13-00-001`, `2026-07-13-12-003`, `2026-07-13-17-001`).
- §2 note (b): "a dispatched leaf cannot sub-dispatch its adversarial validator, so self-review runs inline."

## Size
2 deliverables, one surface. The token payoff (potentially ~1M+ per full-posture plan) justifies its own plan.
