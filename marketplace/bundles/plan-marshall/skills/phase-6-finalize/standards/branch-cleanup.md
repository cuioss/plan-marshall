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
- **Confirmation gate is conditional on conflict severity**: The PR-mode `AskUserQuestion` confirmation gate is no longer mandatory on every `state == open` invocation. It is now driven by the **Conflict-Severity Classifier** section below, which dispatches `plan-marshall:workflow-integration-git:git-workflow baseline-reconcile --no-emit` to classify the rebase as `no_overlap`, `overlap_no_content_conflict`, or `overlap_with_content_conflict`. The classifier's safety properties: `baseline-reconcile --no-emit` is idempotent, performs only `fetch + diff + merge-tree` (with an internal `git merge` probe that is always aborted before any working-tree mutation persists — see the `auto_reconciled: false` downgrade path inside the script), and emits no Q-Gate findings under `--no-emit`. The auto-proceed threshold is tunable via `plan.phase-6-finalize.auto_rebase_threshold`, which is schema-registered in `DEFAULT_PLAN_FINALIZE` (`_config_defaults.py`) with default `no_overlap_only` (opt-in `auto_resolvable`; opt-out `never`). All other safety properties (`--force-with-lease` only, worktree-first removal, targeted ref prune) remain unchanged on every code path.

## Worktree Awareness

Both `{worktree_path}` and `{main_checkout}` were resolved at finalize entry (see SKILL.md Step 0) and are available throughout this workflow. If `worktree_path` is absent (`use_worktree == false`), the consolidated verbs invoked below (`force-push-with-lease`, `switch-and-pull`, `prune-local-and-remote-ref`) resolve the correct working tree internally via `--plan-id {plan_id}` — no path substitution is required at the call site.

The cleanup ordering — **move-back first (via `integrate_into_main`), then remove worktree, then delete branch** — is enforced by the surrounding finalize wiring and here at the call site. The atomic move-back script `plan-marshall:workflow-integration-git:integrate_into_main` runs in `phase-6-finalize/SKILL.md` Step 0 § move-back, AFTER the PR merge and BEFORE this `branch-cleanup` step: it acquires the merge lock, folds the plan's own global logs into the plan dir, moves the plan directory back from the worktree to main, and releases the lock — all while the worktree is STILL PRESENT. The worktree MUST be retained until that move-back completes, because the plan's authoritative state lives in the worktree until then; removing it first would strand the plan-state copy. `branch-cleanup` therefore removes the worktree only AFTER `integrate_into_main` has returned.

Worktree removal is sequenced before branch deletion here at the call site because `git worktree remove` refuses to operate on a worktree that is the cwd of any shell, and the local branch cannot be deleted while still checked out in a worktree. The consolidated verbs are designed to be invoked after worktree removal (they target the main checkout); the `worktree-remove` verb handles the worktree removal step before these cleanup verbs run.

**Executor regeneration is owned by neither `integrate_into_main` nor this step.** `integrate_into_main` performs the plan-dir move-back only and does NOT regenerate the executor. On-main executor regeneration is performed by the project-level `project:finalize-step-sync-plugin-cache` step (order 85) after the cache sync, in both worktree and no-worktree finalize flows, because the executor is per-tree derived state (generated, never file-moved onto main) per ADR-002.

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
  plan phase-6-finalize get --field auto_rebase_threshold --audit-plan-id {plan_id}
