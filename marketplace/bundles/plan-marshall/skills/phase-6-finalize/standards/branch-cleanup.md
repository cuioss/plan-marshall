---
lane:
  class: core
  cost_size: XS
name: default:branch-cleanup
description: Branch cleanup — adapts to PR mode or local-only based on create-pr step presence
order: 70
advances_main_via_rebase: true
default_on: true
presets:
  - local
  - standard
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
configurable:
  - key: pr_merge_strategy
    default: squash
    description: Merge strategy (squash|merge|rebase) used when merging the plan's PR.
  - key: final_merge_without_asking
    default: false
    description: Gate the post-CI auto-merge — false prompts before merging; true merges automatically once CI is green.
  - key: auto_rebase_threshold
    default: no_overlap_only
    description: Gate the pre-rebase auto-proceed decision — no_overlap_only permits auto-rebase only when the rebase would touch a disjoint file set; any overlap defers to the operator.
  - key: merge_queue_wait_budget_seconds
    default: 1800
    description: Bound (in seconds, ~30 min) the FIFO merge-queue poll loop — caps how long branch-cleanup waits for its turn at the head of the merge queue before falling back to the last-resort AskUserQuestion.
  - key: merge_hold_window
    default: full_window_release_at_waits
    description: Hold-scope mode for the widened merge mutex. full_window_release_at_waits acquires the lock before the pre-merge force-push and holds it through the CI wait, merge, and merge-CI-wait, releasing + FIFO-re-enqueueing at every operator-wait / loop-back boundary and re-validating after re-acquire. pre_merge_only is the legacy narrow hold (acquire only at the Pre-Merge Gate).
  - key: merge_hold_budget_seconds
    default: 3600
    description: Bound (in seconds, ~60 min) the maximum wall-clock the widened merge mutex may be held across the staleness window. When the elapsed-since-acquire exceeds this budget during a legitimate wait, the orchestrator releases + FIFO-re-enqueues the lock and escalates via AskUserQuestion, so a live-but-slow holder can never monopolize the merge critical section.
  - key: use_merge_queue
    default: false
    description: Opt-in complement that routes the final merge through the platform merge queue (GitHub merge queue / GitLab merge train) instead of the immediate pr safe-merge, so the platform re-tests-and-merges against the latest base and serializes a truly-external commit the session-scoped mutex cannot. Default false because engaging the platform merge queue is a repo-level branch-protection change affecting ALL PR workflows. Composes with the widened mutex — the mutex guards the pre-enqueue rebase/force-push window, the queue serializes the merge itself.
  - key: admin_merge_on_stuck_state
    default: false
    description: Gate the GitHub-only stuck-state `--admin` fallback inside `ci pr safe-merge` — false refuses the admin merge and surfaces the stuck PR to the operator; true permits `gh pr merge --admin` only when the PR stays `mergeable_state: blocked` past the poll timeout AND every active ruleset requirement is provably met. Orthogonal to `final_merge_without_asking` (which gates whether the merge is attempted at all).
  - key: pre_merge_comment_barrier
    default: fail_into_loopback
    description: Gate the fail-closed pre-merge comment-completeness barrier that re-fetches bot comments immediately before merge/enqueue and blocks when any pr-comment finding is still pending. fail_into_loopback (default) loops the plan back into the automatic-review triage pipeline (records the branch-cleanup step loop_back, releases the merge mutex if held, re-enters phase-6-finalize); ask fires an inline AskUserQuestion offering re-triage / merge-anyway-with-recorded-reason / defer. The clean path (zero new pending findings) proceeds straight to merge.
---

# Branch Cleanup

Pure executor for the `branch-cleanup` finalize step. Switches back to base branch and cleans up after plan completion. Behavior adapts based on whether `create-pr` is in `manifest.phase_6.steps`.

This step's late pre-merge rebase (`order: 70`, onto the newly-fetched `origin/{base_branch}` tip) advances `main` when it is a non-noop, so the step is declared `advances_main_via_rebase: true` in its frontmatter — the fact that arms the dispatcher's **post-rebase step-doc re-resolution contract** (see `phase-6-finalize/SKILL.md` Step 3): every subsequent step's authoritative doc is re-read from the just-rebased `{worktree_path}` at dispatch time rather than trusting the session-start-loaded copy.

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
- **Confirmation gate is conditional on conflict severity**: The PR-mode `AskUserQuestion` confirmation gate is no longer mandatory on every `state == open` invocation. It is now driven by the **Conflict-Severity Classifier** section below, which dispatches `plan-marshall:workflow-integration-git:git-workflow baseline-reconcile --no-emit` to classify the rebase as `no_overlap`, `overlap_no_content_conflict`, or `overlap_with_content_conflict`. The classifier's safety properties: `baseline-reconcile --no-emit` is idempotent, performs only `fetch + diff + merge-tree` (with an internal `git merge` probe that is always aborted before any working-tree mutation persists — see the `auto_reconciled: false` downgrade path inside the script), and emits no Q-Gate findings under `--no-emit`. The auto-proceed threshold is tunable via the `auto_rebase_threshold` param of the `default:branch-cleanup` step (read from the plan-local manifest step-params snapshot), declared in this step's `configurable:` frontmatter with default `no_overlap_only` (opt-in `auto_resolvable`; opt-out `never`) and resolved by the `plan-marshall:extension-api:configurable_contract` parser. All other safety properties (`--force-with-lease` only, worktree-first removal, targeted ref prune) remain unchanged on every code path.

## Worktree Awareness

Both `{worktree_path}` and `{main_checkout}` were resolved at finalize entry (see SKILL.md Step 0) and are available throughout this workflow. If `worktree_path` is absent (`use_worktree == false`), the consolidated verbs invoked below (`force-push-with-lease`, `switch-and-pull`, `prune-local-and-remote-ref`) resolve the correct working tree internally via `--plan-id {plan_id}` — no path substitution is required at the call site.

