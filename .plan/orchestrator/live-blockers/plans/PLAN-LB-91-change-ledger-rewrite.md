# PLAN-LB-91: A history rewrite no longer invalidates the change ledger, and the 5-execute boundary names the real cause

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-91-change-ledger-rewrite.md` and is queued as one row file, `queue/PLAN-LB-91.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-23 from `lessons-routing-046` (consumer epic `pm-mcp-core-m2-m4`, five plans), graded **high**. It is
> the one finding of that drain that makes a plan unable to finish without manual work.

## Objective

The change ledger is pure-append and keyed by commit sha. Every history rewrite (the `sync-baseline` rebase, an amend, a
cherry-pick) rewrites the branch's shas, so every earlier row stops matching, and `manage-status transition --completed
5-execute` refuses with `execute_commits_unrecorded` for the whole branch. Recovery is a manual re-append of every commit.
This plan maps rows of rewritten commits onto their rebased counterparts, so a rewrite costs no manual step, and makes the
refusal say what happened.

## Deliverables

1. **A rewrite is mapped onto the ledger without breaking append-only.**
   - `manage-change-ledger` gains a remap verb that maps the rows of rewritten commits onto their rebased counterparts (by patch-id, or `git range-diff`) and appends the mapped rows.
   - The rewriting step calls it: `finalize-step-sync-baseline` emits an old-to-new sha map whenever it rewrites commits, and the remap consumes that map.

   *Done when:* a fixture branch with three recorded commits is rebased; after the remap the 5-execute boundary no longer reports them unrecorded, and the ledger still holds the original rows. A fixture amend maps the same way. At HEAD the boundary refuses with all three unrecorded (HYPOTHESIS, see Claim Labels).

2. **The refusal names the rewrite and carries the repair.**
   - When the unrecorded set is the whole branch, or every recorded row's sha is no longer an ancestor of HEAD, `execute_commits_unrecorded` reports the rewrite signature instead of a bookkeeping gap.
   - The refusal payload carries the exact unrecorded shas and the ready-to-run remap or append invocation.

   *Done when:* a fixture whose every row was rewritten returns the rewrite signature with the remap invocation; a fixture with one missing row returns the plain gap with its append invocation.

Split guard: two deliverables, one surface (the ledger and the boundary that reads it). The consumer message also asks to append the ledger row in the same step as the task commit, and to let `review_support` switch to a full round when its delta base was rewritten; both are left out here and recorded as follow-ups, not blockers.

## Claim Labels

- OBSERVED: the 5-execute boundary compares `git rev-list` shas with ledger rows, matching a full sha or a prefix of at least 7 characters, and refuses with `execute_commits_unrecorded` — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` L440-475 (`_sha_is_recorded`), L93 and L534.
- OBSERVED: the ledger records `worktree_sha` per row and appends only — `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` (`append_entry`, `change_record`).
- OBSERVED: `finalize-step-sync-baseline` rebases the worktree branch onto `origin/{base_branch}` through the `git-workflow` verbs `baseline-reconcile` and `worktree-rebase-to` — `phase-6-finalize/standards/finalize-step-sync-baseline.md`.
- HYPOTHESIS: after such a rebase every recorded sha is absent from `git rev-list {merge_base}..HEAD`, so the refusal covers the whole branch (consumer counts 14 of 14, 8 of 11, 2 of 11; not re-run here) — confirm with a fixture rebase against `_cmd_lifecycle.py` (verify-at-outline).
- HYPOTHESIS: a patch-id match recovers every rebased commit except one whose patch changed during conflict resolution; such a commit needs the explicit append path — confirm with a fixture (verify-at-outline).
- Verify-first clause: choose where the remap is invoked (the rewriting step, the boundary, or both) and record why; confirm that the existing prefix rule in `_sha_is_recorded` does not already absorb part of the case.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py` — the new remap verb (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the boundary refusal (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md` — the sha map (D1)
- OBSERVED: `test/plan-marshall/manage-change-ledger/`
- OBSERVED: `test/plan-marshall/manage-status/test_transition_boundary_guards.py` (D2)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none of the staged specs declare these files.
- Adjacent to: `review_support` (the delta-base follow-up) and the task-commit path, both untouched here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-91-change-ledger-rewrite.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
