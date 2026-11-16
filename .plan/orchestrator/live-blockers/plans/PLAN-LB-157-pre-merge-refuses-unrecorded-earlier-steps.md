# PLAN-LB-157: The branch-cleanup pre-merge gate refuses while a manifest step ordered before it has no terminal record

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

A finalize step ordered before `branch-cleanup` (order 70) that was skipped, for example `adr-propose` at order 62 after a hand-driven final round, is caught by no guard before the merge. It surfaces only at the tail, when the manifest still lists the step with no record, after the branch is merged and the worktree removed, because the end-of-phase `phase_steps_complete` handshake fires after the point where the step could still have run in order. Add a pre-merge guard that refuses the merge while any manifest step ordered before `branch-cleanup` has no terminal record. This is the second recorded occurrence of this skip.

## Deliverables

1. The `branch-cleanup` pre-merge gate enumerates the manifest's `phase_6.steps` ordered below `branch-cleanup` and checks each with the existing step-record assertion (`assert-step-recorded --require-terminal`); any step without a terminal record refuses the merge with a named reason that lists the steps, and routes back to the dispatcher so the step can still run in order. A step the manifest marks not-applicable for this plan, or already recorded `done` / `skipped` / `loop_back` with a reason, does not block.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
2. The refusal is a distinct reason in the merge-gate vocabulary, documented in `branch-cleanup.md` and the finalize dispatcher's description of the step order, and covered by tests: one unrecorded earlier step (refuses), every earlier step recorded (admits), an `adr-propose` step with `default_on: false` absent from the manifest (admits), and a re-entry after the step is recorded (admits).
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- The guard reads the manifest and the step records; it never runs or records a step itself.
- The guard runs before the merge-mutex hold window opens or is released and re-acquired under the existing invariants, so it adds no new lock path.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.

## Claim Labels

- OBSERVED (leaf reading, not re-read): the only enforcement is the per-dispatch post-guard (`assert-step-recorded --require-terminal`, `step_record_missing`) and the end-of-phase `phase_steps_complete` handshake that fires at the phase transition, after the merge; `adr-propose` is order 62 with `default_on: false`.
- OBSERVED (consumer report): a second occurrence in API-Sheriff plan `plan-sec-03-pending-authorization-store-fairness` (PR #581); the earlier occurrence is archived as API-Sheriff lessons `2026-10-12-07-004`, `-07-008` and `2026-10-13-14-005`.
- HYPOTHESIS: no sweep over all manifest steps ordered before `branch-cleanup` exists at the pre-merge gate — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` § Pre-Merge Gate and § Pre-Merge Review-Completeness Barrier (verify-at-outline; the orchestrator read the document up to the Merge-Authorization Roster and did not reach the gate section).
- OBSERVED (leaf reading, not re-read): `branch-cleanup` runs inline in the orchestrator, not in a dispatched leaf, and its merge-queue landing wait is a bounded re-issued `pr wait-for-queue-settle` owned by the orchestrator — so the consumer's report that a dispatched leaf stalled on its own background wait does not describe this tree and is not part of this plan.
- Verify-first clause: the outline settles where the sweep belongs (the pre-merge gate, or the dispatcher before it dispatches `branch-cleanup`) and how a step excluded from the manifest by preset is told apart from a skipped one.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_assert_step_recorded.py` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none staged.
- Adjacent to: `PLAN-LB-101` and `-120` (shipped) touched the merge gates; their behaviour stays untouched. The local corpus lessons `2026-11-12-19-003` and `-19-004` sit in the same step and stay out of scope.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-157-pre-merge-refuses-unrecorded-earlier-steps.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
