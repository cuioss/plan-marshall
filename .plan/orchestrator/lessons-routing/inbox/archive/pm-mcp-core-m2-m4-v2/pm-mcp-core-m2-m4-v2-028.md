envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T13:17:30Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall

# Rebase the branch in the baseline-drift recovery path before re-entering execute

- component: plan-marshall:plan-marshall
- category: bug
- confidence: high

## Context

In plan-v2-140, phase-5-execute returned `baseline_drift` (7 upstream commits, one adjacent-line conflict in `doc/adr/README.adoc`). The orchestrator looped back to phase-2-refine, which resolved the Q-Gate finding as `taken_into_account` and moved the plan on, but changed no git state. The re-entered execute returned the same `baseline_drift` a second time. The orchestrator rebased the feature branch by hand, outside any phase. The operator also had to say "rebase prior continuing" mid-run. After the manual rebase the change-ledger remap could not map the old commit 27d13e15, so the orchestrator appended a ledger row by hand.

## Root cause

The drift-recovery loop has no step that rebases the branch. phase-5-execute Step 3 never rebases, and refine only judges the conflict. So a conflicting drift can never clear on its own, and loop 2 repeats loop 1.

## Proposed action

Give the drift-recovery path an explicit rebase step after refine accepts the conflict resolution, run through the git-workflow verbs, with the conflict resolution refine recorded. Have it remap the change ledger for the rewritten commits. Or let refine return a `rebase_required` signal that the orchestrator acts on before it re-dispatches execute. A drift loop whose second probe matches the first should stop with a named reason, not run again.

## Evidence

- decision.log 2026-11-12T21:46:26Z [WARNING] ac82cd: "Drift loop 2 would repeat loop 1 ... no phase rebases the branch"
- decision.log 2026-11-13T08:59:31Z 313046: "ledger row for rebased commit e07bf737 appended (remap could not map 27d13e15)"
- work/metrics-dispatch-boundaries-5-execute.toon: two consecutive `baseline_drift` rows (21:42:18Z, 21:46:01Z)
- chat history: operator turn "before you changes code: ... reabse prior continuing"
- invariant-summary: main_sha drift 4-plan -> 5-execute
