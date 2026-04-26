---
name: default:branch-cleanup
description: Branch cleanup — adapts to PR mode or local-only based on create-pr step presence
order: 70
---

# Branch Cleanup

Pure executor for the `branch-cleanup` finalize step. Switches back to base branch and cleans up after plan completion. Behavior adapts based on whether `create-pr` is in `manifest.phase_6.steps`.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `branch-cleanup` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion and records `outcome=done`. Runtime no-op cases (no PR found, branch already in sync) are recorded with an honest `display_detail` rather than a "skip". The user-prompt branches (interactive `AskUserQuestion` decline paths) remain permitted by `validation.md` and are unchanged.

## Inputs

- Branch name available from references context (`branch` field)
- The manifest's `phase_6.steps` list has been read in SKILL.md Step 2 (used here for Mode Detection only)
- `{worktree_path}` and `{main_checkout}` have been resolved at finalize entry (see SKILL.md Step 0). All pre-removal git commands use `git -C {worktree_path}`. Post-removal git commands (after worktree is gone) use `git -C {main_checkout}`. All `ci` invocations pass `--project-dir {worktree_path}` while the worktree exists, and `--project-dir {main_checkout}` after removal.

## Constraints

- **Single-branch-only**: Only the plan's own feature branch (`{head_branch}` from references) may be deleted. Never delete any other local branches, regardless of their state or name.
- **No broad cleanup**: Never run bulk branch deletion commands such as `git -C {main_checkout} branch | grep -v {base_branch} | xargs git branch -d`, `git fetch --prune`, `git remote prune`, or similar patterns that affect multiple branches.
- **No improvisation**: Do not add git cleanup steps beyond what is explicitly documented in the execution sections below.
- **Worktree removal is non-force**: Never pass `--force` to `git worktree remove`. Only clean worktrees may be removed. If the worktree has uncommitted changes, abort cleanup and surface the error — the user may still want to salvage the work.
- **Failure leaves worktree in place**: On any plan abort or failure path, do NOT auto-remove the worktree. Worktree removal happens only during successful branch-cleanup.

## Worktree Awareness

If the plan was created with `use_worktree: true` (the default for `branch_strategy == feature`), the plan ran inside a git worktree at `{worktree_path}` rooted under `{main_checkout}/.claude/worktrees/{plan_id}/` — the canonical Claude Code worktree location inside the main git checkout. Both `{worktree_path}` and `{main_checkout}` were resolved at finalize entry (see SKILL.md Step 0) and are available throughout this workflow.

If `worktree_path` is absent (pre-worktree plan or `use_worktree == false`), substitute `{main_checkout}` in every `git -C {worktree_path}` command below — the plan ran directly against the main checkout, so all git work targets it.

Before any branch deletion, the worktree MUST be removed. The order is:

1. `{worktree_path}` is already in scope from SKILL.md Step 0.
2. If set: invoke `manage-worktree remove`. The script internally operates on `{main_checkout}`, so no `cd` is required.
3. Proceed with base branch checkout and local branch deletion — switching to `git -C {main_checkout}` for all post-removal git calls.

## Mode Detection

Check whether `create-pr` appears in `manifest.phase_6.steps` (already available from SKILL.md Step 2 manifest read):

- **PR mode** (`create-pr` IS in `manifest.phase_6.steps`): Full PR merge workflow — merge PR, wait for CI, clean up branches.
- **Local-only mode** (`create-pr` is NOT in `manifest.phase_6.steps`): PR creation and merging are handled outside this workflow. Only switch to base branch, pull latest, and remove the local feature branch.

---

## Execution: PR Mode

Applies when `create-pr` is present in `manifest.phase_6.steps`.

### Gather Context

Collect all information needed for the user confirmation dialog.

#### Get PR state

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Extract: `pr_number`, `pr_url`, `state` (open/merged/closed), `head_branch`, `base_branch`.

If no PR found (status: error) → there is nothing to clean up on the remote side. Record the no-op outcome and return via **Mark Step Complete** with:

```
--outcome done --display-detail "no PR — nothing to clean up"
```

Log the decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: no PR found for current branch — nothing to clean up"
```

#### Check for other open PRs using this branch

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr list --head {head_branch} --state open
```

Extract count and details of other open PRs (excluding the current PR).

### User Confirmation Gate

**MANDATORY**: Present all context and ask user before any destructive action.

Determine planned actions based on PR state. Local cleanup (switch to base branch, pull, delete local feature branch) is uniform across both paths; only the remote-side action differs (`--delete-branch` deletes the remote branch only when we merge this run):

- **If `state == open`**: Actions = merge PR (with --delete-branch, which deletes the remote branch), wait for CI, switch to base branch, pull latest, delete local feature branch
- **If `state == merged`**: Actions = switch to base branch, pull latest, delete local feature branch