```

Extract `value` as `{threshold}`. Default: `no_overlap_only`. Accepted values:

- `no_overlap_only` — auto-proceed only when classifier returns `classification: no_overlap`.
- `auto_resolvable` — also auto-proceed when classifier returns `classification: overlap_no_content_conflict` AND `auto_reconciled: true`.
- `never` — always prompt the user; skip the classifier entirely. This is the legacy opt-out for users who prefer the unconditional gate.

The field's lifecycle: the default lives in `DEFAULT_PLAN_FINALIZE` (`_config_defaults.py`), is read at runtime via `manage-config plan phase-6-finalize get --field auto_rebase_threshold`, and is operator-visible in `.plan/marshal.json` (seeded by `manage-config init` / `sync-defaults`). This document is the authoritative description of the threshold's effect on the gate, not its storage — the schema row owns the default.

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

### Pre-Rebase Confirmation Gate

The pre-rebase gate decides whether the upcoming `worktree-rebase-to → force-push-with-lease → ci wait` sequence fires silently or prompts the operator for confirmation. It is driven by the `auto_rebase_threshold` knob (read above in the **Conflict-Severity Classifier** section) and the classifier's `{decision}`.

The merge step itself is governed by a separate gate (see **Pre-Merge Confirmation Gate** below) routed by the orthogonal `auto_merge_after_ci` knob. The two gates are independent: a permissive `auto_rebase_threshold` does NOT imply a permissive merge gate, and vice versa.

The gate is **mandatory when `{decision} == needs_user`** (genuine conflict, classifier-bypassed threshold, or `state == merged` re-entry path where there is no rebase to perform but the operator is asked to confirm local cleanup) and **bypassed when `{decision} == auto_proceed`** (clean or auto-resolvable rebase under a permissive threshold).

#### Auto-proceed path (`{decision} == auto_proceed`)

When the classifier returned `{decision} == auto_proceed`, skip the `AskUserQuestion` block entirely and log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: pre-rebase auto-proceed (classification={classification}), pre-rebase confirmation gate bypassed"
```

Then proceed directly to **Safety Check: Other Open PRs**.

#### Interactive path (`{decision} == needs_user` OR `state == merged`)

Present the **rebase-and-cleanup** context and ask the user before any destructive action. The merge action is intentionally absent from this prompt — it is gated separately below after CI passes on the rebased branch.

Determine planned actions based on PR state. Local cleanup (switch to base branch, pull, delete local feature branch) is uniform across both paths; only the remote-side action differs (the merge itself is deferred to the pre-merge gate when `state == open`):

- **If `state == open`**: Actions = rebase onto base, force-push with lease, wait for CI; the post-CI merge is confirmed separately at the pre-merge gate. Local cleanup runs after the merge gate resolves.
- **If `state == merged`**: Actions = switch to base branch, pull latest, delete local feature branch. No rebase or merge is planned; the pre-merge gate is skipped on this path.

```
AskUserQuestion:
  questions:
    - question: "Rebase the feature branch onto {base_branch} and run CI? (Merge will be confirmed separately after CI passes.)"
      header: "Branch Cleanup — Pre-rebase"
      description: |
        **PR**: {pr_url} ({state})
        **Branch**: {head_branch} → {base_branch}
        **Other open PRs for this branch**: {count} {details if any}

        **Actions** (this gate covers rebase + CI wait only; merge is gated separately):
        {- Rebase {head_branch} onto origin/{base_branch} (if state == open)}
        {- Force-push the rebased branch with --force-with-lease (if state == open)}
        {- Wait for CI checks to complete on the rebased branch (if state == open)}
        - Switch to {base_branch}
        - Pull latest
        - Delete local branch {head_branch}
      options:
        - label: "Yes, proceed"
          description: "Execute rebase + CI wait; merge will be confirmed separately"
        - label: "No, skip"
          description: "Leave branch as-is"
      multiSelect: false
```

**If user selects "No, skip"**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup skipped: user declined at pre-rebase gate"
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
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} checks wait \
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

### Pre-Merge Confirmation Gate

**Only if `state == open`** (when `state == merged` there is nothing to merge — skip this entire section and proceed to **Wait for Merge CI**, which itself is a no-op on the `state == merged` path).

The pre-merge gate fires after `ci wait` returns green on the rebased branch and BEFORE the `pr merge --delete-branch` call below. It is suppressed only when `auto_merge_after_ci == true`. The gate is orthogonal to the pre-rebase gate above — the operator may have auto-proceeded through rebase but still be asked to confirm the irreversible merge step.

