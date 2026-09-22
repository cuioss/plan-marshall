# PLAN-10: Task staging and phase-5 entry mechanics

epic: quality-aspect
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-10-plan-execute-mechanics.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT.

## Objective

Make task staging and phase-5 entry structural: no stale file silently read, no
upstream commit absorbed as no-overlap, freshness verdicts stable per tree,
deliverable-less edits declared. G22 + G18 + G23 + 2 singletons (12 lessons).

## Deliverables

1. Absolute-path tasks-file staging, never worktree-relative stale reads (2026-09-02-15-001).
2. Orchestrator post-return q-gate-validation reachability (2026-09-03-08-001).
3. Verification-only guard honoring mutation_scope surveys (2026-09-03-09-001).
4. Single-verdict freshness per unchanged tree (2026-09-03-10-001).
5. declared_set_closure rewarding declaration growth, not shrinkage (2026-09-04-17-013).
6. Registered finding type for scope_creep over-threshold (2026-09-08-22-002).
7. Overlap-aware self-absorb at first phase-5 entry (2026-08-30-11-001).
8. Deliverable-scoped chain-tail predicate (2026-09-09-01-003).
9. OUTCOME before voluntary checkpoint yield (2026-09-14-05-001).
10. Deliverable-less production edits as declared scope changes (2026-09-14-05-004).
11. scope_estimate over edit targets, not named paths (2026-09-03-16-001).
12. Manifest step-params freshness for deliverable-written knobs (2026-09-04-12-001).

## Claim Labels

- OBSERVED: phase-5 entry absorbed a relocating upstream commit as zero-overlap while narrative/outline/tasks invalidated — read at `lessons-archive/2026-08-30-11-001.md` § Symptom.
- OBSERVED: one unchanged tree returned two freshness verdicts minutes apart — read at `lessons-archive/2026-09-03-10-001.md` § Problem.
- HYPOTHESIS: overlap-aware absorb plus deterministic freshness closes both — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-5-execute/` § baseline-drift entry (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/` — absorb, chain-tail, outcome.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — staging, guards.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/` — freshness, scope_creep.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-11/PLAN-12 lifecycle surfaces — PLAN-10 runs first.
- Adjacent to: WS-04/PLAN-07 footprint capture read at absorb time.
- Landing follow-up (PLAN-01, #1545; folded from ledger-joins-001): changed_files
  uniformity residual — 31/33 task records measured, finalize-step and
  late-dispatch closes among the unrecorded. Present-and-empty semantics must hold
  on every close path, not just the measured ones.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/quality-aspect/plans/PLAN-10-plan-execute-mechanics.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
