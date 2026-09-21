envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:22:54Z

component=plan-marshall:manage-status
category=improvement
confidence=medium
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# planning-lane routes on pre-settlement scope_estimate and change_type and is never re-evaluated

## Context

The planning-lane router fired once, at 05:39:25Z in `1-init`, and recorded its inputs:

```
signals={'scope_estimate': 'multi_module', 'change_type': 'verification', ...}
-> planning_lane=deep  (fired=['S2:scope_estimate', 'S7:risk_prose'])
```

Both inputs moved afterwards:

- `scope_estimate` — the init heuristic classified `multi_module` from `distinct_paths=12` over the **whole request body** (its own record calls it a "pre-route coarse guess"). `2-refine` settled it to `single_module` at 05:51:21Z ("Modules: 1, Files: 5").
- `change_type` — `verification` at route time; `3-outline` settled `bug_fix` at 05:55:31Z, explicitly superseding the prior value because "the read-intent-only invariant forbids [verification] for a write-bearing plan".

`planning_lane=deep` was never revisited. `S2:scope_estimate` — one of the two signals that fired the deep lane — was fired by a value that stopped being true 12 minutes later.

The lane governed a run that cost **4,697,985 tokens** for a 3-deliverable, 10-file, single-module bug fix: 3.6x the `single_module + bug_fix` **error** anchor of 1.3M, and that total is a floor because `6-finalize` never closed.

## Root cause

The lane decision is taken at the earliest point in the plan, from the coarsest available estimates, and is structurally terminal — there is no re-evaluation seam after refine and outline settle the very fields the router consumed. The router does record its inputs faithfully (which is why this is diagnosable at all); it simply never gets asked again.

## Proposed action

This is deliberately filed as an **improvement with a measurement request attached**, not as a settled fix — a deep lane may well have been right here, and the plan did find and fix a genuinely subtle two-sided defect. What is wrong is that nobody can tell, because the question was never re-asked.

1. Record a **lane re-evaluation check** at the `4-plan` boundary: re-run the lane predicate against the settled `scope_estimate` / `change_type` and log whether the original routing still holds. Logging only — no automatic re-routing — so the corpus accumulates evidence before any behaviour changes.
2. Over a corpus of such records, measure how often the settled inputs would have routed differently, and what those runs cost. Only then decide whether re-routing (or a cheaper mid-plan lane step-down) is warranted.

The counterfactual this plan offers on its own: had the router seen `single_module` + `bug_fix`, `S2:scope_estimate` would not have fired, leaving `S7:risk_prose` alone.

## Evidence

- `decision.log` 05:39:25Z — the full lane-routing record with its `signals` and `scope_provenance` blocks
- `decision.log` 05:39:22Z — "pre-route coarse guess over the whole request body, deep-lane Step 9 may overwrite"
- `decision.log` 05:51:21Z — "Scope: single_module - Modules: 1, Files: 5"
- `decision.log` 05:55:31Z — "Detected bug_fix (confidence 85) ... supersedes prior verification value"
- aspect: plan_efficiency — `totals_tokens=4697985` against the `single_module+bug_fix` error anchor of 1.3M; `max_phase_token_share 0.52`
- aspect: routing_decisions — `cost_preview.comparison: not_attempted` (no cost preview was recorded in `status.metadata.execution_profile_cost_preview`, so the lane's own cost projection cannot be graded against the outturn either)