#### Read the auto-merge gate

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  ceremony-policy get --field automation.auto_merge_after_ci
```

Extract `value` as `{auto_merge_after_ci}` (default: `true`). Valid values: `true`, `false`. The default is now `true` — auto-merge after CI, serialized across plans via the cross-plan merge-lock so concurrent plans can never race on the merge-to-main critical section. `false` is the explicit interactive opt-out (prompt the operator before merging). The read mechanism is a plain boolean — no tri-state, no back-compat normalization.

#### Re-run the classifier against the current head

The pre-rebase classifier observation can be stale by the time CI completes (other commits may have landed on `origin/{base_branch}` during the wait). Re-dispatch the classifier so the gate is anchored to the *current* head SHA on the rebased branch:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  baseline-reconcile --plan-id {plan_id} --no-emit
```

Parse the TOON return for refreshed `classification`, `auto_reconciled`, `conflict_count`, `upstream_commit_count` values. These values are surfaced to the operator in the prompt below so the merge decision is anchored to the post-rebase reality, not the pre-rebase snapshot.

If the script exits non-zero, STOP and return an error TOON to the dispatcher carrying the stderr verbatim. Do NOT silently fall back to `needs_user` on classifier failure — a broken probe is a different signal than a real conflict.

#### Auto-merge bypass (`auto_merge_after_ci == true`)

When `{auto_merge_after_ci} == true`, skip the `AskUserQuestion` block entirely and log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: pre-merge auto-proceed (auto_merge_after_ci=true), pre-merge confirmation gate bypassed"
```

##### Acquire the cross-plan merge-lock (auto path only)

The auto path is ALWAYS lock-coordinated: because auto-merge serializes through the cross-plan merge-lock, concurrent plans can never race on the merge-to-main critical section, which is precisely what makes auto-merge a safe default. BEFORE the merge, acquire the lock. `acquire` is BLOCKING — the 5-minute poll loop lives inside the Python script (`time.sleep`), NOT a Bash loop — so call it with a Bash tool timeout of ~360000ms (6 minutes) to cover the 5-minute internal poll plus margin:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-lock acquire \
  --plan-id {plan_id}
```

**Bash tool timeout**: 360000ms (6-minute safety net for the 5-minute internal poll window).

Parse the TOON output:

- `status: acquired` → this plan holds the merge-lock. Proceed to **Merge PR (if not yet merged)** below.
- `status: blocked` → the poll window elapsed while another plan held the lock. The script returns `blocking_plan_id` and does NOT issue `AskUserQuestion` — the orchestrator owns the escalation. Issue:

  ```
  AskUserQuestion:
    questions:
      - question: "Another plan ({blocking_plan_id}) is holding the merge-lock. Wait and retry, or skip this merge?"
        header: "Branch Cleanup — Merge-lock contention"
        description: |
          **Blocking plan**: {blocking_plan_id}
          **This plan**: {plan_id}

          The cross-plan merge-lock serializes the merge-to-main critical
          section. {blocking_plan_id} acquired it first and has not yet
          released. The 5-minute poll window elapsed without the lock
          freeing.
        options:
          - label: "Wait and retry"
            description: "Re-run merge-lock acquire (another 5-minute poll window)"
          - label: "Skip merge"
            description: "Defer merge; exit cleanly so finalize can be re-entered later"
        multiSelect: false
  ```

  On **Wait and retry**, re-run the `merge-lock acquire` call above. On **Skip merge**, set `{merge_consent} = deferred` and follow the same skip path as the interactive "No, skip merge" branch.

Then proceed directly to **Merge PR (if not yet merged)** below. The `{merge_consent} = explicit_yes` flag is set so the auto-merge fallback path remains active on a branch-protection error.

> **Sync note**: the `merge-lock` verb is a new `manage-status` subcommand. After this plan merges, the `finalize-step-sync-plugin-cache` step syncs the plugin cache and regenerates the executor against main (after the cache sync), so the new notation resolves.

