---
name: default:commit-push
description: Commit and push changes
order: 10
---

# Commit and Push

Pure executor for the `commit-push` finalize step. Commits all changes and pushes to remote.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `commit-push` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion and records `outcome=done` regardless of whether a commit was produced — the `display_detail` payload distinguishes the branches. The `commit_strategy == none` case is handled at composition time by the manifest's `commit_strategy_none` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`), so this step is never dispatched in that case.

## Inputs

- `commit_strategy` from phase-5-execute config (per_deliverable / per_plan). The `none` value is filtered out at manifest composition time and never reaches this executor.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST use `git -C {worktree_path}`.

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

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the commit outcome. The payload differs by branch:

**Branch A — commit created**: `{commit_hash}` is the short 7-character hash of the commit produced by the `workflow-integration-git` call above (captured from its return payload):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step commit-push --outcome done \
  --display-detail "-> {commit_hash}"
```

**Branch B — no uncommitted changes** (no-changes path from "Check for uncommitted changes" above — `git status --porcelain` returned empty):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step commit-push --outcome done \
  --display-detail "no changes"
```
