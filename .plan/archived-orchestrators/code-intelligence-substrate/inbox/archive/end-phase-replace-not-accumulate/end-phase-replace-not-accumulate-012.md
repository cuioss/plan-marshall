envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:24:51Z

component=plan-marshall:manage-status
category=improvement
created=2026-07-29

# A 4.3%-confidence classification and a pointer-derived scope estimate drove a lane route that a human had to override

Three `decision.log` entries from 1-init, in order:

```
[11:51:17Z] Request aspect classified: implementation (confidence=0.043)
[11:52:18Z] Classified scope_estimate=single_module (distinct_paths=1, glob=True, scope_resolved=True)
[11:52:55Z] Routed planning_lane=light (predicate=signal_set, fired=none, ...)
```

Then, ten minutes later:

```
[12:01:32Z] Escalated planning_lane=deep (trigger=premise, lane_escalated=true) — one-way ratchet
[12:01:44Z] ... routed light on scope_estimate=single_module derived from the pointer artifact path only, and change_type resolved null
```

## The two signal-quality problems

**A near-zero confidence is recorded as a settled classification.** `confidence=0.043` is 4.3% — for practical purposes the classifier abstained. The line records it in the same declarative form ("Request aspect classified: implementation") a 95%-confidence result would get, and `request_aspect: implementation` is then persisted to `status.metadata` with no confidence qualifier attached. Downstream consumers read a fact; the classifier produced a coin-flip.

**`distinct_paths=1` counted the pointer, not the target.** The plan was launched with `task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-10-end-phase-replace-not-accumulate.md"`. The one distinct path the scope heuristic found was the **epic spec file**, not any file the plan would touch. `scope_resolved=True` asserts the scope was resolved when what was resolved was the address of the instructions. The real footprint was 6 files across a widely-consumed CLI surface plus three test modules.

## Why it mattered

The light route was wrong and the correction was human. The operator escalated on `trigger=premise`, and the assistant's own hand-off assessed the override as load-bearing:

> "the lane router chose **light** off a `scope_estimate` derived from the *pointer artifact* rather than real targets. Your override to deep was load-bearing — the light lane would have bounded exactly the discovery that found the provenance subtlety."

That discovery was substantive: deep-lane outline found that `_resolve_token_field` returns either a per-close delta or an already-cumulative value, so the spec's implied blanket `+=` would have introduced a **new** double-counting bug. A light-lane outline would plausibly have shipped that.

No automated check flagged the mis-route. `check-routing-decisions` re-evaluated prune predicates and reported `passed: 1, failed: 0`, because it audits which steps were pruned, not whether the lane itself was right. The counterfactual "was light the correct route" is exactly the track-selection-accuracy question, and nothing in-plan asks it.

## Suggested corrective action

1. Persist the confidence alongside the classification (`request_aspect_confidence`) and have `planning-lane` treat a sub-threshold `request_aspect` as an unset signal rather than as a value — the routing predicate currently cannot distinguish "classified implementation" from "guessed implementation at 4.3%".
2. Teach `scope-estimate-heuristic` to recognize a pointer-shaped request: when the only distinct path is a `.plan/local/orchestrator/**/plans/PLAN-*.md` spec (or any `.plan/` artifact), the scope is **unresolved**, not `single_module`. Emit `scope_resolved=False` and let the lane router route on absence rather than on a confident wrong value. The `orchestrator inbox detect` verb already classifies exactly this pointer shape and is the seam to reuse.
3. Log the routing inputs with their provenance, so `distinct_paths=1` records WHICH path — a route derived from a pointer would then be visible in the log without needing the operator to notice it.
