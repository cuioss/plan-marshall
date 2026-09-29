# PLAN-26: Git-workflow and worktree-location contracts

> ✅ **Staged 2026-09-29 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-26-git-and-worktree-contracts.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Close four places where the documented git and worktree path cannot be followed, or silently does
something other than what it says:
- the documented first push fails on every plan;
- the pre-commit artifact scan asks about tracked fixtures;
- the move-back ends the merge-lock hold early;
- an inbox write from a plan worktree lands in the worktree's copy of the ledger.

## Deliverables

1. **The first push works as documented.** `workflow-integration-git` "Commit Changes" Step 6 documents only
   `git -C {worktree_path} push`. A plan's feature branch is created with no upstream, so every first
   finalize push fails (`fatal: The current branch … has no upstream branch`, exit 128). The run had to
   improvise `--set-upstream origin {branch}`. Document the idempotent `--set-upstream` form, or configure
   the upstream at `worktree-create`.
2. **The artifact scan asks only about what the change could introduce.** `detect-artifacts` routes every
   tracked file to `uncertain`, so the pre-commit confirmation scales with repository size:
   - one run got `safe: []`, `uncertain: 271`, all tracked `test/**/fixtures/**`, and the 2 committed
     files appeared in neither list (`module-budget-campaign-completion-010`, previously routed to the
     PM-MCP carry-over as MB10.1);
   - the PLAN-12 run hit the same false positives on committed fixtures.

   Scope the confirmation population to files new or modified in the current diff, and report
   pre-existing tracked files as a count.
3. **The move-back ends only a lock it acquired.** branch-cleanup acquires the merge mutex under
   `merge_hold_window=full_window_release_at_waits` and documents its release after `switch-and-pull`.
   `integrate_into_main integrate` acquires and releases the same re-entrant lock internally, so the hold
   ends before `worktree-remove`. The terminal release then returns `action: noop, message: lock not held
   (already free)`, which is indistinguishable from a legitimate no-op. Make the inner holder release only
   what it acquired, and make the terminal release distinguish "released by an inner holder" from "never
   held".
4. **Orchestrator-store writes from a plan worktree reach the live ledger.** After phase-5 move-in, two
   `orchestrator inbox write --slug process-compliance` calls from the worktree cwd resolved the worktree's
   own checked-out copy of `.plan/orchestrator/`. The allocator, reading only that copy, re-issued
   sequence numbers (`-006`/`-007`) already taken in main's live inbox. The files then rode the plan's PR
   and collided by name at merge, while the verb reported `status: success`. Resolve the orchestrator
   store main-anchored (as the lessons corpus handle does, and consistent with #1652's optional shared
   ledger worktree). When the resolved store sits inside a plan worktree, refuse or report the anchor.

## Claim Labels

- OBSERVED: the documented push fails on every first push — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-028.md`; Step 6's only command is `git -C {worktree_path} push` at HEAD (`marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md:174`)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: workflow-integration-git SKILL.md:170-175 Step 6 only 'git -C {worktree_path} push'; no script sets an upstream
- OBSERVED: artifact-scan confirmation on tracked fixtures — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-025.md` § 2 and `inbox/archive/module-budget-campaign-completion/module-budget-campaign-completion-010.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: git-workflow.py scan_artifacts:726-760 routes every tracked pattern match to uncertain; no diff scoping
- OBSERVED: the move-back releases the widened hold early; the terminal release is a `noop` — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-021.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: integrate_into_main.py:13-24 acquires and releases the shared merge lock on every exit path
- OBSERVED: inbox writes from a worktree cwd landed in the worktree's ledger copy with colliding sequence numbers — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-019.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: use_worktree=false; file_ops.get_orchestrator_store_root:729-730 -> get_tracked_config_dir (cwd-relative = worktree copy)
- HYPOTHESIS: the orchestrator store resolves cwd-relative through `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` § `get_store_dir`, with #1652's `orchestrator_worktree.py` engaged only when `orchestrator.use_worktree` is on — confirm/refute at those two files (verify-at-outline)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: file_ops.py get_store_dir:590-661 / get_orchestrator_store_root:701-731; orchestrator_worktree.py:77-89,125-135 main-anchored only when the knob is on

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` — Step 6 push form
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — `detect-artifacts`, `worktree-create`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py` — inner lock handling
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/` — re-entrant merge mutex, release reporting
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — hold window
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` — `get_store_dir` anchoring
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/orchestrator_worktree.py` — #1652 shared ledger worktree
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — write-side anchor report
- OBSERVED: `test/plan-marshall/workflow-integration-git/`
- OBSERVED: `test/plan-marshall/manage-locks/`
- OBSERVED: `test/plan-marshall/plan-orchestrator/`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-22 (repo-wide), PLAN-24 / PLAN-20 (`phase-6-finalize/`). D4 overlaps #1652's store seam; read it first.
- Scope-bloat guard: 4 deliverables.

## Folded inbox material (same act)

- `plan-12-tool-triage-028.md` (finding): deliverable 1
- `plan-12-tool-triage-025.md` item 2 (finding) + `module-budget-campaign-completion-010` (archived; reclaimed from the PM-MCP carry-over under the 2026-09-27 directive): deliverable 2
- `plan-12-tool-triage-021.md` (finding): deliverable 3
- `plan-12-tool-triage-019.md` (finding): deliverable 4
- PLAN-10 claim (a second same-sender inbox write silently replaced a live message; `implement-opencode-enforcement-parity-003`): deliverable 4 is its mechanism (the allocator reads a cwd-relative ledger copy). Ownership moved here at cleanup 2026-09-29; the regression test covers it

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-26-git-and-worktree-contracts.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