```
AskUserQuestion:
  questions:
    - question: "Branch cleanup will perform the following actions. Proceed?"
      header: "Branch Cleanup"
      description: |
        **PR**: {pr_url} ({state})
        **Branch**: {head_branch} → {base_branch}
        **Other open PRs for this branch**: {count} {details if any}

        **Actions**:
        {- Merge PR #{pr_number} with --delete-branch (if state == open; deletes remote branch only)}
        {- Wait for CI checks to complete (if merging)}
        - Switch to {base_branch}
        - Pull latest
        - Delete local branch {head_branch}
      options:
        - label: "Yes, proceed"
          description: "Execute branch cleanup"
        - label: "No, skip"
          description: "Leave branch as-is"
      multiSelect: false
```

**If user selects "No, skip"**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup skipped: user declined"
```
→ Done, return.

### Safety Check: Other Open PRs

If other open PRs were found using this branch as head:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup aborted: {count} other open PR(s) use branch {head_branch}"
```

→ Abort cleanup. The user was already informed about these PRs in the confirmation dialog but confirmed anyway — however, deleting a branch with dependent PRs is too destructive. Log and skip.

### Read PR Merge Strategy

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field pr_merge_strategy --trace-plan-id {plan_id}
```

Extract `value` as `{pr_merge_strategy}` (default: `squash`). Valid values: `squash`, `merge`, `rebase`.

### Update Branch (if behind)

This step is a second-line safety net. The primary drift-sync now runs at the start of phase-5-execute when `rebase_on_execute_start=true` (the default), so by the time finalize runs the branch is typically already up to date with the base branch and this section is a no-op. When `rebase_on_execute_start=false`, `pr update-branch` remains the only sync point and this section is the sole mechanism that keeps a stale branch mergeable. The `pr update-branch` logic itself is unchanged.

**Only if `state == open`**: Before merging, check whether the PR branch is behind the base branch. The `merge_state` field from the earlier `pr view` output contains GitHub's `mergeStateStatus`. If the value is `behind`, the branch must be updated before a merge attempt — otherwise `pr merge` fails with 'head branch not up to date' and the auto-merge fallback stalls because GitHub will not auto-update the branch without explicit intervention.

**If `merge_state == behind`**:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr update-branch \
    --pr-number {pr_number}
```

If `update-branch` fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: pr update-branch failed - {error}"
```

After a successful branch update, wait for CI to complete on the updated branch before proceeding to merge:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} ci wait \
    --pr-number {pr_number}
```

**Bash tool timeout**: 1800000ms (30-minute safety net).

If CI fails after the branch update → log warning but continue to the merge attempt (the merge itself may still succeed if branch protection allows it):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup: CI failed after branch update — continuing with merge attempt"
```

Log the update:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: updated PR branch with base branch changes, CI passed"
```

**If `merge_state != behind`**: The branch is already up to date with the base branch — no update is required. Continue to the next sub-step ("Merge PR"). If this is the only branch-update outcome reached on this run (i.e. the run terminates here without performing a merge), record the no-op via **Mark Step Complete** with:

```
--outcome done --display-detail "branch not behind — already in sync"
```

Log the decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: branch already in sync with base — no update required"
```

### Merge PR (if not yet merged)

**Only if `state == open`**:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr merge \
    --pr-number {pr_number} --strategy {pr_merge_strategy} --delete-branch
```

If merge fails with branch protection error ('base branch policy prohibits the merge'), fall back to auto-merge:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr auto-merge \
    --pr-number {pr_number} --strategy {pr_merge_strategy}
```

Log the fallback:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: direct merge blocked by branch protection, enabled auto-merge"
```

If auto-merge also fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: PR merge failed - {error}"
```

### Wait for Merge CI

**Only if PR was just merged** (state was open):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} ci wait \
    --pr-number {pr_number}
```

**Bash tool timeout**: 1800000ms (30-minute safety net).

If CI fails → log warning but continue (PR is already merged):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup: post-merge CI failed — continuing with branch cleanup"
```

### Remove Worktree (if any)

**Only if `{worktree_path}` is set** (from the Worktree Awareness section).

The worktree must be removed BEFORE executing any post-removal git operations — `git worktree remove` refuses to operate on a worktree that is the current working directory of any shell, and the local branch cannot be deleted while still checked out in a worktree.

The `manage-worktree remove` script operates on the main checkout internally and does not rely on the caller's cwd:

```bash
python3 .plan/execute-script.py plan-marshall:manage-worktree:manage-worktree remove \
  --plan-id {plan_id}
```

Parse the TOON output:

- `status: success, action: removed` → continue. From this point forward, every git call MUST use `git -C {main_checkout}` and every `ci` invocation MUST use `--project-dir {main_checkout}`, because `{worktree_path}` no longer exists on disk.
- `status: success, action: noop` → worktree already gone (possibly manual cleanup), continue with the same `{main_checkout}` rule.
- `status: error, error: worktree_remove_failed` → ABORT cleanup. The worktree has uncommitted changes or is otherwise not clean. Log the error:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree remove failed at {worktree_path} - {error}. Salvage any uncommitted work and run 'git worktree remove --force {worktree_path}' manually."
```

