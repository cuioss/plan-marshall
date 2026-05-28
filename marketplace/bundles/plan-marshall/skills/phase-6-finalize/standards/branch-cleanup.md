---
name: default:branch-cleanup
description: Branch cleanup — adapts to PR mode or local-only based on create-pr step presence
order: 70
---

# Branch Cleanup

Pure executor for the `branch-cleanup` finalize step. Switches back to base branch and cleans up after plan completion. Behavior adapts based on whether `create-pr` is in `manifest.phase_6.steps`.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-status get-worktree-path` returning an empty `worktree_path`) — are documented inline in the step that issues them.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `branch-cleanup` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion and records `outcome=done`. Runtime no-op cases (no PR found, branch already in sync) are recorded with an honest `display_detail` rather than a "skip". The user-prompt branches (interactive `AskUserQuestion` decline paths) remain permitted by `validation.md` and are unchanged.

## Inputs

- Branch name available from references context (`branch` field)
- The manifest's `phase_6.steps` list has been read in SKILL.md Step 2 (used here for Mode Detection only)
- `{worktree_path}` and `{main_checkout}` have been resolved at finalize entry (see SKILL.md Step 0). Consolidated `workflow-integration-git` verbs (`force-push-with-lease`, `switch-and-pull`, `prune-local-and-remote-ref`) resolve the working tree internally via `--plan-id {plan_id}` — no path forwarding required at call sites. All `ci` invocations identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`; auto-resolution falls back to the main checkout when `use_worktree=false`, so `--plan-id` keeps working post-removal) or `--project-dir {worktree_path}` / `--project-dir {main_checkout}` (escape hatch / explicit override). The two flags are mutually exclusive.

## Constraints

- **Single-branch-only**: Only the plan's own feature branch (`{head_branch}` from references) may be deleted. Never delete any other local branches, regardless of their state or name.
- **No broad cleanup**: Never run operations that may affect refs not owned by the current plan, such as `git -C {main_checkout} branch | grep -v {base_branch} | xargs git branch -d`, `git fetch --prune`, `git remote prune`, or any similar pattern whose ref set is determined by external state rather than this plan. Targeted single-ref deletion of the plan's own remote-tracking ref (`refs/remotes/origin/{head_branch}`) is permitted and is prescribed in the PR-mode local cleanup section below — it deletes exactly the one ref this finalize run made stale by deleting the corresponding remote branch, and is provably scoped to the current plan.
- **No improvisation**: Do not add git cleanup steps beyond what is explicitly documented in the execution sections below.
- **Worktree removal is non-force**: Never pass `--force` to `git worktree remove`. Only clean worktrees may be removed. If the worktree has uncommitted changes, abort cleanup and surface the error — the user may still want to salvage the work.
- **Failure leaves worktree in place**: On any plan abort or failure path, do NOT auto-remove the worktree. Worktree removal happens only during successful branch-cleanup.
- **Confirmation gate is conditional on conflict severity**: The PR-mode `AskUserQuestion` confirmation gate is no longer mandatory on every `state == open` invocation. It is now driven by the **Conflict-Severity Classifier** section below, which dispatches `plan-marshall:workflow-integration-git:git-workflow baseline-reconcile --no-emit` to classify the rebase as `no_overlap`, `overlap_no_content_conflict`, or `overlap_with_content_conflict`. The classifier's safety properties: `baseline-reconcile --no-emit` is idempotent, performs only `fetch + diff + merge-tree` (with an internal `git merge` probe that is always aborted before any working-tree mutation persists — see the `auto_reconciled: false` downgrade path inside the script), and emits no Q-Gate findings under `--no-emit`. The auto-proceed threshold is tunable via `plan.phase-6-finalize.branch_cleanup_auto_proceed_threshold` (default `no_overlap_only`; opt-in `auto_resolvable`; opt-out `never`). All other safety properties (`--force-with-lease` only, worktree-first removal, targeted ref prune) remain unchanged on every code path.

## Worktree Awareness

Both `{worktree_path}` and `{main_checkout}` were resolved at finalize entry (see SKILL.md Step 0) and are available throughout this workflow. If `worktree_path` is absent (`use_worktree == false`), the consolidated verbs invoked below (`force-push-with-lease`, `switch-and-pull`, `prune-local-and-remote-ref`) resolve the correct working tree internally via `--plan-id {plan_id}` — no path substitution is required at the call site.