The cleanup ordering — **move-back first (via `integrate_into_main`), then remove worktree, then delete branch** — is now **script-enforced**, not just wired: `worktree-remove` itself refuses with `error: plan_dir_not_moved_back` until `integrate_into_main` has landed the plan directory back on the main checkout, and the refusal is NOT overridable by `--force` (`--force` keeps its dirty-tree meaning only). On that refusal, surface the error and run the move-back — never force. The atomic move-back script `plan-marshall:workflow-integration-git:integrate_into_main` runs in `phase-6-finalize/SKILL.md` Step 0 § move-back, AFTER the PR merge and BEFORE this `branch-cleanup` step: it acquires the merge lock, folds the plan's own global logs into the plan dir, moves the plan directory back from the worktree to main, and releases the lock — all while the worktree is STILL PRESENT. The worktree MUST be retained until that move-back completes, because the plan's authoritative state lives in the worktree until then; removing it first would strand the plan-state copy. `branch-cleanup` therefore removes the worktree only AFTER `integrate_into_main` has returned.

Worktree removal is sequenced before branch deletion here at the call site because `git worktree remove` refuses to operate on a worktree that is the cwd of any shell, and the local branch cannot be deleted while still checked out in a worktree. The consolidated verbs are designed to be invoked after worktree removal (they target the main checkout); the `worktree-remove` verb handles the worktree removal step before these cleanup verbs run.

**Executor regeneration is owned by neither `integrate_into_main` nor this step.** `integrate_into_main` performs the plan-dir move-back only and does NOT regenerate the executor. On-main executor regeneration is performed by the project-level `project:finalize-step-sync-plugin-cache` step (order 85) after the cache sync, in both worktree and no-worktree finalize flows, because the executor is per-tree derived state (generated, never file-moved onto main) per ADR-002.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path convention, never-edit-main-checkout invariant, cleanup ordering rationale).

## Merge-Mutex Hold Window (widened)

The cross-plan merge mutex (`plan-marshall:manage-locks:merge_lock`) is held across the **full staleness-exposure window**, not just the merge call. Under the default `merge_hold_window == full_window_release_at_waits`, PR-mode branch-cleanup **acquires the lock BEFORE the pre-merge force-push** (see § "Acquire the Merge Mutex" below) and holds it through `rebase → force-push → CI wait → merge → merge-CI-wait`, releasing only **after `switch-and-pull`** has pulled the merge commit into the base branch. This closes the exposure window the previous narrow hold left uncovered: the old flow acquired the lock only at the Pre-Merge Gate, AFTER rebase → force-push → CI wait had already run, so `origin/{base_branch}` could advance under a concurrent plan during the CI wait and the merge would land stale. Both the auto path (`final_merge_without_asking == true`) AND the interactive path acquire the lock — the interactive path previously never locked.

The widened hold obeys four invariants:

