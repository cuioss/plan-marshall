# Branch Cleanup

Switch back to base branch and clean up after plan completion. Behavior adapts based on whether `default:create-pr` is in the finalize steps list.

## Prerequisites

- Branch name available from references context (`branch` field)
- The finalize `steps` list has been read from config (Step 2 of phase-6-finalize)
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

Check whether `default:create-pr` appears in the finalize `steps` list (already available from Step 2 config read):

- **PR mode** (`default:create-pr` IS in `steps`): Full PR merge workflow — merge PR, wait for CI, clean up branches.
- **Local-only mode** (`default:create-pr` is NOT in `steps`): PR creation and merging are handled outside this workflow. Only switch to base branch, pull latest, and remove the local feature branch.

---

## Execution: PR Mode

Applies when `default:create-pr` is present in the finalize steps list.

### Gather Context

Collect all information needed for the user confirmation dialog.

#### Get PR state

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Extract: `pr_number`, `pr_url`, `state` (open/merged/closed), `head_branch`, `base_branch`.

If no PR found (status: error) → skip cleanup, log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup skipped: no PR found for current branch"
```

#### Check for other open PRs using this branch

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr list --head {head_branch} --state open
```

Extract count and details of other open PRs (excluding the current PR).

### User Confirmation Gate

**MANDATORY**: Present all context and ask user before any destructive action.

Determine planned actions based on PR state:
- **If `state == open`**: Actions = merge PR (with --delete-branch), wait for CI, pull latest
- **If `state == merged`**: Actions = switch to base branch, pull latest, delete local branch

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
        {- Merge PR #{pr_number} with --delete-branch (if state == open)}
        {- Wait for CI checks to complete (if merging)}
        {- Switch to {base_branch} (if state == merged)}
        - Pull latest
        {- Delete local branch {head_branch} (if state == merged)}
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

### Switch to Base Branch and Pull (state-dependent)

All git calls in this section target the main checkout via `git -C {main_checkout}` because the worktree has been removed above.

**If `state == open`** (we just merged with `--delete-branch`):

The `--delete-branch` flag already deletes the remote branch, deletes the local branch, and switches the main checkout to the base branch. Only `git pull` is needed to fetch the merge commit.

```bash
git -C {main_checkout} pull
```

**If `state == merged`** (PR was already merged without `--delete-branch`):

The main checkout may still be on the feature branch and the local branch may still exist. Explicitly switch to base branch, pull, and clean up.

```bash
git -C {main_checkout} checkout {base_branch}
```

```bash
git -C {main_checkout} pull
```

```bash
git -C {main_checkout} branch -d {head_branch}
```

If `git branch -d` fails → log warning (branch may not exist locally):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup: local branch delete failed - {error} (may not exist)"
```

**Error handling** (both paths):

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

Applies when `default:create-pr` is NOT in the finalize steps list. PR creation and merging are handled outside this workflow.

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

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done
```