#### Interactive merge prompt (`auto_merge_after_ci == false`)

Present the merge context and ask the operator to confirm. The prompt is anchored to the current (post-rebase, post-CI) head SHA via the freshly-re-run classifier above:

```
AskUserQuestion:
  questions:
    - question: "CI passed on the rebased branch. Merge PR #{pr_number} now?"
      header: "Branch Cleanup — Pre-merge"
      description: |
        **PR**: {pr_url} (state: open)
        **Branch**: {head_branch} → {base_branch}
        **Merge strategy**: {pr_merge_strategy}
        **Current classifier** (post-rebase): classification={classification}, auto_reconciled={auto_reconciled}, upstream_commits={upstream_commit_count}

        **Actions on "Yes, merge"**:
        - `pr merge --pr-number {pr_number} --strategy {pr_merge_strategy} --delete-branch`
        - On branch-protection error, fall back to `pr auto-merge` with the same strategy
        - Switch to {base_branch}, pull latest, delete local branch {head_branch}

        **Actions on "No, skip merge"**:
        - Workflow exits cleanly; the rebased branch is left in place
        - Re-enter finalize later to merge (state == merged short-circuits this prompt if you merged manually)
      options:
        - label: "Yes, merge"
          description: "Run pr merge --delete-branch with auto-merge fallback on branch protection"
        - label: "No, skip merge"
          description: "Defer merge; exit cleanly so finalize can be re-entered later"
      multiSelect: false
```

**If user selects "No, skip merge"**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: pre-merge deferred at user request — re-enter finalize later to merge"
```

Set `{merge_consent} = deferred`. Skip the **Merge PR**, **Wait for Merge CI**, **Remove Worktree**, and **Switch to Base Branch** sections entirely; the rebased branch is left in place with no further mutation. Emit the `mark-step-done` payload below using **Branch C — declined by user** (deferral is the same shape from the workflow's point of view: cleanup was not completed this run, re-entry is expected) and return.

**If user selects "Yes, merge"**: Set `{merge_consent} = explicit_yes` and proceed to **Merge PR (if not yet merged)** below. The auto-merge fallback path remains active on a branch-protection error (explicit consent was given for the merge action; the fallback is part of the same merge intent).

### Merge PR (if not yet merged)

**Only if `state == open` AND the pre-merge gate above resolved to `{merge_consent} == explicit_yes`** (the `auto_merge_after_ci == true` bypass also sets `{merge_consent} = explicit_yes`):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr merge \
    --pr-number {pr_number} --strategy {pr_merge_strategy} --delete-branch
```

If merge fails with branch protection error ('base branch policy prohibits the merge'), fall back to auto-merge — the operator's "Yes, merge" answer (or the `auto_merge_after_ci == true` bypass) is the consent for both the direct merge and its auto-merge fallback:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr auto-merge \
    --pr-number {pr_number} --strategy {pr_merge_strategy}
```

Log the fallback:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: direct merge blocked by branch protection, enabled auto-merge (merge_consent=explicit_yes)"
```

If auto-merge also fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: PR merge failed - {error}"
```

### Wait for Merge CI

**Only if PR was just merged** (state was open):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} checks wait \
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

#### Release the cross-plan merge-lock (auto path only)

**Only if the merge-lock was acquired on the auto path** (`{auto_merge_after_ci} == true` and `merge-lock acquire` returned `status: acquired`). The release fires AFTER `switch-and-pull` has pulled the merge commit into the base branch — the merge-to-main critical section is now complete, so the marker can be freed for the next plan:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-lock release \
  --plan-id {plan_id}
```

`release` is idempotent (`released: false` when no marker was present), so a re-entry that already released the lock is a safe no-op. The `false`/prompt opt-out path never acquires the lock and therefore never releases it.

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
- `base_branch`: target branch (consumer-configured via `project.default_base_branch`; per-plan override via `references.base_branch`)

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