1. **Release-and-FIFO-re-enqueue at every operator-wait / loop-back boundary.** The lock is held ONLY across non-interactive spans. Before EVERY `AskUserQuestion` (the Pre-Rebase Confirmation Gate, the re-review-timeout trigger-A gate, the Pre-Merge Confirmation Gate, the Pre-Merge Comment-Completeness Barrier ask gate, and the merge-queue budget-exhaustion escalation) and before every loop-back boundary (the loop-back-to-phase-5 disposition AND the Pre-Merge Comment-Completeness Barrier's fail-closed loop-back-to-6-finalize), the orchestrator releases the lock **if held** and re-enqueues via the FIFO admission queue (preserving FIFO position). On resume it RE-ACQUIRES through the same FIFO poll loop and **re-validates** — re-runs `baseline-reconcile` and re-rebases when `origin/{base_branch}` advanced during the released window — before merging. Releasing before the interactive wait is what prevents a held lock from blocking every other plan while this plan waits on a human. (At the Pre-Rebase Gate the lock is normally not yet held, so its release is a no-op; the guard is uniform for robustness.)

2. **Bounded hold with the `merge_hold_budget_seconds` knob.** The orchestrator records the wall-clock instant of acquire and tracks elapsed-since-acquire. When a legitimate wait would push the held duration past `merge_hold_budget_seconds` (default 3600s), it releases + FIFO-re-enqueues + escalates via `AskUserQuestion` rather than continuing to hold. `merge_lock.py` is unchanged — its holder-liveness reclaim already bounds a CRASHED holder; this budget bounds a live-but-slow holder at the orchestrator layer.

3. **FIFO fairness preserved** via the existing admission queue (`merge_queue.json`); the serialized-structure-is-front invariant (`merge_lock._fifo_front`) is unchanged, so a release-then-re-enqueue keeps the plan's place in line.

4. **Release-on-abort, provably.** EVERY error / abort path — rebase conflict, force-push rejected (lease violation), `safe-merge` failure, worktree-remove failure, classifier error — releases the lock (if held) before returning. `merge_lock release` is idempotent and foreign-safe, so a release on a path where the lock was never acquired is a safe no-op.

`merge_hold_budget_seconds` and `merge_hold_window` are declared in this step's `configurable:` frontmatter; their seed-into-`marshal.json` assertion is owned by deliverable 6's `test_config_defaults.py` (single test owner). The narrow legacy hold is still available via `merge_hold_window == pre_merge_only` (acquire only at the Pre-Merge Gate, as the pre-widening flow did).

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

```text
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

The `auto_rebase_threshold`, `pr_merge_strategy`, `final_merge_without_asking`, and `admin_merge_on_stuck_state` params are all step-owned params of the `default:branch-cleanup` step. Read them from the plan-local execution-manifest step-params snapshot in a single one-stop call (the same `params` object is reused at the merge-strategy, pre-merge-gate, and Merge-PR reads below):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id branch-cleanup
```

Read `auto_rebase_threshold` off the returned `params` object as `{threshold}`. Default: `no_overlap_only`. Accepted values:

- `no_overlap_only` — auto-proceed only when classifier returns `classification: no_overlap`.
- `auto_resolvable` — also auto-proceed when classifier returns `classification: overlap_no_content_conflict` AND `auto_reconciled: true`.
- `never` — always prompt the user; skip the classifier entirely. This is the legacy opt-out for users who prefer the unconditional gate.

The param's lifecycle: the default is declared in this step's `configurable:` frontmatter (resolved by the `plan-marshall:extension-api:configurable_contract` parser, which the `get_default_config()` finalize-step seed delegates to), is snapshotted into the manifest at compose time, is read at runtime via the manifest `step-params get` call above, and is operator-visible in `.plan/marshal.json` under the `default:branch-cleanup` step's nested param object (seeded by `manage-config init` / `sync-defaults`). This document is the authoritative description of the threshold's effect on the gate, not its storage — the `configurable:` declaration owns the default.

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

The merge step itself is governed by a separate gate (see **Pre-Merge Confirmation Gate** below) routed by the orthogonal `final_merge_without_asking` knob. The two gates are independent: a permissive `auto_rebase_threshold` does NOT imply a permissive merge gate, and vice versa.

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

```text
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

Read `pr_merge_strategy` off the `default:branch-cleanup` step's param object — the same `params` object resolved by the one-stop `step-params get` call in the **Conflict-Severity Classifier** section above (re-issue the call if the value was not retained):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id branch-cleanup
```

Extract `pr_merge_strategy` from the returned `params` object as `{pr_merge_strategy}` (default: `squash`). Valid values: `squash`, `merge`, `rebase`.

### Acquire the Merge Mutex (before the pre-merge force-push)

**Only if `state == open` AND `merge_hold_window == full_window_release_at_waits`** (the default). Read `merge_hold_window`, `merge_hold_budget_seconds`, and `merge_queue_wait_budget_seconds` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above. When `merge_hold_window == pre_merge_only`, SKIP this section — the lock is acquired later, at the Pre-Merge Gate, exactly as the legacy narrow flow did.

This is the widened-hold acquire point: it takes the cross-plan merge mutex BEFORE the rebase force-push (the first staleness-creating operation), so the lock spans the entire `force-push → CI wait → merge → merge-CI-wait` window. It runs on BOTH the auto (`final_merge_without_asking == true`) and interactive paths — the interactive path previously never locked. The Pre-Rebase Confirmation Gate has already resolved above (an operator wait that completed while NO lock was held), so acquiring here does not hold the lock across a human prompt.

Acquire via the FIFO admission queue exactly as documented in **Budget-exhaustion escalation** below — the same poll/backoff mechanism, bounded by `merge_queue_wait_budget_seconds`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock acquire \
  --plan-id {plan_id}
```

Follow the **FIFO poll/backoff loop** and **Budget-exhaustion escalation** procedure (see the Pre-Merge Gate section below for the canonical poll-loop body — `acquire` returns immediately, pace polls with a single standalone `sleep {interval}` Bash call, evaluate the `admission` discriminator, fall back to the last-resort `AskUserQuestion` on budget exhaustion). On `admission: admitted`, **record the wall-clock instant of acquire as `{hold_start}`** so the `merge_hold_budget_seconds` bound (see § "Merge-Mutex Hold Window") can be tracked across the held window, then continue to **Rebase Branch onto Base** below. The lock is now held; every operator-wait and abort path from here on obeys the release invariants in § "Merge-Mutex Hold Window".

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

  Do NOT proceed with force-push, merge, or any cleanup. The conflicted rebase state is intentionally preserved so the user can resolve conflicts in the worktree and run `git rebase --continue` or `git rebase --abort` as appropriate. **Release-on-abort**: before returning, release the merge mutex if held (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe, so a no-op when the widened hold was not acquired) per § "Merge-Mutex Hold Window" invariant 4.

- `status: error` → ABORT cleanup with a fatal error using the returned `error` and `message` fields:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree-rebase-to failed - {error}: {message}"
  ```

  Then return — do NOT proceed with force-push or merge. **Release-on-abort**: release the merge mutex if held before returning (§ "Merge-Mutex Hold Window" invariant 4).

On a successful rebase, push the rewritten history to the remote with a lease guard via the `force-push-with-lease` verb (see `workflow-integration-git` Canonical invocations → `force-push-with-lease`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  force-push-with-lease --plan-id {plan_id}
```

Parse the TOON output. On `status: rejected` (lease violation — remote moved since last fetch), ABORT cleanup and surface the error. On `status: error`, ABORT cleanup and return the error TOON verbatim to the dispatcher. On `status: success`, continue to the CI wait below. **Release-on-abort**: on either the `rejected` or `error` branch, release the merge mutex if held before returning (§ "Merge-Mutex Hold Window" invariant 4) — a lease violation means `origin/{base_branch}` moved, so holding the lock further would only block the plan that legitimately advanced it.

After the force-push, gate on CI before proceeding to merge. **How much CI wall-clock this gate spends is governed by `use_merge_queue`** — read `use_merge_queue` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (default: `false`). When the merge queue is enabled, the platform re-tests the rebased HEAD against the latest base as its OWN authoritative CI gate (see § "Merge routing"), so a full-green pre-merge wait here is redundant with it — the pre-review full-green `ci-verify` wait is folded into the merge queue's authoritative CI.

- **`use_merge_queue == true`** — the merge queue's re-test is the authoritative CI. Do NOT block for full-green CI here; run only a cheap **not-obviously-red** snapshot so a branch that is ALREADY clearly failing is surfaced before it is enqueued, then proceed to the enqueue where the queue's authoritative CI runs:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} checks status \
      --pr-number {pr_number}
  ```

  Parse `overall_status` from the returned TOON. `pending`, `success`, and `none` all proceed straight to the merge routing without waiting — the queue re-tests regardless. A `failure` snapshot (CI has already gone clearly red on the rebased HEAD) logs the warning below but still proceeds; the merge queue will re-test and refuse a still-red HEAD, so this gate never hard-blocks — it only surfaces the early signal cheaply. This is the fold: the redundant full-green pre-merge CI wait is removed under the merge-queue path, leaving only this single non-blocking snapshot.

- **`use_merge_queue == false`** (default) — the immediate `pr safe-merge` path below has NO queue re-test, so the pre-merge CI wait remains the authoritative gate. Pass `--adaptive` so this wait seeds its ceiling from — and records its observed duration back into — the persisted `ci:wait` budget (the same #849 ratchet `ci_complete_precondition` drives), instead of the fixed `DEFAULT_CI_TIMEOUT`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} checks wait \
      --pr-number {pr_number} --adaptive
  ```

  **Bash tool timeout**: 1800000ms (30-minute safety net — the outer ceiling; `--adaptive` seeds the inner `ci:wait` ceiling from the persisted budget so the wait converges on observed CI durations rather than the fixed baseline).

The disposition of a red gate depends on WHICH path produced it — the two paths are NOT symmetric, because only the merge-queue path has an authoritative re-test behind it:

- **Merge-queue path (`use_merge_queue == true`)** — a `failure` snapshot is NON-authoritative: the merge queue re-tests the rebased HEAD and refuses a still-red one, so this cheap snapshot never hard-blocks. Log a warning and proceed to the enqueue:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup: CI red snapshot after rebase (merge-queue path) — enqueuing anyway; the merge queue re-tests and refuses a still-red HEAD"
  ```

- **Immediate-merge path (`use_merge_queue == false`, default)** — the `pr safe-merge` below has NO queue re-test, so this `checks wait --adaptive` IS the authoritative CI gate. A failing (or `timed_out`) wait means a KNOWN-RED PR, and warn-and-proceed here would merge it whenever branch protection does not itself enforce the check. Do NOT proceed. Parse the wait's terminal status (`final_status`) from the returned TOON; when it is not green, **ABORT or ESCALATE** — never warn-and-continue:

  - **Abort (default, fail-loud)**: release the merge mutex if held (§ "Merge-Mutex Hold Window" invariant 4 — the plan no longer intends to merge), decision-log the abort naming the red checks, and return control to the dispatcher WITHOUT calling `pr safe-merge`. Re-entering finalize after CI goes green is the recovery path.

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level ERROR --message "(plan-marshall:phase-6-finalize) Branch cleanup: CI RED on the authoritative immediate-merge gate (use_merge_queue=false, no queue re-test) — aborting merge for known-red PR #{pr_number}; re-enter finalize after CI is green"
    ```

  - **Escalate (operator override)**: when an operator gate is warranted, fire an inline `AskUserQuestion` mirroring the trigger-A timeout gate — default **"Abort merge"**, with an explicit **"Merge anyway — override red CI"** option that decision-logs the override at WARNING before proceeding. Silent warn-and-proceed is NOT one of the options.

Log the rebase:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: rebased onto origin/{base_branch}, force-pushed with lease, CI gated"
```

### Re-review the rebased HEAD (trigger A)

**Only if `state == open`** (a rebase + force-push happened above): the rebase/force-push advanced HEAD past the `reviewed_commit_sha` of the staged `pr-comment` findings, so branch-cleanup's own rebase commit is unreviewed. This step re-requests a fresh bot review for the new HEAD (gated by the `re_review_on_branch_cleanup` knob, default `true`, owned by the `plan-marshall:automatic-review` step) and, on a re-review await timeout, resolves the unreviewed-HEAD decision via the `re_review_on_timeout` knob (default `ask`, an inline operator gate). The full walkthrough — bot_kind resolution, the `github_re_review re-review` invocation, the matched/timed_out branches, and the three timeout dispositions (proceed / defer / ask) — lives in the same-directory sub-standard [`branch-cleanup-rereview.md`](branch-cleanup-rereview.md). Load and execute it here when `state == open`, then continue to the **Pre-Merge Confirmation Gate**. This gate is an operator-wait boundary, so it obeys the § "Merge-Mutex Hold Window" release-before-wait / re-acquire-and-re-validate invariants.

### Pre-Merge Confirmation Gate

**Only if `state == open`** (when `state == merged` there is nothing to merge — skip this entire section and proceed to **Wait for Merge CI**, which itself is a no-op on the `state == merged` path).

The pre-merge gate fires after `ci wait` returns green on the rebased branch and BEFORE the `pr merge --delete-branch` call below. It is suppressed only when `final_merge_without_asking == true`. The gate is orthogonal to the pre-rebase gate above — the operator may have auto-proceeded through rebase but still be asked to confirm the irreversible merge step.

#### Read the auto-merge gate

Read `final_merge_without_asking` off the `default:branch-cleanup` step's param object — the same `params` object resolved by the one-stop `step-params get` call in the **Conflict-Severity Classifier** section above (re-issue the call if the value was not retained):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id branch-cleanup
```

Extract `final_merge_without_asking` from the returned `params` object as `{final_merge_without_asking}` (default: `false`). Valid values: `true`, `false`. The default is now `false` — interactive-by-default: the operator is prompted to confirm before the irreversible merge to `main`. `true` is the explicit opt-in to unattended auto-merge after CI, serialized across plans via the cross-plan merge-lock so concurrent plans can never race on the merge-to-main critical section. The read mechanism is a plain boolean — no tri-state, no back-compat normalization.

#### Re-run the classifier against the current head

The pre-rebase classifier observation can be stale by the time CI completes (other commits may have landed on `origin/{base_branch}` during the wait). Re-dispatch the classifier so the gate is anchored to the *current* head SHA on the rebased branch:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  baseline-reconcile --plan-id {plan_id} --no-emit
```

Parse the TOON return for refreshed `classification`, `auto_reconciled`, `conflict_count`, `upstream_commit_count` values. These values are surfaced to the operator in the prompt below so the merge decision is anchored to the post-rebase reality, not the pre-rebase snapshot. Under `merge_hold_window == full_window_release_at_waits` this re-run classifier IS the mandatory post-hold re-validation before the merge (§ "Merge-Mutex Hold Window" invariant 1).

If the script exits non-zero, STOP and return an error TOON to the dispatcher carrying the stderr verbatim. Do NOT silently fall back to `needs_user` on classifier failure — a broken probe is a different signal than a real conflict. **Release-on-abort**: release the merge mutex if held before returning (§ "Merge-Mutex Hold Window" invariant 4).

#### Auto-merge bypass (`final_merge_without_asking == true`)

When `{final_merge_without_asking} == true`, skip the `AskUserQuestion` block entirely and log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: pre-merge auto-proceed (final_merge_without_asking=true), pre-merge confirmation gate bypassed"
```

##### Acquire / confirm the cross-plan merge-lock (canonical FIFO procedure)

The merge is ALWAYS lock-coordinated: because the merge-to-main critical section serializes through the unified merge-lock, concurrent plans can never race on it. This section is the **canonical FIFO acquire procedure** referenced both by the early § "Acquire the Merge Mutex" (widened hold) and by the legacy `pre_merge_only` path.

**Under `merge_hold_window == full_window_release_at_waits`** (default): the lock was ALREADY acquired before the force-push (§ "Acquire the Merge Mutex") and — unless a subsequent operator-wait released it — is still held here. In that case do NOT re-run the poll loop; the freshly-re-run classifier above IS the required re-validation, so proceed directly to **Merge PR (if not yet merged)**. Only when a prior operator-wait boundary released the lock (trigger-A timeout, or the interactive Pre-Merge prompt) do you re-enter the poll loop below to RE-ACQUIRE, then re-validate before merging.

**Under `merge_hold_window == pre_merge_only`** (legacy narrow hold): the lock was NOT acquired earlier — acquire it here now via the poll loop below. BEFORE the merge, this plan takes its turn at the head of the FIFO merge queue. `acquire` is **non-blocking for the queue case** — it FIFO-enqueues `--plan-id` into `merge-queue.json` (idempotently, preserving FIFO position on re-poll), admits ONLY the FIFO-front plan, and returns an `admission` discriminator; the poll/backoff wait is the consumer's job here, NOT an internal `time.sleep` inside the script (see `plan-marshall:manage-locks` Canonical invocations → `merge_lock acquire`). `acquire` returns IMMEDIATELY — the `--timeout` flag is a legacy compatibility no-op (default `0`) and drives no internal backoff. The consumer paces successive polls by issuing a SINGLE standalone `sleep {interval}` Bash call between `acquire` invocations — one command, never a Bash `for`/`while`/`until` loop.

###### Read the wait budget

Read `merge_queue_wait_budget_seconds` off the `default:branch-cleanup` step's param object — the same `params` object resolved by the one-stop `step-params get` call in the **Conflict-Severity Classifier** section above (re-issue the call if the value was not retained):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id branch-cleanup
```

Extract `merge_queue_wait_budget_seconds` from the returned `params` object as `{wait_budget}` (default: `1800`, ~30 minutes). This caps the wall-clock time the FIFO poll loop waits for admission before falling back to the last-resort `AskUserQuestion`.

###### FIFO poll/backoff loop

Record the wall-clock start time. Then re-poll `merge_lock acquire` until the plan is admitted at the FIFO front or the `{wait_budget}` is exhausted. Each poll is a SINGLE Bash command — there is NO `for`/`while`/`until` shell loop. `acquire` returns immediately (it does not wait internally), so the model issues one `acquire` Bash call per poll iteration, evaluates the `admission` discriminator, and — when still blocked and within budget — paces the next poll with a SINGLE standalone `sleep {interval}` Bash call (one command, e.g. `sleep 30`) before re-issuing `acquire`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock acquire \
  --plan-id {plan_id}
```

**Bash tool timeout**: the `acquire` poll returns immediately, so the default Bash timeout suffices; the inter-poll pacing is the separate standalone `sleep {interval}` call.

Parse the TOON output and branch on the `admission` discriminator:

- **`status: success`, `admission: admitted`** (`action: acquired`, or `action: already_held` on a reentrant self-holder re-acquire) → this plan is the FIFO front and holds the `O_EXCL` lock (created via `O_EXCL`, or a dead holder's lock reclaimed with `reclaimed: true`). Exit the poll loop and proceed to **Merge PR (if not yet merged)** below.
- **`status: blocked`, `admission: blocked`** → this plan is not yet the FIFO front, or is the front but a FOREIGN live holder still holds the lock. The script returns `blocking_plan_id` and `waiting_count` (NOT a hard error). Check the elapsed wall-clock time against `{wait_budget}`:
  - **Elapsed < `{wait_budget}`** → pace the next poll with a single standalone `sleep {interval}` Bash call (one command, e.g. `sleep 30`), then re-issue the single `merge_lock acquire --plan-id {plan_id}` Bash call above (the next poll). The FIFO position is preserved across polls, so re-polling never loses the plan's place in line.
  - **Elapsed ≥ `{wait_budget}`** → the budget is exhausted; the poll loop ends and the last-resort `AskUserQuestion` escalation below fires.
- **`status: error`** (a resolution failure, distinct from `admission: blocked`) → STOP and surface the stderr verbatim per the **Exit-code convention** at the top of this document. Do NOT route a hard error to the escalation prompt — a broken lock primitive is a different signal than queue contention.

Optionally log each `admission: blocked` poll for grep-ability during a run:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup: merge-queue poll blocked behind {blocking_plan_id} (waiting_count={waiting_count}), re-polling within budget"
```

###### Budget-exhaustion escalation (last resort)

Only when the FIFO poll loop exhausts `{wait_budget}` without admission does the escalation fire. Surface the FIFO-front `blocking_plan_id` from the final `admission: blocked` poll:

```yaml
AskUserQuestion:
  questions:
    - question: "Another plan ({blocking_plan_id}) is at the front of the merge queue. Keep waiting, or skip this merge?"
      header: "Branch Cleanup — Merge-queue wait budget exhausted"
      description: |
        **Front-of-queue plan**: {blocking_plan_id}
        **This plan**: {plan_id}
        **Wait budget**: {wait_budget}s (exhausted)

        The unified merge-lock serializes the merge-to-main critical
        section behind a FIFO admission queue. {blocking_plan_id} is ahead
        of this plan (or holds the lock) and has not yet released. The
        {wait_budget}-second FIFO poll budget elapsed without this plan
        reaching the front.
      options:
        - label: "Wait and retry"
          description: "Re-enter the FIFO poll loop for another {wait_budget}-second budget"
        - label: "Skip merge"
          description: "Defer merge; exit cleanly so finalize can be re-entered later"
      multiSelect: false
```

On **Wait and retry**, reset the wall-clock start time and re-enter the **FIFO poll/backoff loop** above (a fresh `{wait_budget}` window; the plan kept its FIFO position throughout). On **Skip merge**, set `{merge_consent} = deferred` and follow the same skip path as the interactive "No, skip merge" branch.

Once `admission: admitted` is reached, proceed directly to **Merge PR (if not yet merged)** below. The `{merge_consent} = explicit_yes` flag is set so the `pr safe-merge` poll-then-merge path (including its GitHub-only stuck-state admin fallback when `admin_merge_on_stuck_state` is enabled) is authorized.

> **Sync note**: the merge-lock is the unified `plan-marshall:manage-locks:merge_lock` primitive (the file-based `O_EXCL` mutex). After this plan merges, the `finalize-step-sync-plugin-cache` step syncs the plugin cache and regenerates the executor against main (after the cache sync), so the notation resolves.

#### Interactive merge prompt (`final_merge_without_asking == false`)

**Release-before-wait / re-acquire-after (widened hold)**: this Pre-Merge Gate is an operator-wait boundary. Under `merge_hold_window == full_window_release_at_waits`, BEFORE presenting the `AskUserQuestion` below, release the merge mutex if held and FIFO-re-enqueue (`merge_lock release --plan-id {plan_id}`), so the plan does not hold the lock across the human confirmation (§ "Merge-Mutex Hold Window" invariant 1). On "Yes, merge", RE-ACQUIRE via the canonical FIFO poll loop above and **re-validate** — re-dispatch `baseline-reconcile` and re-rebase when `origin/{base_branch}` advanced during the released window — before issuing the merge (mirroring the trigger-A re-review-timeout section's wording). Do NOT reuse the pre-wait classifier run from § "Re-run the classifier against the current head": that run was anchored to HEAD BEFORE the human confirmation, and because the confirmation can take an arbitrary amount of time `origin/{base_branch}` may have advanced further during the wait — invariant 1 requires re-running `baseline-reconcile` on resume-after-release, not reusing a stale pre-wait result. Check the `merge_hold_budget_seconds` bound against elapsed-since-`{hold_start}` and escalate if exceeded.

Read `use_merge_queue` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (default: `false`). It selects which action the "Yes, merge" option authorizes below, so the operator-facing description matches the routed action performed by the authoritative **Merge routing (`use_merge_queue`)** section under **Merge PR** — this gate only describes the action; it does not itself route.

Present the merge context and ask the operator to confirm. The prompt is anchored to the current (post-rebase, post-CI) head SHA via the freshly-re-run classifier above:

```text
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
        {On `use_merge_queue == false` (default):}
        {- `pr safe-merge --pr-number {pr_number} --strategy {pr_merge_strategy} --delete-branch` (polls readiness, then merges and deletes the remote branch; GitHub-only `--admin` stuck-state fallback when `admin_merge_on_stuck_state` is enabled)}
        {On `use_merge_queue == true`:}
        {- ENQUEUE via `ci pr merge-queue --pr-number {pr_number}` — NO `--delete-branch` and NO direct-merge/admin fallback; the platform re-tests-and-merges against the latest base and deletes the head branch itself after the queue merge (repo `delete_branch_on_merge` / queue auto-delete)}
        - Switch to {base_branch}, pull latest, delete local branch {head_branch}

        **Actions on "No, skip merge"**:
        - Workflow exits cleanly; the rebased branch is left in place
        - Re-enter finalize later to merge (state == merged short-circuits this prompt if you merged manually)
      options:
        - label: "Yes, merge"
          description: "Authorize the merge — routed by use_merge_queue: safe-merge --delete-branch (+ admin fallback) on false; pr merge-queue enqueue on true"
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

**If user selects "Yes, merge"**: Set `{merge_consent} = explicit_yes` and proceed to **Merge PR (if not yet merged)** below, where the **Merge routing (`use_merge_queue`)** section performs the routed action. The authorization is symmetric with that routing:

- On `use_merge_queue == false` (default): the `pr safe-merge` poll-then-merge path — including its GitHub-only stuck-state admin fallback when `admin_merge_on_stuck_state` is enabled — is authorized (explicit consent was given for the merge action; the stuck-state fallback is part of the same merge intent).
- On `use_merge_queue == true`: the ENQUEUE via `ci pr merge-queue` is authorized instead — with NO `--delete-branch` and NO direct-merge/admin fallback; the platform re-tests-and-merges against the latest base and performs the head-branch deletion itself after the queue merge.

### Pre-Merge Comment-Completeness Barrier

**Only if `state == open` AND `{merge_consent} == explicit_yes`** (the `final_merge_without_asking == true` bypass and the interactive "Yes, merge" both set `{merge_consent} = explicit_yes`). This fail-closed barrier fires AFTER the pre-merge gate authorized the merge and BEFORE the **Merge PR (if not yet merged)** routing below, so it gates BOTH the `use_merge_queue == false` safe-merge path and the `use_merge_queue == true` merge-queue path (both live inside **Merge PR**). It re-fetches bot comments from the provider against the current HEAD and refuses to merge while any `pr-comment` finding is still unhandled — closing the window where a comment that lands after `automatic-review` (order 30) marked done is never re-fetched by the time `branch-cleanup` (order 70) merges. The existing `phase_handshake findings-check` gate only re-reads the findings *store*; this barrier re-reads the *provider*, so a comment that was never fetched is visible to it.

#### Read the barrier knob and the enabled-bot set

Read `pre_merge_comment_barrier` off the `default:branch-cleanup` step's param object — the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (re-issue the call if the value was not retained):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id branch-cleanup
```

Extract `pre_merge_comment_barrier` from the returned `params` object as `{barrier_mode}` (default: `fail_into_loopback`). Valid values: `fail_into_loopback`, `ask`.

Read `enabled_bots` off the `plan-marshall:automatic-review` step's param object (the set of `bot_kind`s this plan reviews with):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review
```

Extract `enabled_bots` from the returned `params` object as `{enabled_bots}` (e.g. `coderabbit,sourcery,gemini`).

#### Re-fetch bot comments against the current HEAD

Re-run the `github_pr fetch_findings` producer. It dedups against the already-stored findings via `_existing_pr_comment_keys`, so this files ONLY genuinely-new comments as pending `pr-comment` findings — a re-fetch of an already-handled comment adds nothing:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  fetch_findings --pr-number {pr_number} --plan-id {plan_id} --enabled-bots {enabled_bots}
```

> **GitLab provider asymmetry**: the GitLab producer `gitlab_pr fetch_findings` has NO `--enabled-bots` flag (the same asymmetry the FIND stage already documents). On GitLab, invoke it without the flag; every comment is considered.

#### Query for unhandled comments

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type pr-comment --resolution pending
```

Parse the returned `findings` list; let `{count}` be its length.

#### Clean path — zero pending findings

When the pending `pr-comment` list is empty, the barrier is satisfied: every enabled bot's comments against the current HEAD are handled. Log and proceed directly to **Merge PR (if not yet merged)** below — the barrier added exactly one `fetch_findings` call and zero dispatches:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Pre-merge comment barrier: clean — zero pending pr-comment findings, proceeding to merge"
```

#### Blocked path — one or more pending findings

When the pending list is non-empty, the merge is blocked. Branch on `{barrier_mode}`:

##### `{barrier_mode} == fail_into_loopback` (default)

Loop the plan back into the `automatic-review` triage pipeline so the unhandled comments are triaged before any further merge attempt. **Release-on-loopback**: release the merge mutex if held (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe) per § "Merge-Mutex Hold Window" invariant 4 — a loop-back to triage is a wait boundary, so the lock must not be held across it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
  --plan-id {plan_id}
```

Record the `branch-cleanup` step as a loop-back to `6-finalize` so the phase-6-finalize loop-back continuation hook re-fires the finalize pipeline (re-running `automatic-review`'s FIND → TRIAGE → RESPOND over the newly-filed pending findings, then re-entering this barrier):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome loop_back \
  --loop-back-target 6-finalize --display-detail "pre-merge comment barrier: {count} unhandled comment(s), looping back to triage"
```

Log the decision and return control to the finalize dispatcher:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Pre-merge comment barrier: {count} unhandled pr-comment finding(s) — pre_merge_comment_barrier=fail_into_loopback, looping back to automatic-review triage (merge blocked)"
```

Do NOT proceed to **Merge PR**. The re-fired finalize pipeline re-runs the triage and re-enters this barrier; a subsequent clean barrier proceeds to merge.

##### `{barrier_mode} == ask`

Fire an inline `AskUserQuestion` (branch-cleanup runs inline in the orchestrator). **Release-before-wait / re-acquire-after (widened hold)**: this ask is an operator-wait boundary — under `merge_hold_window == full_window_release_at_waits`, release the merge mutex if held (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe) and FIFO-re-enqueue BEFORE the prompt (§ "Merge-Mutex Hold Window" invariant 1), mirroring the `fail_into_loopback` branch's explicit release step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
  --plan-id {plan_id}
```

On the "Merge anyway" resume, RE-ACQUIRE via the canonical FIFO poll loop (§ "Acquire / confirm the cross-plan merge-lock") and re-validate (`baseline-reconcile`) before merging.

Then fire the prompt:

```text
AskUserQuestion:
  questions:
    - question: "{count} bot comment(s) are still unhandled at merge time. How should branch cleanup proceed?"
      header: "Branch Cleanup — Pre-merge comment barrier"
      description: |
        **PR**: #{pr_number}
        **Unhandled pr-comment findings**: {count}

        A re-fetch against the current HEAD surfaced comment(s) that
        were never handled. Merging now would land the PR with open
        bot feedback.
      options:
        - label: "Re-triage now"
          description: "Loop back into automatic-review triage before merging"
        - label: "Merge anyway (record reason)"
          description: "Proceed to merge despite unhandled comments; a reason is recorded"
        - label: "Defer merge"
          description: "Skip the merge; re-enter finalize later"
      multiSelect: false
```

Branch on the operator's selection:

- **"Re-triage now"** → take the SAME loop-back path as `fail_into_loopback` above (release the mutex per invariant 4, record `branch-cleanup` as `loop_back` to `6-finalize`, log, return).
- **"Merge anyway (record reason)"** → RE-ACQUIRE the merge mutex and re-validate (per the release-before-wait note above), decision-log at WARNING naming the unhandled count and the operator's reason, then continue to **Merge PR (if not yet merged)** below:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Pre-merge comment barrier: operator chose merge-anyway with {count} unhandled comment(s) — reason: {reason}"
  ```

- **"Defer merge"** → set `{merge_consent} = deferred`, skip the **Merge PR**, **Wait for Merge CI**, **Remove Worktree**, and **Switch to Base Branch** sections, emit the `mark-step-done` payload using **Branch C — declined by user**, and return (the mutex was already released before the prompt). Log the decision:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Pre-merge comment barrier: operator deferred merge with {count} unhandled comment(s) — re-enter finalize later"
  ```

### Merge PR (if not yet merged)

**Only if `state == open` AND the pre-merge gate above resolved to `{merge_consent} == explicit_yes`** (the `final_merge_without_asking == true` bypass also sets `{merge_consent} = explicit_yes`):

#### Merge routing (`use_merge_queue`)

Read `use_merge_queue` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (default: `false`). This routing branch is documented BEFORE the merge dispatch it selects (bypass-before-dispatch ordering):

- **`use_merge_queue == false`** (default) → issue the immediate `pr safe-merge` call below. The plan merges the PR itself under the widened mutex.
- **`use_merge_queue == true`** → route the merge through the platform merge queue via the `pr merge-queue` verb INSTEAD of `pr safe-merge`, so the platform re-tests-and-merges against the latest base and serializes a truly-external commit the session-scoped mutex cannot. The widened D4 mutex still guards the pre-enqueue rebase/force-push window; the two mechanisms compose. The enqueue takes no `--strategy` or `--delete-branch` flag — unchanged: the platform merges queued PRs with the method configured on the queue itself, GitHub rejects `--delete-branch` when a merge queue is enabled, and the platform auto-deletes the head branch after the queue merge. The queue's configured method is no longer an independent knob, though — `repo merge-queue enable` provisions and reconciles it from `pr_merge_strategy`, and the mismatch warn below catches residual drift. All engagement is routed through the `ci` abstraction — NEVER a direct `gh`/`glab` call.

  **Merge-method mismatch warn (best-effort, advisory)** — BEFORE the enqueue, probe the queue's configured merge method and warn when it disagrees with the configured `pr_merge_strategy`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} repo merge-queue probe
  ```

  Parse the returned TOON. When it carries a `merge_method` field whose value differs from the mapped `pr_merge_strategy` (`squash` → `SQUASH`, `merge` → `MERGE`, `rebase` → `REBASE`), log a WARNING decision naming BOTH conflicting values and BOTH remedies, then proceed with the enqueue — the mismatch is warn-only and never blocks the merge:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Merge-queue merge-method mismatch: queue is configured {merge_method} but pr_merge_strategy maps to {mapped_strategy}. The platform will merge with {merge_method}. Remedies: re-run /marshall-steward → Configuration → Merge Queue to reconcile the queue, or change the pr_merge_strategy step param (default:branch-cleanup)."
  ```

  When the probe fails, returns `status: error`, or returns no `merge_method` field (GitLab, an unconfigured queue, an auth-scope failure), skip the comparison silently and proceed — the probe is advisory here, never a gate.

  Then enqueue:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr merge-queue \
      --pr-number {pr_number}
  ```

  Because the platform auto-deletes the remote head branch after the queue merge, no `--delete-branch` follow-up is needed; the later `prune-local-and-remote-ref` tail accounts for the local-branch prune either way — it deletes the local feature branch and, via its internal `show-ref` guard, produces a `status: partial` no-op when the remote-tracking ref is already gone (the platform already deleted the remote branch) or deletes the stale ref when it is still present.

  Parse the returned TOON. On `status: success` (`enqueued: true`), the PR is on the platform queue — proceed to **Wait for Merge CI** (the queue's own re-test) and the cleanup sections below. On `status: error` (e.g. a GitLab merge-train-ineligible project, or a queue-engagement / auth-scope failure), log the **actionable** error and abort — do NOT silently fall back to an immediate merge, since the operator opted into queue serialization for a reason. The abort message MUST name BOTH remedies so the operator is never left with a bare error: (a) **disable `use_merge_queue`** (set it back to `false` via `manage-config … step set --step-id default:branch-cleanup --param use_merge_queue --value false`) to merge immediately via `pr safe-merge`, or (b) **run the marshall-steward merge-queue provisioning step** (Configuration → Merge Queue) to configure the platform merge queue so the enqueue succeeds:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: pr merge-queue enqueue failed - {error}. Remedies: (a) disable use_merge_queue to merge immediately via pr safe-merge, or (b) run /marshall-steward → Configuration → Merge Queue to provision the platform merge queue, then re-run finalize."
  ```

  **Release-on-abort**: release the merge mutex if held before returning (§ "Merge-Mutex Hold Window" invariant 4).

The remainder of this section (the immediate `pr safe-merge` path) applies only when `use_merge_queue == false`.

Issue a single `pr safe-merge` call. It polls the PR's mergeability until ready, then merges (and deletes the remote branch via `--delete-branch`); on GitHub it additionally falls back to an `--admin` merge when the PR stays stuck `mergeable_state: blocked` past the poll timeout AND every active ruleset requirement is provably met. This single verb replaces the former `pr merge` → `pr auto-merge` branch-protection fallback sequence: the poll-then-merge path and the stuck-state admin fallback are both internal to `pr safe-merge`.

The GitHub-only `--admin` fallback is gated by the `{admin_merge_on_stuck_state}` param read from the one-stop `step-params get` call in the **Conflict-Severity Classifier** section above (default: `false`). Resolve `{admin_flag}` from that param: when `{admin_merge_on_stuck_state} == true`, `{admin_flag}` is the literal `--admin-merge-on-stuck-state`; when it is `false` (the default), `{admin_flag}` is the empty string and the flag is omitted entirely (it is `store_true`). On GitLab the flag is accepted but has no effect — there is no admin-merge equivalent, so a stuck MR surfaces as an error rather than force-merging.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr safe-merge \
    --pr-number {pr_number} --strategy {pr_merge_strategy} --delete-branch {admin_flag}
```

If `safe-merge` fails (poll timeout with the admin fallback disabled or unmet, a GitLab stuck state, or any merge error) → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: PR safe-merge failed - {error}"
```

**Release-on-abort**: before returning, release the merge mutex if held (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe) per § "Merge-Mutex Hold Window" invariant 4 — a failed merge must never leave the critical section locked against every other plan.

### Wait for Merge CI

**Only if PR was just merged** (state was open). Pass `--adaptive` so this post-merge wait also seeds from — and records into — the persisted `ci:wait` budget (the same #849 ratchet), rather than the fixed `DEFAULT_CI_TIMEOUT`:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} checks wait \
    --pr-number {pr_number} --adaptive
```

**Bash tool timeout**: 1800000ms (30-minute safety net — the outer ceiling; `--adaptive` seeds the inner `ci:wait` ceiling from the persisted budget so the wait converges on observed CI durations rather than the fixed baseline).

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
- `status: error, error: plan_dir_not_moved_back` → ABORT cleanup. The script-enforced move-back precondition fired: the plan directory has not been moved back to the main checkout, so removing the worktree would destroy the sole authoritative plan-state copy. Surface the error and run `integrate_into_main` first — NEVER retry with `--force` (the refusal is deliberately not overridable; `--force` keeps its dirty-tree meaning only):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree-remove refused (plan_dir_not_moved_back) — run integrate_into_main to land the plan dir on main, then re-run cleanup. Do not force."
```

- `status: error, error: worktree_remove_failed` → ABORT cleanup. The worktree has uncommitted changes or is otherwise not clean. Log the error:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: worktree remove failed at {worktree_path} - {error}. Salvage any uncommitted work and run 'git worktree remove --force {worktree_path}' manually."
```

Then return — do NOT proceed with branch deletion while the worktree still exists. **Release-on-abort**: the PR was already merged by this point (the merge-to-main critical section completed), but the terminal release (§ "Release the cross-plan merge-lock") runs only after `switch-and-pull`, which this abort path skips — so release the merge mutex if held here before returning (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe) per § "Merge-Mutex Hold Window" invariant 4.

### Switch to Base Branch, Pull, and Delete Local Branch

All git operations in this section target the main checkout because the worktree has been removed above.

**Uniform local cleanup (both `state == open` and `state == merged`)**:

The `--delete-branch` flag on `pr safe-merge` deletes ONLY the remote branch (via the provider REST API). It does NOT touch the local clone — local branch deletion and base-branch checkout are always the workflow's responsibility and must run here regardless of the prior merge path. After worktree removal, the main checkout may still be on the feature branch and the local feature branch still exists.

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

#### Release the cross-plan merge-lock (both paths)

**If the merge-lock is held** (acquired either early via § "Acquire the Merge Mutex" under the widened `full_window_release_at_waits` hold, OR at the Pre-Merge Gate under the legacy `pre_merge_only` hold — on EITHER the auto or interactive path). The release fires AFTER `switch-and-pull` has pulled the merge commit into the base branch — the merge-to-main critical section is now complete, so the lock file can be freed for the next plan (see `plan-marshall:manage-locks` Canonical invocations → `merge_lock release`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
  --plan-id {plan_id}
```

`release` is idempotent and foreign-safe (`action: noop` when the lock is already free or held by another plan — it never removes a foreign holder's lock), so a re-entry that already released the lock is a safe no-op, and a path that never acquired it releases harmlessly. This is the terminal (successful-path) release; the per-operator-wait releases (§ "Merge-Mutex Hold Window" invariant 1) and the release-on-abort paths (invariant 4) are the other release sites, all pointing at the same idempotent verb.

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

```text
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

On `status: error`, log and abort as in PR mode — including the script-enforced `error: plan_dir_not_moved_back` refusal (run `integrate_into_main` first; never retry with `--force`). Do not proceed with branch deletion while the worktree remains. On success, the consolidated verbs (`switch-and-pull`, `prune-local-and-remote-ref`) and any `ci` invocations MUST use `--project-dir {main_checkout}`.

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