The cleanup ordering — **remove worktree first, then delete branch** — is enforced here at the call site because `git worktree remove` refuses to operate on a worktree that is the cwd of any shell, and the local branch cannot be deleted while still checked out in a worktree. The consolidated verbs are designed to be invoked after worktree removal (they target the main checkout); the `worktree-remove` verb handles the worktree removal step before these cleanup verbs run.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path convention, never-edit-main-checkout invariant, cleanup ordering rationale).

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
--outcome done --display-detail "no PR, nothing to clean up"
```

Log the decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: no PR found for current branch, nothing to clean up"
```

#### Check for other open PRs using this branch

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr list --head {head_branch} --state open
```

Extract count and details of other open PRs (excluding the current PR).

### Conflict-Severity Classifier

**Only runs when `state == open`** (when `state == merged` no rebase is planned and the classifier is skipped — proceed directly to the User Confirmation Gate, which the merged branch already treats as a routine local-cleanup confirmation).

This section dispatches the existing `baseline-reconcile` probe to classify the upcoming rebase against `origin/{base_branch}` and decide whether the User Confirmation Gate below must fire interactively or may be bypassed.

#### Read the auto-proceed threshold

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field branch_cleanup_auto_proceed_threshold --audit-plan-id {plan_id}
```

Extract `value` as `{threshold}`. Default: `no_overlap_only`. Accepted values:

- `no_overlap_only` — auto-proceed only when classifier returns `classification: no_overlap`.
- `auto_resolvable` — also auto-proceed when classifier returns `classification: overlap_no_content_conflict` AND `auto_reconciled: true`.
- `never` — always prompt the user; skip the classifier entirely. This is the legacy opt-out for users who prefer the unconditional gate.

#### Threshold-driven bypass (when `{threshold} == never`)

When `{threshold} == never`, skip the classifier dispatch entirely and force `{decision} = needs_user`. Log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: classifier bypassed (threshold=never), confirmation gate will fire"
```

Then proceed directly to the **User Confirmation Gate**.

#### Dispatch the classifier (when `{threshold}` != `never`)

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  baseline-reconcile --plan-id {plan_id} --no-emit
```

`--no-emit` suppresses Q-Gate finding emission (those are a phase-2-refine concern; branch-cleanup consumes the classification directly).

Parse the TOON return for fields `classification`, `auto_reconciled`, `conflict_count`, `conflicts[]`, `upstream_commit_count`.

If the script exits non-zero (per the **Exit-code convention** at the top of this document) → STOP and return an error TOON to the dispatcher carrying the stderr verbatim. Do NOT silently fall back to `needs_user` on classifier failure — a broken probe is a different signal than a real conflict and must surface as an error so the user can repair the environment.

#### Compute the gate decision

Apply the following rules in order; the first match wins:

- `classification == no_overlap` → `{decision} = auto_proceed` (regardless of threshold, except `never` which already short-circuited above).
- `classification == overlap_no_content_conflict` AND `auto_reconciled == true` AND `{threshold} == auto_resolvable` → `{decision} = auto_proceed`.
- `classification == overlap_no_content_conflict` AND (`auto_reconciled == false` OR `{threshold} == no_overlap_only`) → `{decision} = needs_user` (the script downgraded auto-resolution OR the threshold opts out even for auto-resolvable overlaps).
- `classification == overlap_with_content_conflict` → `{decision} = needs_user` (genuine conflict requiring human resolution).

#### Log the classifier decision

Emit both a `[STATUS]` work-log entry (for grep-ability during a run) and a `decision` log entry (so the retrospective phase can audit the call):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: classifier={classification}, auto_reconciled={auto_reconciled}, threshold={threshold}, decision={decision}, conflict_count={conflict_count}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup classifier: classification={classification}, auto_reconciled={auto_reconciled}, threshold={threshold}, decision={decision}, upstream_commits={upstream_commit_count}"
```

### User Confirmation Gate

The gate is **mandatory when `{decision} == needs_user`** (genuine conflict, classifier-bypassed threshold, or `state == merged` re-entry path) and **bypassed when `{decision} == auto_proceed`** (clean or auto-resolvable rebase under a permissive threshold).

#### Auto-proceed path (`{decision} == auto_proceed`)

When the classifier returned `{decision} == auto_proceed`, skip the `AskUserQuestion` block entirely and log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: auto-proceed (classification={classification}), confirmation gate bypassed"
```

Then proceed directly to **Safety Check: Other Open PRs**.

#### Interactive path (`{decision} == needs_user` OR `state == merged`)

