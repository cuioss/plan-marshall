---
name: default:commit-push
description: Commit and push changes
order: 10
---

# Commit and Push

Pure executor for the `commit-push` finalize step. Commits all changes and pushes to remote.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `commit-push` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion and records `outcome=done` regardless of whether a commit was produced — the `display_detail` payload distinguishes the branches. The `commit_strategy == none` case is handled at composition time by the manifest's `commit_strategy_none` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`), so this step is never dispatched in that case.

## Inputs

- `commit_strategy` from phase-5-execute config (per_deliverable / per_plan). The `none` value is filtered out at manifest composition time and never reaches this executor.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST use `git -C {worktree_path}`.

### Freshness precondition

Before any of the Execution steps below run — and specifically BEFORE the `git status --porcelain` check, so the no-changes branch is never reached on a stale worktree — invoke the deterministic freshness gate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  pre-commit-verify-freshness --plan-id {plan_id}
```

Parse `status` from the returned TOON. The contract is **fail-closed**: only `status: fresh` permits the executor to proceed. Any other status halts `commit-push` immediately — record `outcome=failed` with a `display_detail` carrying the reason, the newest-mtime path, and the two timestamps so the orchestrator's recovery path has the structured signal it needs to dispatch a fresh `verify` run.

| `status` value | `commit-push` action |
|----------------|----------------------|
| `fresh` | Proceed to **Execution** below. |
| `stale` | Halt. Record `outcome=failed` with `display_detail` `"stale: newest={newest_mtime_path} t_build={t_build_iso} t_worktree={t_worktree_iso}"`. Do NOT push. |
| `undecidable` | Halt. Record `outcome=failed` with `display_detail` `"undecidable: {reason}"`. Do NOT push. |

The freshness gate is **complementary to**, NOT redundant with, the `pre-push-quality-gate` step. The quality-gate verifies *what the code is* (mypy + ruff + tests on the on-disk tree); freshness verifies *that the most recent `verify` run actually observed this version of the code*. A worktree that was modified after the most recent build-runner log line passes neither: the quality-gate may pass against the new tree if the orchestrator re-runs it, but the freshness gate fails because no `verify` log line post-dates the mutation. The two gates together close the gap that `loop-exit-guard` cannot close on its own — `loop-exit-guard` answers "is the queue empty?" while freshness answers "has a `verify` run actually observed this version of the code?"

The `--force` escape mirrors phase-5 Step 12a's escape — orchestrator-only, log-recorded, never auto-invoked. When the orchestrator drives finalize with `--force` AND the freshness gate returned a non-`fresh` status, the dispatcher records a `decision`-level WARNING (`(plan-marshall:phase-6-finalize:commit-push) Worktree-freshness precondition overridden via --force — proceeding with status={status}` — append `reason={reason}` only when status is `undecidable`; the `stale` branch does not emit a `reason` field) and then allows `commit-push` to proceed.

## Execution

### Strategy context (informational)

- **`per_deliverable`**: Some changes may already be committed per-deliverable during execute phase; commit only the remainder.
- **`per_plan`**: Commit all changes as a single commit (default behavior).

### Check for uncommitted changes

```bash
git -C {worktree_path} status --porcelain
```

If output is empty, the executor records the no-changes path and proceeds to **Mark Step Complete** (Branch B). Otherwise it continues with the load-and-commit path below.

### Load git_workflow skill

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-git"
```

```
Skill: plan-marshall:workflow-integration-git
```

Execute the git_workflow skill's **Workflow: Commit Changes** with:
- `message`: Generated from request.md summary
- `push`: true (always push in finalize)
- `worktree_path`: `{worktree_path}` resolved at finalize entry

## Capture HEAD and Mark Step Complete

`commit-push` is a member of `HEAD_DEPENDENT_STEPS` (see `phase-6-finalize/SKILL.md` § HEAD-dependent steps). A loop-back fix task may produce a fresh commit *after* a prior `commit-push` recorded `outcome=done` against the now-stale HEAD; without HEAD-comparison the dispatcher would skip `commit-push` on re-entry and leave the fix-task changes staged-but-uncommitted. To make the comparison meaningful, capture the live HEAD before `mark-step-done`:

**Dirty-tree re-entry**: the dispatcher's re-entry check for `commit-push` additionally consults `git status --porcelain` — see the `outcome == done AND head_at_completion == HEAD` (dirty) row of the HEAD-dependent re-entry table in `phase-6-finalize/SKILL.md` § HEAD-dependent steps. When a loop-back fix task mutates the worktree without producing a commit (e.g., the fix step ran but its commit step was deferred), the persisted `commit-push` record matches HEAD but the worktree is dirty — the dirty-tree row forces RE-FIRE so the staged changes are committed instead of silently skipping `commit-push`. `commit-push` is the **only** `HEAD_DEPENDENT_STEPS` member for which this dirty-tree branch is meaningful; the other four members (`pre-push-quality-gate`, `automated-review`, `sonar-roundtrip`, `ci-verify`) are read-only validators that do not produce commits and continue to follow the HEAD-only rows of the table.

```bash
git -C {worktree_path} rev-parse HEAD
```

Then record that this step ran on the live plan, forwarding the captured SHA via `--head-at-completion` so the dispatcher's HEAD-comparison logic can detect a loop-back fix-task commit on re-entry:

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the commit outcome. The payload differs by branch:

**Branch A — commit created**: `{commit_hash}` is the short 7-character hash of the commit produced by the `workflow-integration-git` call above (captured from its return payload); `{sha}` is the full SHA from `git rev-parse HEAD` (which equals the commit just created):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step commit-push --outcome done \
  --head-at-completion {sha} \
  --display-detail "-> {commit_hash}"
```

**Branch B — no uncommitted changes** (no-changes path from "Check for uncommitted changes" above — `git status --porcelain` returned empty). `{sha}` is the full SHA from `git rev-parse HEAD` (the unchanged prior HEAD):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step commit-push --outcome done \
  --head-at-completion {sha} \
  --display-detail "no changes"
```
