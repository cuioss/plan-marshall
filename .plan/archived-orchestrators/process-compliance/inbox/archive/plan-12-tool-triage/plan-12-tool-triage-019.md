envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:57Z

# `orchestrator inbox write` from a phase-5+ cwd-pinned worktree writes into the worktree's copy of the epic store

## Observed

After phase-5 move-in the orchestrator's cwd is pinned to `.plan/local/worktrees/plan-12-tool-triage`
(ADR-002). Two `orchestrator inbox write --slug process-compliance ...` calls issued from there resolved
the git-tracked `.plan/orchestrator/` store of the WORKTREE (checked out at the plan's base commit), not
main's live store:

- they wrote `.plan/local/worktrees/plan-12-tool-triage/.plan/orchestrator/process-compliance/inbox/plan-12-tool-triage-006.md` and `-007.md`;
- main's live inbox already held DIFFERENT messages `plan-12-tool-triage-006..008.md` (filed earlier from
  the main checkout), so the sequence allocator — reading only the worktree copy — re-issued taken numbers;
- the files now sit untracked in the worktree and ride the plan's PR, colliding by name with main's files
  at merge and duplicating "one message per emitted item".

The verb reported `status: success` with a `path` under the worktree; nothing flagged that the write
landed in a non-live copy of the ledger. The operator chose to leave the two files in the PR.

## Why it matters

Every plan that files inbox messages during phase 5/6 (including finalize's `emit-landing`, if it
resolves the same way) risks writing to a stale ledger copy and colliding sequence numbers with the
live one. The collision is invisible until merge.

## Suggested fix

Resolve the orchestrator store main-anchored (like the lessons corpus `store handle`), never
cwd-relative, and make `inbox write` refuse — or report the anchor — when the resolved store is inside
a plan worktree.