Present all context and ask the user before any destructive action.

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
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup aborted: {count} other open PR(s) use branch {head_branch}"
```

→ Abort cleanup. The user was already informed about these PRs in the confirmation dialog but confirmed anyway — however, deleting a branch with dependent PRs is too destructive. Log and skip.

### Read PR Merge Strategy

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field pr_merge_strategy --audit-plan-id {plan_id}
```

Extract `value` as `{pr_merge_strategy}` (default: `squash`). Valid values: `squash`, `merge`, `rebase`.

### Rebase Branch onto Base

**Only if `state == open`**: Rebase the feature branch onto the latest base branch before merging so the merge lands as a linear-history append. This step is unconditional — it runs every time the PR is still open, regardless of whether the branch was already up to date. A uniform rebase guarantees the merged history is linear and that CI runs against the exact commits that will land on the base branch.

Dispatch the rebase via the structured `worktree-rebase-to` verb so the result is consumed as a TOON payload (rather than ad-hoc shell parsing):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  worktree-rebase-to --plan-id {plan_id} --base {base_branch}
```

Parse the returned TOON and branch on `status`:

- `status: success` (including `action: noop` when the branch was already at the base, or `action: rebased` when the rebase produced a new history) → continue to force-push-with-lease below.
- `status: conflict` → ABORT cleanup with a fatal error. The rebase is left in progress with conflict markers so the user can inspect or abort manually. The classifier's merge-tree probe is best-effort — overlapping renames and a few other rare cases produce a clean probe but a real-rebase conflict. Log the returned `conflicts[]` file list and the conflict state:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree-rebase-to onto {base_branch} produced conflicts in {conflicts} — resolve manually in the worktree (rebase is left in progress) and re-run finalize"
  ```

  Do NOT proceed with force-push, merge, or any cleanup. The conflicted rebase state is intentionally preserved so the user can resolve conflicts in the worktree and run `git rebase --continue` or `git rebase --abort` as appropriate.

- `status: error` → ABORT cleanup with a fatal error using the returned `error` and `message` fields:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree-rebase-to failed - {error}: {message}"
  ```

  Then return — do NOT proceed with force-push or merge.

On a successful rebase, push the rewritten history to the remote with a lease guard via the `force-push-with-lease` verb (see `workflow-integration-git` Canonical invocations → `force-push-with-lease`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  force-push-with-lease --plan-id {plan_id}
```

Parse the TOON output. On `status: rejected` (lease violation — remote moved since last fetch), ABORT cleanup and surface the error. On `status: error`, ABORT cleanup and return the error TOON verbatim to the dispatcher. On `status: success`, continue to the CI wait below.

After the force-push, wait for CI to complete on the rebased branch before proceeding to merge:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} ci wait \
    --pr-number {pr_number}
```

**Bash tool timeout**: 1800000ms (30-minute safety net).

If CI fails after the rebase → log warning but continue to the merge attempt (the merge itself may still succeed if branch protection allows it):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup: CI failed after rebase — continuing with merge attempt"
```

Log the rebase:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: rebased onto origin/{base_branch}, force-pushed with lease, CI passed"
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
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup: post-merge CI failed — continuing with branch cleanup"
```

### Remove Worktree (if any)

**Only if `{worktree_path}` is set** (from the Worktree Awareness section).

The worktree must be removed BEFORE executing any post-removal git operations — `git worktree remove` refuses to operate on a worktree that is the current working directory of any shell, and the local branch cannot be deleted while still checked out in a worktree.

The `worktree-remove` verb operates on the main checkout internally and does not rely on the caller's cwd (see `workflow-integration-git` Canonical invocations → `worktree-remove`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove \
  --plan-id {plan_id}
```

Parse the TOON output:

- `status: success, action: removed` → continue. From this point forward, the consolidated verbs (`switch-and-pull`, `prune-local-and-remote-ref`) and every `ci` invocation MUST use `--project-dir {main_checkout}`, because `{worktree_path}` no longer exists on disk.
- `status: success, action: noop` → worktree already gone (possibly manual cleanup), continue with the same `{main_checkout}` rule for `ci` invocations.
- `status: error, error: worktree_remove_failed` → ABORT cleanup. The worktree has uncommitted changes or is otherwise not clean. Log the error:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree remove failed at {worktree_path} - {error}. Salvage any uncommitted work and run 'git worktree remove --force {worktree_path}' manually."
```

Then return — do NOT proceed with branch deletion while the worktree still exists.

### Switch to Base Branch, Pull, and Delete Local Branch

All git operations in this section target the main checkout because the worktree has been removed above.

**Uniform local cleanup (both `state == open` and `state == merged`)**:

The `--delete-branch` flag on `pr merge` deletes ONLY the remote branch (via the provider REST API). It does NOT touch the local clone — local branch deletion and base-branch checkout are always the workflow's responsibility and must run here regardless of the prior merge path. After worktree removal, the main checkout may still be on the feature branch and the local feature branch still exists.

Switch to the base branch and pull the merge commit via `switch-and-pull` (see `workflow-integration-git` Canonical invocations → `switch-and-pull`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  switch-and-pull --plan-id {plan_id} --base {base_branch}
```

