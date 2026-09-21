envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:47Z

# Re-route planning_lane when phase-2-refine revises scope_estimate downward

component: plan-marshall:phase-2-refine
category: improvement
confidence: high
source: plan-retrospective (aspects: routing-decisions, plan-efficiency)
suggested_epic: truthful-signals

## Context

This plan consumed **2,635,090 tokens** on a 10-file, 2-deliverable bug fix, against a `single_module + bug_fix` calibration anchor whose ERROR column is 1.3M. That is 2.0x the error threshold, and the figure is a FLOOR — 6-finalize had not closed when metrics were generated, and this retrospective's own spend is not in it.

The token spend is not concentrated (`max_phase_token_share = 0.33`), so there is no single runaway phase to blame. The routing decision is the lever:

- **10:31:08** — init routed `planning_lane=deep` on signals `S2:scope_estimate` (multi_module, 8 distinct paths) and `S7:risk_prose`.
- **10:38:36** — phase-2-refine REVISED the scope: `Scope: single_module (revised from init multi_module) - Module: plan-marshall, Files: 4 confirmed`.
- The lane was never reconsidered. 3-outline + 4-plan then spent **819K tokens (31% of the plan)** producing 2 deliverables and 3 tasks.

## Root cause

`planning_lane` is routed once, at init, from a pre-route coarse guess that the init log itself labels provisional ("pre-route coarse guess over the whole request body, deep-lane Step 9 may overwrite"). Phase-2-refine's job is precisely to replace that guess with confirmed facts, and here it did — halving the scope band. But the lane routing is not re-evaluated against the revision, so the coarse guess survives the very correction that was supposed to supersede it.

The asymmetry is the point: init's own log acknowledges the guess is provisional and names a downstream overwrite path, yet the one phase that produces the authoritative scope value has no edge back into the routing decision.

## Proposed action

1. After phase-2-refine writes a revised `scope_estimate`, re-run the `planning-lane` predicate against the revised signal set and log the outcome — whether it changes the lane or confirms it. A confirming re-route is still worth logging; it converts "the lane was never rechecked" into "the lane was rechecked and held".
2. Emit the re-route decision to `decision.log` in the same `(plan-marshall:manage-status:planning-lane)` shape so the routing-decisions retrospective aspect can grade both the init routing and the post-refine routing.
3. Calibration note for whoever picks this up: do NOT read this single plan as proof that deep-lane-on-revised-single_module is always wrong. The plan also carried genuine complexity (a falsified premise, a loop-back, 5 PR-review fix tasks). The claim here is narrow and testable: the lane decision was never re-evaluated after its primary input changed.

## Evidence

- aspect: plan-efficiency — `[BUDGET] error, total_tokens=2635090` vs `single_module+bug_fix error at 1.3M`; `tokens_per_file_modified=263509` (5.3x the 50K fallback); `total_tokens_per_deliverable=1317545` (2.6x the 500K fallback)
- `logs/decision.log:6` — init `planning_lane=deep`, `fired=['S2:scope_estimate', 'S7:risk_prose']`, `scope_estimate: 'multi_module'`
- `logs/decision.log:13` — refine `Scope: single_module (revised from init multi_module) ... Files: 4 confirmed`
- `metrics.md` — 3-outline 438,530 + 4-plan 380,337 = 818,867 tokens
- aspect: routing-decisions — `posture_verdict: correct` (the posture dial was right; the lane dial is the one at issue)