Then return — do NOT proceed with branch deletion while the worktree still exists.

### Switch to Base Branch, Pull, and Delete Local Branch

All git calls in this section target the main checkout via `git -C {main_checkout}` because the worktree has been removed above.

**Uniform local cleanup (both `state == open` and `state == merged`)**:

The `--delete-branch` flag on `pr merge` deletes ONLY the remote branch (via the provider REST API). It does NOT touch the local clone — local branch deletion and base-branch checkout are always the workflow's responsibility and must run here regardless of the prior merge path. After worktree removal, the main checkout may still be on the feature branch and the local feature branch still exists, so switch to the base branch, pull the merge commit, and delete the local feature branch:

```bash
git -C {main_checkout} checkout {base_branch}
```

```bash
git -C {main_checkout} pull
```

```bash
git -C {main_checkout} branch -d {head_branch}
```

Notes on the two entry paths:

- **`state == open`** (we just merged this run with `--delete-branch`): the remote branch is already gone. The sequence above performs the local-only cleanup.
- **`state == merged`** (PR was already merged on a prior run, possibly without `--delete-branch`): the remote branch may still exist. The local cleanup sequence is identical; any leftover remote branch is left as-is and can be cleaned up by a separate workflow if desired.

If `git branch -d` fails → log warning (branch may not exist locally, e.g. another process already deleted it):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup: local branch delete failed - {error} (may not exist)"
```

**Error handling**:

If checkout or pull fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: {checkout|pull} failed - {error}"
```

### Log Completion (PR Mode)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup complete: merged PR #{pr_number}, pulled latest on {base_branch}"
```

---

## Execution: Local-Only Mode

Applies when `create-pr` is NOT in `manifest.phase_6.steps`. PR creation and merging are handled outside this workflow.

### Gather Context

Get branch information from references context (already available from Step 2 config read):
- `head_branch`: current feature branch (from `branch` field in references)
- `base_branch`: target branch (e.g., `main`)

### User Confirmation Gate

**MANDATORY**: Present context and ask user before any action.

```
AskUserQuestion:
  questions:
    - question: "PR creation and merge are handled outside this workflow. Ready to switch back to base branch and clean up?"
      header: "Branch Cleanup (local-only)"
      description: |
        **Branch**: {head_branch} → {base_branch}

        **Actions**:
        - Switch to {base_branch}
        - Pull latest changes
        - Delete local branch {head_branch}
      options:
        - label: "Yes, proceed"
          description: "Switch to base branch and clean up"
        - label: "No, skip"
          description: "Stay on current branch"
      multiSelect: false
```

**If user selects "No, skip"**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup skipped: user declined (local-only mode)"
```
→ Done, return.

### Remove Worktree (if any)

**Only if `{worktree_path}` is set** (from the Worktree Awareness section).

```bash
python3 .plan/execute-script.py plan-marshall:manage-worktree:manage-worktree remove \
  --plan-id {plan_id}
```

On `status: error`, log and abort as in PR mode. Do not proceed with branch deletion while the worktree remains. On success, all subsequent git calls MUST use `git -C {main_checkout}`.

### Switch to Base Branch, Pull, and Clean Up

```bash
git -C {main_checkout} checkout {base_branch}
```

```bash
git -C {main_checkout} pull
```

```bash
git -C {main_checkout} branch -d {head_branch}
```

If `git branch -d` fails → log warning (branch may not exist locally or has unmerged changes):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup: local branch delete failed - {error} (may not exist or has unmerged changes)"
```

**Error handling**:

If checkout or pull fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: {checkout|pull} failed - {error}"
```

### Log Completion (Local-Only Mode)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup complete (local-only): switched to {base_branch}, pulled latest"
```

---

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This MUST run while `status.json` is still under `.plan/plans/{plan_id}/` — if `default:archive-plan` appears earlier in the pipeline, ensure `mark-step-done` for `branch-cleanup` is emitted before that archive call rather than here. In the canonical order (`default:archive-plan` is last), this call runs here on the still-live plan.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the cleanup outcome. The payload differs by branch and must match the branch actually executed above:

**Branch A — PR mode (merge + cleanup)** (PR was merged, base branch pulled, feature branch deleted locally and on remote, worktree removed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "main pulled, branch deleted (local+remote), worktree removed"
```

**Branch B — local-only mode** (no PR was created; only local switch-to-base-branch was performed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "local-only: switched to main"
```

**Branch C — declined by user** (interactive prompt was rejected; cleanup was not performed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "declined by user"
```

**Branch D — no PR found** (PR mode, `pr view` returned status: error — there is no PR for the current branch, so there is nothing to clean up on the remote side):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "no PR — nothing to clean up"
```

**Branch E — branch already in sync** (PR mode, `merge_state != behind` was the terminal outcome — the branch is up to date with the base branch and no update was required; the run terminates here without merging):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "branch not behind — already in sync"
```