Parse the TOON output:

- `status: success` → continue to local branch deletion below.
- `status: error, error_type: branch_not_found` → base branch not found on remote; log error and abort.
- `status: error, error_type: merge_conflict` → checkout failed due to uncommitted changes on the main checkout; log error and abort.
- Any other `status: error` → log error and abort.

**Error handling** (checkout or pull failures):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: switch-and-pull failed - {error_type}: {message}"
```

Delete the local feature branch and prune the now-stale remote-tracking ref via `prune-local-and-remote-ref` (see `workflow-integration-git` Canonical invocations → `prune-local-and-remote-ref`). The verb encapsulates the `show-ref` guard and `update-ref -d` so the remote-tracking ref is only deleted when it exists:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  prune-local-and-remote-ref --plan-id {plan_id}
```

Parse the TOON output:

- `status: success` → both local branch and remote-tracking ref deleted.
- `status: partial` → local branch deleted; remote-tracking ref was already absent (graceful no-op — expected on `state == merged` re-entry or external prune).
- `status: error, error_type: branch_delete_failed` → log warning and continue (branch may not exist locally, e.g. another process already deleted it).
- `status: error, error_type: unexpected_ref_error` → log warning and continue (ref-db lock contention; cleanup gap is detection-friendly, not a hard blocker).

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup: prune-local-and-remote-ref - {error_type}: {message}"
```

Notes on the two entry paths:

- **`state == open`** (we just merged this run with `--delete-branch`): the remote branch is already gone. `prune-local-and-remote-ref` deletes the local branch AND prunes the now-stale remote-tracking ref.
- **`state == merged`** (PR was already merged on a prior run, possibly without `--delete-branch`): the remote branch may still exist. `prune-local-and-remote-ref` deletes the local branch; the remote-tracking ref may or may not be present — the internal `show-ref` guard produces a `status: partial` no-op when the tracking ref is already absent on this re-entry path.

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
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove \
  --plan-id {plan_id}
```

On `status: error`, log and abort as in PR mode. Do not proceed with branch deletion while the worktree remains. On success, the consolidated verbs (`switch-and-pull`, `prune-local-and-remote-ref`) and any `ci` invocations MUST use `--project-dir {main_checkout}`.

### Switch to Base Branch, Pull, and Clean Up

Switch to the base branch and pull via `switch-and-pull` (see `workflow-integration-git` Canonical invocations → `switch-and-pull`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  switch-and-pull --plan-id {plan_id} --base {base_branch}
```

Parse the TOON output:

- `status: success` → continue to local branch deletion below.
- Any `status: error` → log error and abort.

**Error handling** (checkout or pull failures):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: switch-and-pull failed - {error_type}: {message}"
```

Delete the local feature branch only (no remote-tracking ref deletion in local-only mode — the remote branch lifecycle is managed outside this workflow) via `prune-local-and-remote-ref` with `--mode local_only` (see `workflow-integration-git` Canonical invocations → `prune-local-and-remote-ref`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  prune-local-and-remote-ref --plan-id {plan_id} --mode local_only
```

If `status: error` → log warning and continue (branch may not exist locally or has unmerged changes):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup: local branch delete failed - {error_type}: {message} (may not exist or has unmerged changes)"
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

**Branch A — PR mode (rebase + merge + cleanup)** (PR was rebased onto base, merged, base branch pulled, feature branch deleted locally and on remote, worktree removed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "rebased onto base, merged, cleanup complete"
```

**Branch B — local-only mode** (no PR was created; only local switch-to-base-branch was performed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "local-only: switched to main"
```

**Branch C — declined by user** (interactive prompt was rejected; cleanup was not performed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "declined by user"
```

**Branch D — no PR found** (PR mode, `pr view` returned status: error — there is no PR for the current branch, so there is nothing to clean up on the remote side):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --display-detail "no PR, nothing to clean up"
```
