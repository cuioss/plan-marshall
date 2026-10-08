envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:04Z

component=plan-marshall:phase-6-finalize
category=improvement
source_plan=lb-22-finalize-loop-control
confidence=high

# Let the pre-push gate produce build evidence the freshness check accepts

## Context

The freshness check that guards the execute-to-finalize transition and the push accepts only a whole-tree `verify` for a change that spans bundles. With green rows for `compile plan-marshall`, the whole-tree `quality-gate`, `verify plan-marshall` and `verify pm-plugin-development` all matching the current tree, it still returned `stale` with reason `build_scope_narrow` ("none can be cited").

The pre-push quality gate runs per-bundle arms plus a whole-tree `quality-gate` (its record here: "2 bundles + whole-tree quality-gate green, test-compile + module-tests green"). None of that is evidence the freshness check will take. So after every fix commit the run owes one more build: a whole-tree `verify`, which resolves above the per-call time ceiling (1208 to 1408 s estimated) and must be run by the orchestrator. The three slowest builds of this plan were 1030 s, 1026 s and 714 s; the pre-push gate fired 3 times.

## Root cause

Two gates that sit next to each other ask for different build scopes. The gate that runs first does not produce what the gate that runs second requires, so the same tree is built twice.

## Proposed action

One of:

- give the pre-push quality gate a whole-tree `verify` arm when the change spans more than one bundle, and record it in the change ledger so the freshness check cites it; or
- let the freshness check accept the union of per-bundle verifies when together they cover every bundle the change touches, plus the whole-tree `quality-gate` for the cross-bundle lint.

## Evidence

- aspect: chat_history_analysis - execute hand-backs at TASK-21 and TASK-22: "Freshness gate: stale, reason build_scope_narrow ... Only a whole-tree verify covers it" and "the ledger rows matching the current tree are quality-gate (too few analyses) and the two bundle verifies (scope narrower than the change), so none can be cited".
- aspect: log_analysis - `slowest_scripts`: 1029870 ms, 1026320 ms, 714240 ms, all `pyproject_build`; builds own 79.3 percent of script time.
- aspect: plan_efficiency - finalize spent 5.93M tokens with the gate, CI and review each re-run after fix commits.
- scope of the evidence: the `build_scope_narrow` verdict was observed at the execute-exit freshness check; that the push-time check behaves the same is the operator's observation, consistent with the push record `basis=ledger-verified`.
