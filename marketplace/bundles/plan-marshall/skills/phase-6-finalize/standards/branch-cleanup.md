---
lane:
  class: core
  cost_size: XS
name: default:branch-cleanup
description: Branch cleanup — adapts to PR mode or local-only based on create-pr step presence
order: 70
mutates_source: false
advances_main_via_rebase: true
records_facts:
  - action
  - upstream_commit_count
  - merge_mechanism
  - work_performed
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
    description: Bound (in seconds, ~30 min) applied SEPARATELY to each of the two queue waits branch-cleanup performs, so one run can block for up to twice this value. Wait 1 is the FIFO merge-queue admission poll — how long the step waits for its turn at the head of the queue; on exhaustion it falls back to the last-resort AskUserQuestion. Wait 2 is the platform queue-landing poll, reached only when use_merge_queue is true — how long the step waits for the platform to merge the enqueued PR; on exhaustion it logs a WARNING, releases the merge mutex and returns via Branch F with NO AskUserQuestion, leaving the head branch intact and the post-merge cleanup deferred to a later finalize re-entry.
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
    description: Gate the fail-closed pre-merge review-completeness barrier that re-fetches bot comments immediately before merge/enqueue and blocks on EITHER of two predicates — any pr-comment finding still pending, or any REQUIRED bot whose participation against the current HEAD is unproven. The second predicate exists because the first cannot see an absence: a bot that never reviewed files no comment and so reads as clean to a pending count. fail_into_loopback (default) loops the plan back into the automatic-review triage pipeline (records the branch-cleanup step loop_back, releases the merge mutex if held, re-enters phase-6-finalize); ask fires an inline AskUserQuestion offering re-triage / merge-anyway-with-recorded-reason / defer. The clean path requires BOTH zero pending findings and participation_complete.
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

1. **Release-and-FIFO-re-enqueue at every operator-wait / loop-back boundary.** The lock is held ONLY across non-interactive spans. Before EVERY `AskUserQuestion` (the Pre-Rebase Confirmation Gate, the re-review-timeout trigger-A gate, the Pre-Merge Confirmation Gate, the Pre-Merge Review-Completeness Barrier ask gate, and the merge-queue budget-exhaustion escalation) and before every loop-back boundary (the loop-back-to-phase-5 disposition AND the Pre-Merge Review-Completeness Barrier's fail-closed loop-back-to-6-finalize), the orchestrator releases the lock **if held** and re-enqueues via the FIFO admission queue (preserving FIFO position). On resume it RE-ACQUIRES through the same FIFO poll loop and **re-validates** — re-runs `baseline-reconcile` and re-rebases when `origin/{base_branch}` advanced during the released window — before merging. Releasing before the interactive wait is what prevents a held lock from blocking every other plan while this plan waits on a human. (At the Pre-Rebase Gate the lock is normally not yet held, so its release is a no-op; the guard is uniform for robustness.)

2. **Bounded hold with the `merge_hold_budget_seconds` knob.** The orchestrator records the wall-clock instant of acquire and tracks elapsed-since-acquire. When a legitimate wait would push the held duration past `merge_hold_budget_seconds` (default 3600s), it releases + FIFO-re-enqueues + escalates via `AskUserQuestion` rather than continuing to hold. `merge_lock.py` is unchanged — its holder-liveness reclaim already bounds a CRASHED holder; this budget bounds a live-but-slow holder at the orchestrator layer.

3. **FIFO fairness preserved** via the existing admission queue (`merge_queue.json`); the serialized-structure-is-front invariant (`merge_lock._fifo_front`) is unchanged, so a release-then-re-enqueue keeps the plan's place in line.

4. **Release-on-abort, provably.** EVERY error / abort path — rebase conflict, force-push rejected (lease violation), `safe-merge` failure, worktree-remove failure, classifier error — releases the lock (if held) before returning. `merge_lock release` is idempotent and foreign-safe, so a release on a path where the lock was never acquired is a safe no-op.

`merge_hold_budget_seconds` and `merge_hold_window` are declared in this step's `configurable:` frontmatter; their seed-into-`marshal.json` assertion is owned by deliverable 6's `test_config_defaults.py` (single test owner). The narrow legacy hold is still available via `merge_hold_window == pre_merge_only` (acquire only at the Pre-Merge Gate, as the pre-widening flow did).

## Merge-Authorization Roster

Every mechanism by which an operator (or a policy standing in for one) authorizes advancing a tree past a merge gate. This section is the **declared population**: membership lives here and nowhere else, and the derivation guard in `test/plan-marshall/phase-6-finalize/test_merge_authorization_roster.py` parses these rows rather than carrying a hardcoded list, so a mechanism added here is covered automatically.

Each row leads with its backticked `{kind}` token and carries four machine-checkable claims — `head_bound:` (is this authorization bound to a specific tree), `bound_via:` (which mechanism binds it), `authorizes:` (which **gap class** the ruling covers), and `site:` (where that mechanism lives).

- `barrier-ask-override` — head_bound: yes — bound_via: grant — authorizes: review-barrier-gap — site: § Pre-Merge Review-Completeness Barrier, `{barrier_mode} == ask` → "Merge anyway (record reason)". Granted at the live HEAD alongside the existing WARNING decision-log line, and checked by the barrier before any blocked path proceeds.
- `pre-merge-consent` — head_bound: yes — bound_via: grant — authorizes: merge-action — site: § Pre-Merge Confirmation Gate → "Yes, merge" (`{merge_consent} = explicit_yes`). Granted at the live HEAD so a re-rebase between consent and merge — the release-before-wait / re-acquire path — lapses the consent instead of silently carrying it onto a different tree.
- `red-ci-override` — head_bound: yes — bound_via: grant — authorizes: red-ci-gate — site: § Rebase Branch onto Base, the immediate-merge authoritative CI gate → "Merge anyway — override red CI". Granted at the live HEAD before the override proceeds.
- `rereview-timeout-override` — head_bound: yes — bound_via: grant — authorizes: rereview-timeout — site: [`branch-cleanup-rereview.md`](branch-cleanup-rereview.md) § "On re-review timeout (trigger A)" — BOTH the `re_review_on_timeout: proceed` policy branch and the `ask` → "Merge anyway — proceed unreviewed" selection. Granted at the re-resolved `{head_sha}`.
- `automatic-review-force-done` — head_bound: yes — bound_via: head_dependent — authorizes: find-step-completion — site: [`automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § "Force-done with an explicit recorded reason". Bound by that step's own `head_dependent: true` declaration and its persisted `--head-at-completion`, and the barrier re-derives participation from the provider rather than trusting the record — so it needs no grant of its own.
- `final_merge_without_asking` — head_bound: n/a — bound_via: out_of_class — authorizes: merge-action — site: the `default:branch-cleanup` step param. Standing config that authorizes a *policy* rather than a specific tree, so it falls outside the HEAD-bound class and is recorded here rather than granted.

The verb backing every `bound_via: grant` row is `manage-status merge-authorization` — see `manage-status` Canonical invocations → `merge-authorization — grant` / `merge-authorization — check`.

### Gap classes — why HEAD-binding alone is not authorization

**`authorizes:` is what a check site routes on; `head_bound:` only says the ruling has not gone stale.** The two claims answer different questions and BOTH must hold. Every `bound_via: grant` site passes its row's `authorizes:` token as `--gap-class`, every check site passes the token for the gap IT is reporting, and a record is admissible only when the two agree at the current HEAD.

Routing on HEAD-validity alone is a fail-open shape, not a conservative one. Read the rows above in EXECUTION order: `red-ci-override` is granted at the CI gate, `rereview-timeout-override` at the trigger-A timeout, and `pre-merge-consent` at the Pre-Merge Confirmation Gate — all three BEFORE the Pre-Merge Review-Completeness Barrier, and all three at the same HEAD it is about to gate, because nothing rebases in between. `pre-merge-consent` is the sharpest case: on the default interactive path it is granted on every single "Yes, merge", so a barrier that admitted any HEAD-valid record would find one on every ordinary merge and skip its own disposition universally. A routine merge confirmation, given before the operator was ever shown the participation gap, would authorize past it — the same defect the HEAD binding exists to remove, re-entered through the side door.

The `check` verb stays deliberately kind-agnostic for the reason it always did: it returns EVERY record, so `lapsed_kinds` still names every expired sibling and a valid-but-wrong-gap record is reported in `inadmissible_kinds` rather than hidden. Admissibility narrows the ROUTING, never the REPORT.

`--granted-over` and `--gap-class` are complementary, not redundant: `--granted-over` is free prose naming the specific gap instance the operator saw (the pending count, the `unproven_bots` list), for a human re-evaluating the ruling against a later delta; `--gap-class` is the comparable machine token naming WHICH GATE was answered. Prose is not comparable, so routing never reads it.

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

The `auto_rebase_threshold`, `pr_merge_strategy`, `final_merge_without_asking`, `admin_merge_on_stuck_state`, `use_merge_queue`, `merge_queue_wait_budget_seconds`, `merge_hold_window`, `merge_hold_budget_seconds`, and `pre_merge_comment_barrier` params are all step-owned params of the `default:branch-cleanup` step. **The enumeration above is closed**: it names every `configurable:` key this document consumes, so every later read in this document names a member of THIS list and re-uses THIS `params` object rather than resolving one of its own. A key that is read anywhere below but missing from this enumeration is a defect in this section, not in the reading site. Read them from the plan-local execution-manifest step-params snapshot in a single one-stop call (the same `params` object is reused at the mutex-acquire, merge-strategy, CI-wait-strategy, pre-merge-gate, review-barrier, Merge-routing, queue-landing-gate, and post-merge-cleanup reads below):

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

**Observability (mandatory)** — immediately after the predicate above is evaluated and BEFORE the CI-gate branch it selects is entered, emit one decision-log line naming the bound value, its provenance, and the branch about to run. Which strategy a run took is otherwise unreconstructible from the log, because both branches call into `ci checks` and only the flags differ:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup CI-wait strategy: use_merge_queue={use_merge_queue} (provenance: default:branch-cleanup step-params object, Conflict-Severity Classifier one-stop read) — running {ci checks status snapshot, non-blocking | ci checks wait --adaptive, authoritative}"
```

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

    On the **"Merge anyway — override red CI"** selection, bind the override to the tree it was granted against. Resolve the live HEAD:

    ```bash
    git -C {worktree_path} rev-parse HEAD
    ```

    Record the output as `{sha}`, then grant (see `manage-status` Canonical invocations → `merge-authorization — grant`):

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
      --plan-id {plan_id} --kind red-ci-override --head {sha} --gap-class red-ci-gate \
      --granted-over "red CI on the authoritative immediate-merge gate: {red_checks}" --reason "{reason}"
    ```

    The grant is in addition to the WARNING decision-log line, never in place of it. `--gap-class red-ci-gate` is this row's `authorizes:` claim: the ruling covers a red CI gate and nothing else, so it can never be read as authorization at the later review barrier, which reports a different gap.

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

Once `admission: admitted` is reached, proceed directly to **Merge PR (if not yet merged)** below. The `{merge_consent} = explicit_yes` flag is set so the merge action routed by `use_merge_queue` (see the authoritative **Merge routing (`use_merge_queue`)** section under **Merge PR**) is authorized: the `pr safe-merge` poll-then-merge path (including its GitHub-only stuck-state admin fallback when `admin_merge_on_stuck_state` is enabled) when `use_merge_queue == false`, or the `ci pr merge-queue` enqueue (no `--delete-branch`, no direct-merge/admin fallback) when `use_merge_queue == true`.

> **Sync note**: the merge-lock is the unified `plan-marshall:manage-locks:merge_lock` primitive (the file-based `O_EXCL` mutex). After this plan merges, the `finalize-step-sync-plugin-cache` step syncs the plugin cache and regenerates the executor against main (after the cache sync), so the notation resolves.

#### Interactive merge prompt (`final_merge_without_asking == false`)

**Release-before-wait / re-acquire-after (widened hold)**: this Pre-Merge Gate is an operator-wait boundary. Under `merge_hold_window == full_window_release_at_waits`, BEFORE presenting the `AskUserQuestion` below, release the merge mutex if held and FIFO-re-enqueue (`merge_lock release --plan-id {plan_id}`), so the plan does not hold the lock across the human confirmation (§ "Merge-Mutex Hold Window" invariant 1). On "Yes, merge", RE-ACQUIRE via the canonical FIFO poll loop above and **re-validate** — re-dispatch `baseline-reconcile` and re-rebase when `origin/{base_branch}` advanced during the released window — before issuing the merge (mirroring the trigger-A re-review-timeout section's wording). Do NOT reuse the pre-wait classifier run from § "Re-run the classifier against the current head": that run was anchored to HEAD BEFORE the human confirmation, and because the confirmation can take an arbitrary amount of time `origin/{base_branch}` may have advanced further during the wait — invariant 1 requires re-running `baseline-reconcile` on resume-after-release, not reusing a stale pre-wait result. Check the `merge_hold_budget_seconds` bound against elapsed-since-`{hold_start}` and escalate if exceeded.

Read `use_merge_queue` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (default: `false`). It selects which action the "Yes, merge" option authorizes below, so the operator-facing description matches the routed action performed by the authoritative **Merge routing (`use_merge_queue`)** section under **Merge PR** — this gate only describes the action; it does not itself route.

**Observability (mandatory)** — immediately after the predicate above is evaluated and BEFORE the prompt whose wording it selects is presented, emit one decision-log line naming the bound value, its provenance, and the action the consent is about to be sought for. The operator's recorded consent is only interpretable against the action they were actually shown:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup pre-merge consent wording: use_merge_queue={use_merge_queue} (provenance: default:branch-cleanup step-params object, Conflict-Severity Classifier one-stop read) — seeking consent for {ci pr safe-merge --delete-branch | ci pr merge-queue enqueue}"
```

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
        {- `pr safe-merge --pr-number {pr_number} --strategy {pr_merge_strategy} --delete-branch` (polls readiness, then merges and deletes the remote branch; GitHub-only `--admin` stuck-state fallback when `admin_merge_on_stuck_state` is enabled) (if use_merge_queue == false)}
        {- ENQUEUE via `ci pr merge-queue --pr-number {pr_number}` — NO `--delete-branch` and NO direct-merge/admin fallback; the platform re-tests-and-merges against the latest base and deletes the head branch itself after the queue merge (repo `delete_branch_on_merge` / queue auto-delete) (if use_merge_queue == true)}
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

**If user selects "Yes, merge"**: Set `{merge_consent} = explicit_yes`, then bind the consent to the tree it was given over — the release-before-wait / re-acquire path may re-rebase between this consent and the merge, and an unbound consent would silently carry onto the different tree that produces. Resolve the live HEAD:

```bash
git -C {worktree_path} rev-parse HEAD
```

Record the output as `{sha}`, then grant (see `manage-status` Canonical invocations → `merge-authorization — grant`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
  --plan-id {plan_id} --kind pre-merge-consent --head {sha} --gap-class merge-action \
  --granted-over "operator confirmed merge of PR #{pr_number} at this HEAD" --reason "operator selected 'Yes, merge' at the Pre-Merge Confirmation Gate"
```

⚠ **`--gap-class merge-action` is what keeps this consent from authorizing past the barrier below.** The operator has confirmed the MERGE ACTION; they have not been shown a review-completeness gap, because the barrier has not run yet. This grant lands at the very HEAD the barrier is about to gate with no rebase in between, so without the class it would satisfy a HEAD-only check on every interactive merge and the barrier's disposition would never fire — see § "Gap classes — why HEAD-binding alone is not authorization".

Then proceed to **Merge PR (if not yet merged)** below, where the **Merge routing (`use_merge_queue`)** section performs the routed action. The authorization is symmetric with that routing:

- On `use_merge_queue == false` (default): the `pr safe-merge` poll-then-merge path — including its GitHub-only stuck-state admin fallback when `admin_merge_on_stuck_state` is enabled — is authorized (explicit consent was given for the merge action; the stuck-state fallback is part of the same merge intent).
- On `use_merge_queue == true`: the ENQUEUE via `ci pr merge-queue` is authorized instead — with NO `--delete-branch` and NO direct-merge/admin fallback; the platform re-tests-and-merges against the latest base and performs the head-branch deletion itself after the queue merge.

### Pre-Merge Review-Completeness Barrier

**Only if `state == open` AND `{merge_consent} == explicit_yes`** (the `final_merge_without_asking == true` bypass and the interactive "Yes, merge" both set `{merge_consent} = explicit_yes`). This fail-closed barrier fires AFTER the pre-merge gate authorized the merge and BEFORE the **Merge PR (if not yet merged)** routing below, so it gates BOTH the `use_merge_queue == false` safe-merge path and the `use_merge_queue == true` merge-queue path (both live inside **Merge PR**). It re-fetches bot comments from the provider against the current HEAD and refuses to merge while any `pr-comment` finding is still unhandled — closing the window where a comment that lands after `automatic-review` (order 30) marked done is never re-fetched by the time `branch-cleanup` (order 70) merges. The existing `phase_handshake findings-check` gate only re-reads the findings *store*; this barrier re-reads the *provider*, so a comment that was never fetched is visible to it.

**The barrier has TWO predicates, and the second exists because the first cannot see an absence.** Unhandled-comment completeness asks whether every comment that EXISTS has been handled; a required bot that never reviewed at all publishes nothing, contributes zero pending findings, and therefore reads as *clean* to that predicate alone. Silence and satisfaction are indistinguishable to a comment count. The participation predicate below closes that by asking the complementary question — did every REQUIRED bot actually publish a review artifact against this HEAD — and both must pass before the merge proceeds.

⚠ **This barrier, not the `automatic-review` force-done escape hatch, is what authorizes a merge.** That escape hatch (SKILL.md § "Force-done with an explicit recorded reason") lets the FIND step mark itself `done` with a required bot unproven, and the resulting record is byte-identical to one earned by a genuine pass — so nothing downstream could previously distinguish *reviewed* from *forced*. Observed on plan-marshall#1045: the fix commit was reviewed by CodeRabbit and never by the required `pr-agent`, `review_completeness` returned `participation_complete: false` with `unproven_bots: [pr-agent, sourcery]`, the step went `done` through the hatch, and `final_merge_without_asking: true` carried it to merge unchallenged. Re-deriving participation HERE rather than trusting the step record means a force-done no longer buys a merge: it defers the question to a barrier that asks it again, under an operator-configured `{barrier_mode}` rather than a leaf's own judgement.

Every mechanism that can authorize advancing a tree past a merge gate is enumerated in § "Merge-Authorization Roster" above, and this barrier is the single site at which they are checked. The `automatic-review` force-done hatch is recorded there as ALREADY HEAD-bound — via that step's own `head_dependent: true` declaration — which is why it needs no grant of its own here.

#### Read the barrier knob and the bot participation lists

Read `pre_merge_comment_barrier` off the `default:branch-cleanup` step's param object — the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (re-issue the call if the value was not retained):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id branch-cleanup
```

Extract `pre_merge_comment_barrier` from the returned `params` object as `{barrier_mode}` (default: `fail_into_loopback`). Valid values: `fail_into_loopback`, `ask`.

Read `required_bots` and `optional_bots` off the `plan-marshall:automatic-review` step's param object (the review-bot participation classification for this plan):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review
```

Extract `required_bots` and `optional_bots` from the returned `params` object as `{required_bots}` (e.g. `coderabbit,pr-agent`) and `{optional_bots}` (e.g. `sourcery`). Both default EMPTY. The two lists classify rather than admit — see [`../../automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md).

#### Re-fetch bot comments against the current HEAD

Re-run the `github_pr fetch_findings` producer. It dedups against the already-stored findings via `_existing_pr_comment_keys`, so this files ONLY genuinely-new comments as pending `pr-comment` findings — a re-fetch of an already-handled comment adds nothing:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  fetch_findings --pr-number {pr_number} --plan-id {plan_id} \
  --required-bots "{required_bots}" --optional-bots "{optional_bots}"
```

Both lists default EMPTY. **The load-bearing defence is the parser, not the quoting.** The generated
executor strips every empty-string argument before argparse sees it (`script_args = [a for a in
script_args if a]` in `.plan/execute-script.py`), so through the executor `--required-bots ""` and a
bare `--required-bots` are indistinguishable — the quotes do NOT survive to the parser. What makes the
empty case safe is that each flag declares `nargs='?'` with `const=''` (see
[`../../workflow-integration-github/SKILL.md`](../../workflow-integration-github/SKILL.md) § Canonical
invocations → `github_pr fetch_findings`), so a bare flag reads as the empty list instead of consuming
the next token as its own.

The placeholders are still double-quoted above, and should stay quoted — quoting is what keeps a
*non-empty* value with spaces as one argument, and it is the correct habit for any direct
(non-executor) invocation. Just do not read it as the empty-value defence: **never rely on quoting
alone to make an empty list safe.**

⚠ **This producer call takes NO participation-state flag beyond the two classification lists above.**
`fetch_findings` is the PRODUCER of `stale_participation_bots[]` — it declares neither
`--stale-participation-bots` nor `--not-triggered`, both of which live only on the
`review_completeness check` parser. Adding either here would document an argparse rejection (exit 2),
not a richer call. The two flags belong at § "Predicate 2" below, which is the CONSUMER.

> **GitLab provider asymmetry**: the GitLab producer `gitlab_pr fetch_findings` has NEITHER a `--required-bots` nor an `--optional-bots` flag (the same asymmetry the FIND stage already documents). On GitLab, invoke it without them; every comment is considered and none is classified.

##### UNKNOWN — the re-fetch itself failed

When this `fetch_findings` call exits **non-zero**, OR its return carries **no `participated_bots`
field at all**, the barrier's participation inputs (`participated_bots`, `stale_participation_bots`,
`refused_bots`) were never produced. A zero exit is NOT sufficient on its own: a truncated or malformed
return that omits the participation fields leaves exactly the same absent inputs as a crash, so this
trigger is symmetric with its sibling branch below rather than exit-code-only. The barrier **MUST NOT
proceed to Predicate 2** with absent participation inputs: feeding an empty `--participated-bots` to a
predicate that fails closed would render every required bot `absent`, and feeding nothing at all would
make the verdict a fiction either way. An absent input is an UNKNOWN verdict, never a `false` the
operator can act on and never a `true`.

**The same rule covers each of the new inputs, in its own way.** An absent `stale_participation_bots`
is an UNKNOWN on exactly the terms above — the field is produced by this same call, so its absence is
the same absence. The PR-wide `not_triggered` read (`ci checks pull-request-runs`, § "Predicate 2") is
a separate call and fails separately: when IT returns `status: unconfigured` or `status: error` the
observable was never read, and neither polarity may be assumed — omitting the flag would silently
assert *"a run exists"*, and passing it would silently assert *"none does"*. Both are fictions, so an
unreadable observable routes here too. The **one** case that is NOT an UNKNOWN is GitLab's structured
unsupported refusal: that is a KNOWN provider-capability gap rather than a failed read, so the barrier
omits the flag, records the gap, and proceeds — `not_triggered` is simply unavailable on that provider
and `absent` remains the correct classification there.

Log at ERROR naming which call failed, its exit code, and its stderr verbatim, under the configured
`{barrier_mode}`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-6-finalize) Pre-merge review barrier UNKNOWN: {failed_call} exited non-zero or returned no participation field (exit_code={exit_code}, stderr={stderr}) — participation inputs absent, NOT evaluating Predicate 2; pre_merge_comment_barrier={barrier_mode} (merge blocked)"
```

Then take the dedicated § "UNKNOWN disposition — blocked, and never authorizable" below. That
disposition is **NOT** the participation-incomplete branch's: it mints no authorization record and
offers no merge option under any `{barrier_mode}`. The merge NEVER proceeds on an UNKNOWN verdict.

#### Query for unhandled comments

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type pr-comment --resolution pending
```

Parse the returned `findings` list; let `{count}` be its length.

#### Predicate 2 — required-bot participation against this HEAD

Retain `participated_bots`, `stale_participation_bots`, and `refused_bots` from the `fetch_findings` return above — that call observed every bot comment on the PR at the current HEAD, so its participation sets are the freshest evidence available and no second provider round-trip is needed. `stale_participation_bots[]` is the set whose comment matched a declared publish shape but failed the `participation_requires_update` currency test; feeding it forward is what makes the barrier distinguish a review that merely predates this HEAD from a reviewer that never engaged.

One input is NOT available from the re-fetch, because no earlier call observes it — the PR-wide question of whether any `pull_request`-event workflow run exists for this PR at all. Read it here:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} checks pull-request-runs \
    --pr-number {pr_number}
```

Read `has_pull_request_run` from the returned TOON. When it is `false`, pass the bare `--not-triggered` flag on the predicate call below; omit the flag otherwise, INCLUDING for a `pull_request` run that concluded `skipped` — a skipped run was still triggered. A `status: unconfigured` or `status: error` return is an UNKNOWN input, NOT a licence to assume either polarity: take § "UNKNOWN — the re-fetch itself failed" below, which names this read among the calls that route there. On GitLab the verb returns a structured unsupported error, so the `not_triggered` refinement is unavailable there and the barrier omits the flag — a bot that published nothing resolves to `absent` as before.

Feed the retained sets to the same predicate the FIND step uses:

```bash
python3 .plan/execute-script.py plan-marshall:automatic-review:review_completeness \
  check --plan-id {plan_id} --required-bots "{required_bots}" --optional-bots "{optional_bots}" \
  --participated-bots "{participated_bots}" --refused-bots "{refused_bots}" \
  --stale-participation-bots "{stale_participation_bots}"
```

Append the bare `--not-triggered` flag to that call when and only when the read above reported `has_pull_request_run: false`. It is a `store_true` bool carrying no value of its own, so it is never interpolated and never quoted — the quoting discipline below governs the five list flags only.

This site never passes `--in-progress-bots` — the barrier has no completion-poll observation of its
own — so the five list flags above are the complete set here. Each is legitimately empty in normal
operation (no optional bots, no refusals, no stale publishes). **The load-bearing defence is the parser, not the quoting.** The generated
executor strips every empty-string argument before argparse sees it (`script_args = [a for a in
script_args if a]` in `.plan/execute-script.py`), so through the executor `--refused-bots ""` arrives
as a bare `--refused-bots` exactly as an unquoted empty placeholder would — the quotes do NOT survive
to the parser. What makes the empty case safe is that each flag declares `nargs='?'` with `const=''`
(see [`../../automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § Canonical invocations →
`review_completeness — check`), so a bare flag reads as the empty list instead of swallowing the next
token or tripping an argparse rejection at end of line.

The placeholders are still double-quoted above, and should stay quoted — quoting is what keeps a
*non-empty* value with spaces as one argument, and it is the correct habit for any direct
(non-executor) invocation. Just do not read it as the empty-value defence: **never rely on quoting
alone to make an empty list safe.**

Read `participation_complete`, `unproven_bots`, and `bot_states` from the returned TOON. The predicate is fail-closed over the REQUIRED set: a required bot that published nothing resolves to `absent` and yields `participation_complete: false`. An unproven OPTIONAL bot never blocks — a bot on a hard quota that will not clear inside this plan's lifetime belongs in `optional_bots`, which is the configured way to accept its silence, rather than in a force-done that accepts every bot's silence at once.

**Read `bot_states` before disposing of a block, because two of the seven blocking members name a different remedy than the others.** A required bot on `participated_stale` DID publish — its review merely predates this HEAD — so the productive action is a re-review trigger; and a PR-wide `not_triggered` means no reviewer was ever asked, so the productive action is to generate the trigger event at all. Both are still blocks and neither shortens the barrier, but a `{barrier_mode} == ask` prompt that renders them as *"the bot did not review"* asks the operator to accept the wrong gap. See [`../../automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md) § "Two members are refinements, not siblings — and their remedies are opposite".

> **`participation_complete: true` proves PARTICIPATION, never review QUALITY.** It means each required bot published an artifact against this diff — not that the diff was reviewed well. Do not render a satisfied quorum as a reviewed diff in any log line, `display_detail`, or PR-body claim. See [`../../automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md) § "Participation is not review quality".

##### UNKNOWN — the predicate itself failed

When the `review_completeness check` call above exits **non-zero**, or its return carries **no
`participation_complete` field at all**, the verdict is UNKNOWN — explicitly **NOT `false`** and
emphatically not `true`. The predicate never ran to a verdict, so participation is neither proven nor
disproven, and a barrier that reads a crashed gate as a pass is exactly the defect this branch exists
to make structurally impossible. An argparse rejection (exit 2), an unhandled exception, or a
truncated return are all UNKNOWN.

Log at ERROR naming which call failed, its exit code, and its stderr verbatim, under the configured
`{barrier_mode}`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-6-finalize) Pre-merge review barrier UNKNOWN: review_completeness check exited non-zero or returned no participation_complete (exit_code={exit_code}, stderr={stderr}) — participation neither proven nor disproven; pre_merge_comment_barrier={barrier_mode} (merge blocked)"
```

Then take the dedicated § "UNKNOWN disposition — blocked, and never authorizable" below. That
disposition is **NOT** the participation-incomplete branch's: it mints no authorization record and
offers no merge option under any `{barrier_mode}`. The merge NEVER proceeds on an UNKNOWN verdict, and
an UNKNOWN verdict is NEVER folded into the clean path below on a zero comment count.

#### UNKNOWN disposition — blocked, and never authorizable

Both UNKNOWN branches above — § "UNKNOWN — the re-fetch itself failed" and § "UNKNOWN — the predicate
itself failed" — route HERE, and nowhere else. This disposition is deliberately **not** the
participation-incomplete branch's: that branch is an *authorizable* blocked path, and its
`{barrier_mode} == ask` variant offers "Merge anyway (record reason)" and persists a
`barrier-ask-override` ruling over `review-barrier-gap`. Routing an UNKNOWN verdict into it would put a
merge option and a durable grant on a path that must have neither. Two independent reasons, both
load-bearing:

1. **Nothing can describe the gap.** `{count}` and `{unproven_bots}` are structurally unbound on an
   UNKNOWN path — the re-fetch or the predicate never produced them — so a prompt body or a
   `--granted-over` string built from them would report a fiction rather than the gap the operator is
   being asked to accept.
2. **A grant is durable, and outlives this pass.** A persisted `review-barrier-gap` record makes a
   LATER barrier pass at the same HEAD return `any_admissible: true` and skip its disposition
   entirely. A bypass minted here would therefore authorize past a gap nobody ever identified.

Therefore, on an UNKNOWN verdict: **no `merge-authorization grant` is issued, under any
`{barrier_mode}`, and no prompt raised here carries a merge option.** This is what makes the claim in
§ "Authorization check — the only admissible evidence on a blocked path" structurally true rather than
merely asserted — there is no reachable grant site on an UNKNOWN path, so there is nothing for a later
check to honour.

Release the merge mutex if held (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe)
per § "Merge-Mutex Hold Window" invariant 4 — a loop-back and an operator prompt are both wait
boundaries:

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
  --plan-id {plan_id}
```

Then branch on `{barrier_mode}`:

##### `{barrier_mode} == fail_into_loopback` (default)

Record `branch-cleanup` as a loop-back to `6-finalize` so the finalize pipeline re-fires and the
failed call gets a second observation, then return control to the finalize dispatcher. The
`display_detail` names the verdict as unavailable — never as a count, which does not exist here:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome loop_back \
  --loop-back-target 6-finalize --display-detail "pre-merge barrier UNKNOWN: verdict unavailable, looping back"
```

Do NOT proceed to **Merge PR**.

##### `{barrier_mode} == ask`

Fire an inline `AskUserQuestion` (branch-cleanup runs inline in the orchestrator). The mutex was
already released above. **The option set carries no merge option** — that is the whole point of this
branch existing separately from the participation-incomplete `ask` variant, which does carry one:

```text
AskUserQuestion:
  questions:
    - question: "The pre-merge review barrier could not reach a verdict. How should branch cleanup proceed?"
      header: "Branch Cleanup — Barrier verdict UNKNOWN"
      description: |
        **PR**: #{pr_number}
        **Failed call**: {failed_call} (exit_code={exit_code})

        The barrier's participation inputs were never produced, so it is
        neither proven nor disproven that this diff was reviewed. The gap
        cannot be described, so it cannot be authorized past — merging is
        not on offer here.
      options:
        - label: "Retry the barrier now"
          description: "Loop back into finalize so the failed call is re-observed"
        - label: "Defer merge"
          description: "Skip the merge; re-enter finalize later"
      multiSelect: false
```

Branch on the operator's selection:

- **"Retry the barrier now"** → take the SAME loop-back path as `fail_into_loopback` above (record
  `branch-cleanup` as `loop_back` to `6-finalize`, log, return). The mutex was already released.
- **"Defer merge"** → set `{merge_consent} = deferred`, skip the **Merge PR**, **Wait for Merge CI**,
  **Remove Worktree**, and **Switch to Base Branch** sections, emit the `mark-step-done` payload using
  **Branch C — declined by user**, and return. Log the decision:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Pre-merge review barrier UNKNOWN: operator deferred merge — verdict unavailable, no authorization sought or recorded"
  ```

#### Clean path — zero pending findings AND participation complete

The barrier is satisfied only when **both** predicates pass: `{count} == 0` (every comment against the current HEAD is handled) **and** `participation_complete: true` (every required bot published against it). Log and proceed directly to **Merge PR (if not yet merged)** below — the barrier added exactly one `fetch_findings` call, one predicate evaluation, and zero dispatches:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Pre-merge review barrier: clean — zero pending pr-comment findings, required-bot participation complete, proceeding to merge"
```

#### Authorization check — the only admissible evidence on a blocked path

**UNKNOWN is never authorizable — read this before the check below.** This check applies to exactly TWO blocked paths: **participation-incomplete** and **pending-findings**. It does NOT apply to either UNKNOWN branch (§ "UNKNOWN — the re-fetch itself failed" and § "UNKNOWN — the predicate itself failed"). Those two branches route into § "UNKNOWN disposition — blocked, and never authorizable", which is what makes them untouched by the authorization mechanism in BOTH directions: no check is run there, **no grant can be minted there** (that disposition reaches no grant site and offers no merge option under either `{barrier_mode}`), no grant is honoured there, and no bypass exists there. The minting half is the load-bearing one — a grant persisted on an UNKNOWN path would be durable, so a LATER pass at the same HEAD would read `any_admissible: true` and skip its disposition. Their absolute refusal — **the merge NEVER proceeds on an UNKNOWN verdict** — stands verbatim, mirroring `automatic-review`'s rule that the force-done hatch is UNAVAILABLE for an UNKNOWN verdict. Wiring a bypass into an UNKNOWN branch would reintroduce exactly the fail-open shape this check exists to remove: an absent verdict is not a gap an operator can knowingly authorize past, because nobody knows what the gap is.

On the two authorizable blocked paths, this check is a **bypass of the `{barrier_mode}` disposition**, so it is evaluated BEFORE that branching, not after it. Resolve the live HEAD:

```bash
git -C {worktree_path} rev-parse HEAD
```

Record the output as `{sha}`, then run the check (see `manage-status` Canonical invocations → `merge-authorization — check`). `--gap-class review-barrier-gap` names the gap THIS barrier reports — it is what makes the reply's admissibility verdict answer this barrier's question rather than some earlier gate's:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization check \
  --plan-id {plan_id} --head {sha} --gap-class review-barrier-gap
```

⚠ **Route on `any_admissible`, NEVER on `any_authorized`.** The two are different facts and the difference is load-bearing. `any_authorized` says only that SOME ruling is still bound to this tree; `any_admissible` says a ruling was granted over THIS barrier's gap and is still bound to this tree. Three of the roster's four `bound_via: grant` kinds — `pre-merge-consent`, `red-ci-override`, `rereview-timeout-override` — are granted at sites that run BEFORE this barrier, at the SAME HEAD, over a DIFFERENT gap. `pre-merge-consent` in particular is granted on every interactive "Yes, merge" immediately above, with no rebase in between, so `any_authorized` is `true` on essentially every ordinary merge. Routing on it would skip this disposition universally and let a routine merge confirmation — given before the operator was ever shown the participation gap — authorize past it. See § "Gap classes — why HEAD-binding alone is not authorization".

Read `any_admissible`, `admissible_kinds`, `inadmissible_kinds`, and `lapsed_kinds` from the returned TOON, then route:

- **`any_admissible: true`** → an operator authorization granted over THIS barrier's gap, against THIS HEAD, exists. Proceed directly to **Merge PR (if not yet merged)**, skipping the `{barrier_mode}` disposition. The mandatory decision-log line names the gap AND the authorization it is proceeding under — never a phrase that reads like a passed gate:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Pre-merge review barrier: proceeding despite {gap} under authorization {admissible_kinds} granted over review-barrier-gap at {sha}"
  ```

  `{gap}` expands to the full reported gap (the pending count plus the entire `unproven_bots` list), so it is unbounded. The step's operator-facing `display_detail` is length-bounded (≤80 chars, ASCII, no trailing period) and MUST be checked against that placeholder's **worst-case expansion**, not its literal form — so the bounded string carries the fixed-width form `merged under {kind}, gap recorded` and the full expansion lives only in the unbounded `decision`-log line above. That bounded form is emitted by **Branch E — merged under an authorization** in § "Mark Step Complete", NOT by Branch A: this path merged past a reported gap, so the step output must say so rather than render as an ordinary clean merge.

- **`any_admissible: false`** → the merge is REFUSED and the configured `{barrier_mode}` disposition below runs. **This includes the case where `any_authorized` is `true`** — a valid ruling exists but covers a different gap, which is a refusal, not a pass. Name BOTH lists when non-empty: `lapsed_kinds` shows WHICH ruling expired, and `inadmissible_kinds` shows which ruling is live but does not cover this gap, so the operator reads the prompt as an explained re-ask rather than a fresh, unexplained block — and is never left thinking their just-given consent was ignored:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Pre-merge review barrier: no authorization admissible for review-barrier-gap at {sha} — lapsed_kinds={lapsed_kinds}, valid-but-other-gap={inadmissible_kinds}; re-seek under pre_merge_comment_barrier={barrier_mode}"
  ```

**The D4 admissible-evidence rule.** The ONLY admissible evidence that an operator authorized proceeding past a reported gap is a `merge-authorization check` verdict reporting that record `admissible` at the CURRENT HEAD for the CURRENT gap class. Two independent conditions, both required: the ruling must still be bound to the tree in hand, and it must have been granted over the gap being reported. A `decision`-log entry is **NEVER admissible** authorization evidence — including one this barrier itself wrote on a preceding pass at a different HEAD. A log entry records that a ruling was made; it does not record which tree the ruling covered, so recalling one at a later HEAD is precisely the defect this check exists to remove. Do not read, quote, or reason from `decision.log` when deciding whether to proceed past a gap.

**Check-then-act constraint.** This check and the merge dispatch form a check-then-act pair. The check MUST be the LAST gate before the **Merge PR** routing, with no operator-wait, no merge-mutex release-and-re-acquire, and no re-rebase between it and the merge. When any of those intervenes, the check MUST be re-run against the freshly-resolved HEAD before merging — the same rule the Pre-Merge Confirmation Gate applies when it forbids reusing a pre-wait classifier run. The mitigation menu for this hazard class is owned by [`ref-code-quality/standards/code-organization.md`](../../ref-code-quality/standards/code-organization.md) § TOCTOU / check-then-act hazards.

#### Blocked path — participation incomplete

When `participation_complete: false`, the merge is blocked even if `{count} == 0`. **Zero pending comments is exactly what an unreviewed diff looks like**, so this branch must never be collapsed into the clean path on a comment count alone.

This is an **authorizable** blocked path: § "Authorization check — the only admissible evidence on a blocked path" above has already run, and this disposition fires only when it returned `any_admissible: false` for `review-barrier-gap` — including when `any_authorized` was `true` under a ruling granted over some other gap.

Branch on `{barrier_mode}` using the SAME two branches as the unhandled-comment block below — `fail_into_loopback` (default) loops back into `6-finalize` so `automatic-review` re-fires and re-awaits the unproven bot, and `ask` prompts the operator. Both branches carry the same merge-mutex release obligations documented there; only the recorded message differs:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Pre-merge review barrier: required-bot participation incomplete — unproven_bots={unproven_bots}, pending pr-comment findings={count} — pre_merge_comment_barrier={barrier_mode} (merge blocked)"
```

⚠ **A loop-back here is only productive if the unproven bot can still produce evidence.** Whether it can is a per-bot, per-repository property: a bot with no auto-review-on-push trigger in this repository's caller workflow will never re-review a loop-back fix commit on its own, and `re_review_on_loopback` (default `false`) governs whether an explicit trigger comment is posted for it. If neither holds, the loop-back re-enters this barrier with the same verdict. Fix the trigger, or move the bot to `optional_bots` — do not answer a structurally-unprovable bot with repeated loop-backs. See [`../../automatic-review/standards/pr-agent.md`](../../automatic-review/standards/pr-agent.md) § "Signal calibration" for how to read a given repository's caller.

#### Blocked path — one or more pending findings

When the pending list is non-empty, the merge is blocked. This is the second **authorizable** blocked path: § "Authorization check — the only admissible evidence on a blocked path" above has already run, and the branches below fire only when it returned `any_admissible: false` for `review-barrier-gap` — including when `any_authorized` was `true` under a ruling granted over some other gap. Branch on `{barrier_mode}` (these are the branches the participation-incomplete block above also uses):

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
- **"Merge anyway (record reason)"** → RE-ACQUIRE the merge mutex and re-validate (per the release-before-wait note above), decision-log at WARNING naming the unhandled count and the operator's reason, **then persist the ruling as a HEAD-bound authorization**, then continue to **Merge PR (if not yet merged)** below:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-6-finalize) Pre-merge comment barrier: operator chose merge-anyway with {count} unhandled comment(s) — reason: {reason}"
  ```

  The log line above is the honest record of what the operator decided and is kept verbatim — recording was never the defect. What it cannot do is *authorize*: it names no tree, so a later barrier pass at a different HEAD could recall it and merge a tree the operator never saw (the plan-marshall#1067 shape). Bind the ruling to the tree it was granted over. Because the re-acquire and re-validation above may have re-rebased, resolve the live HEAD **after** them:

  ```bash
  git -C {worktree_path} rev-parse HEAD
  ```

  Record the output as `{sha}`, then grant (see `manage-status` Canonical invocations → `merge-authorization — grant`):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
    --plan-id {plan_id} --kind barrier-ask-override --head {sha} --gap-class review-barrier-gap \
    --granted-over "{count} unhandled, unproven_bots={unproven_bots}" --reason "{reason}"
  ```

  `--granted-over` carries the gap AS THE BARRIER REPORTED IT, so a later reader can re-evaluate the ruling against a later delta rather than re-deriving what the operator was shown. `--gap-class review-barrier-gap` is the machine token for the same fact — this row's `authorizes:` claim, and the ONE class the check above admits, which is why this is the only ruling that can bypass this barrier's disposition. A re-grant at a new HEAD overwrites this record — that overwrite IS the sanctioned re-seek.

  This path merged past a reported gap, so it emits **Branch E — merged under an authorization** in § "Mark Step Complete" (with `{kind}` = `barrier-ask-override`), NOT Branch A.

- **"Defer merge"** → set `{merge_consent} = deferred`, skip the **Merge PR**, **Wait for Merge CI**, **Remove Worktree**, and **Switch to Base Branch** sections, emit the `mark-step-done` payload using **Branch C — declined by user**, and return (the mutex was already released before the prompt). Log the decision:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Pre-merge comment barrier: operator deferred merge with {count} unhandled comment(s) — re-enter finalize later"
  ```

### Merge PR (if not yet merged)

**Only if `state == open` AND the pre-merge gate above resolved to `{merge_consent} == explicit_yes`** (the `final_merge_without_asking == true` bypass also sets `{merge_consent} = explicit_yes`):

#### Merge routing (`use_merge_queue`)

Read `use_merge_queue` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (default: `false`). This routing branch is documented BEFORE the merge dispatch it selects (bypass-before-dispatch ordering).

##### The dispatch set is CLOSED

`ci pr safe-merge` and `ci pr merge-queue` are the **only** merge-shaped dispatches this step may issue, on any code path, under any parameter combination. The set has exactly two members and admits no third:

| Verb | Reachable from this step | Selected by |
|------|--------------------------|-------------|
| `ci pr safe-merge` | yes | `use_merge_queue == false` |
| `ci pr merge-queue` | yes | `use_merge_queue == true` |
| `ci pr merge` | **never** | — not reachable under any condition |
| `ci pr auto-merge` | **never** | — not reachable under any condition |

`ci pr merge` and `ci pr auto-merge` are **not reachable from this step under any condition**. Neither is a fallback for the other's failure, neither is a degraded mode for a stuck PR, and neither is reachable when the enqueue fails — the enqueue's error path aborts (see the no-fallback contract below), it does not re-route. A branch-protection fallback sequence at this layer is unnecessary in the first place: `pr safe-merge` carries the poll-then-merge path and the stuck-state admin fallback internally. Do not reintroduce either verb here as a recovery path. The two verbs remain part of the `ci pr` surface for other callers — the closure is over THIS step's dispatch set, not over the provider API.

**Observability (mandatory)** — immediately after the routing predicate above is evaluated and BEFORE the dispatch it selects, emit one decision-log line naming the bound `use_merge_queue` value, its provenance, and the verb about to be dispatched. This line is what makes "which verb did this run actually merge with?" answerable from the log alone, rather than inferred from downstream side effects:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup merge routing: use_merge_queue={use_merge_queue} (provenance: default:branch-cleanup step-params object, Conflict-Severity Classifier one-stop read) — dispatching {ci pr safe-merge | ci pr merge-queue} for PR #{pr_number}"
```

The routing itself:

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

  Parse the returned TOON. `status: success` with `enqueued: true` is a **corroborated** claim on both providers — it is reported only when a queue actually exists to be enqueued onto, so a repo with no configured queue returns `status: error` here rather than a green `enqueued: true` for a PR that joined no queue. The *mechanism* behind that outcome is provider-shaped, and the difference matters when reading what a failed enqueue left behind: on **GitHub** the verb probes the PR's own base branch **before** the `gh` call and refuses without ever issuing it, so an ineligible target incurs no side effect; on **GitLab** there is **no probe** — the verb POSTs to the dedicated merge-train endpoint and reads its HTTP 403/404 as the refusal, so a failed GitLab enqueue has already issued that POST (see [`../../tools-integration-ci/standards/pr-operations.md`](../../tools-integration-ci/standards/pr-operations.md) § "Merge-Queue PR"). `enqueued: true` still means only that the PR reached the queue — **it is not a merge**. Set `{merge_mechanism} = merge_queue` AND `{merge_landed} = false` — the enqueue is not a merge, so the landing gate below is the only site on this path that may raise `{merge_landed}` to `true`. Then proceed to § "Wait for the Queue Merge to Land (bounded)" below, which is the gate that decides whether the post-merge tail may run at all. On `status: error` (e.g. a GitLab merge-train-ineligible project, or a queue-engagement / auth-scope failure), log the **actionable** error and abort — do NOT silently fall back to an immediate merge, since the operator opted into queue serialization for a reason. The abort message MUST name BOTH remedies so the operator is never left with a bare error: (a) **disable `use_merge_queue`** (set it back to `false` via `manage-config … step set --step-id default:branch-cleanup --param use_merge_queue --value false`) to merge immediately via `pr safe-merge`, or (b) **run the marshall-steward merge-queue provisioning step** (Configuration → Merge Queue) to configure the platform merge queue so the enqueue succeeds:

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

On success, `pr safe-merge` returns a corroborated `merged: true` — the verb re-reads PR state after the merge and asserts the state the chosen strategy actually produces, rather than deriving the claim from the CLI exit code (see [`../../tools-integration-ci/standards/pr-operations.md`](../../tools-integration-ci/standards/pr-operations.md) § "Safe-Merge PR"). Set `{merge_mechanism} = pr_safe_merge` and `{merge_landed} = true`, then continue to **Wait for the Queue Merge to Land (bounded)** below, which short-circuits on this path because the merge has already landed.

### Wait for the Queue Merge to Land (bounded)

This gate is documented BEFORE the post-merge tail it bypasses (bypass-before-dispatch ordering). It governs **every** section that follows: **Wait for Merge CI**, **Remove Worktree**, **Switch to Base Branch, Pull, and Delete Local Branch**, the terminal merge-mutex release, and `prune-local-and-remote-ref`. Each of those is a *post-merge* action — they assume the PR has landed on the base branch. On the `use_merge_queue == true` path that assumption is false at the moment the enqueue returns: `enqueued: true` says the PR joined the queue, not that the queue merged it. Running the tail on a still-queued PR prunes the head branch (and the remote-tracking ref) out from under a merge the platform has not performed yet, and pulls a base branch that does not contain the commit.

**Short-circuit — `{merge_mechanism} == pr_safe_merge`**: the merge landed synchronously and was corroborated by the verb. `{merge_landed}` is already `true`. Skip this entire section and proceed to **Wait for Merge CI**.

**Applies only when `{merge_mechanism} == merge_queue`.**

#### Read the landing budget

Reuse `merge_queue_wait_budget_seconds` — the SAME knob that bounds the FIFO admission poll — off the one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above. It is reused deliberately rather than given a sibling knob: both bounds answer "how long may this step block on a queue it does not control", and one operator-facing number is the honest surface for that. Record it as `{wait_budget}` (default: `1800`, ~30 minutes).

The budget is applied **separately** to each of the two waits, so a run that spends the full admission budget and then the full landing budget blocks for up to `2 × {wait_budget}`. The two exhaustion outcomes also differ, and the knob's `configurable:` description names both: admission exhaustion escalates via the last-resort `AskUserQuestion`, whereas landing exhaustion takes the **Landing-gate failure path** below — WARNING, mutex release, Branch F, no prompt.

#### Landing poll loop

Record the wall-clock start time. Then poll the PR's state until it reports merged or the budget is exhausted. Each poll is a SINGLE Bash call — there is NO `for`/`while`/`until` shell loop; pace successive polls with a SINGLE standalone `sleep {interval}` Bash call (one command, e.g. `sleep 30`), exactly as the FIFO admission loop above does:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view \
    --pr-number {pr_number}
```

The poll keys on `--pr-number`, **never** on `--head`, and that is load-bearing rather than stylistic: the platform auto-deletes the head branch as the queue merges (which is why the enqueue above needs no `--delete-branch`). A `--head`-keyed poll would therefore stop resolving at exactly the moment `state == merged` became observable — the gate could only ever time out or read an error, never see the landing it exists to confirm. The PR number survives the branch deletion. See [`../../tools-integration-ci/standards/pr-operations.md`](../../tools-integration-ci/standards/pr-operations.md) § "`--head` is not a landing-poll selector".

Parse `state` from the returned TOON and branch:

- **`state == merged`** → the platform merged the queued PR. Set `{merge_landed} = true`, exit the poll loop, and proceed to **Wait for Merge CI**. Log the landing:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup queue-landing gate: PR #{pr_number} merged by the platform merge queue after {elapsed}s (budget {wait_budget}s) — post-merge tail authorized"
  ```

- **`state == open`** (still queued, or dequeued and re-queued) → check the elapsed wall-clock against `{wait_budget}`. **Elapsed < `{wait_budget}`** → pace with a single standalone `sleep {interval}` Bash call, then re-issue the single `pr view` call above. **Elapsed >= `{wait_budget}`** → the budget is exhausted; take the **Landing-gate failure path** below.
- **`state == closed`** (the queue dequeued the PR without merging — its re-test went red against the latest base, or an operator removed it) → take the **Landing-gate failure path** below. This is NOT a merge and must never be read as one.
- **`status: error`** on the `pr view` call → take the **Landing-gate failure path** below. An unobservable state is not a landed merge; the gate fails closed, exactly as the pre-merge review barrier does on an UNKNOWN verdict.

Also honour the `merge_hold_budget_seconds` bound from § "Merge-Mutex Hold Window" invariant 2 against elapsed-since-`{hold_start}`: when the landing wait would push the held duration past that budget, take the **Landing-gate failure path** below rather than continuing to hold the mutex.

#### Landing-gate failure path

`{merge_landed}` stays `false`. The PR is enqueued but not merged, so **none of the post-merge tail may run**: no CI wait, no worktree removal, no `switch-and-pull`, and — most importantly — **no `prune-local-and-remote-ref`**, because deleting the head branch or its remote-tracking ref while the platform still has the PR queued destroys the very ref the queue merge needs.

1. Log the outcome at WARNING, naming the terminal observation and the budget:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Branch cleanup queue-landing gate: PR #{pr_number} enqueued but not merged after {wait_budget}s (terminal observation: {state_or_error}) — skipping the post-merge tail; the head branch and its remote-tracking ref are left intact for the queue. Re-enter finalize once the queue merge lands."
   ```

2. **Release the merge mutex** if held (`merge_lock release --plan-id {plan_id}`; idempotent + foreign-safe) per § "Merge-Mutex Hold Window" invariant 4. The plan is no longer inside the merge-to-main critical section — the platform owns the merge from here — so holding the lock would block every other plan for a wait this plan cannot shorten:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \
     --plan-id {plan_id}
   ```

3. Emit the `mark-step-done` payload using **Branch F — enqueued, merge not yet landed** in § "Mark Step Complete" and **return**. Do NOT fall through to **Wait for Merge CI**.

This failure path is a bounded, honest stop — not an error. The enqueue succeeded and the platform will merge on its own schedule; what this run cannot do is claim the merge landed or clean up as though it had.

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

**Reached only when `{merge_landed} == true`** — § "Wait for the Queue Merge to Land (bounded)" returns without pruning on its failure path, so a still-queued PR never reaches this dispatch.

Read `use_merge_queue` off the same one-stop `step-params get` `params` object resolved in the **Conflict-Severity Classifier** section above (default: `false`). It determines who deleted the remote head branch, and therefore which `prune-local-and-remote-ref` outcome is the expected one rather than a symptom.

**Observability (mandatory)** — immediately after the predicate above is evaluated and BEFORE the prune dispatch it characterizes, emit one decision-log line naming the bound value, its provenance, and the expected remote-side state. Without it a `status: partial` prune is indistinguishable from a cleanup gap:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup post-merge cleanup: use_merge_queue={use_merge_queue} (provenance: default:branch-cleanup step-params object, Conflict-Severity Classifier one-stop read) — remote head branch deleted by {ci pr safe-merge --delete-branch | the platform merge queue}, dispatching prune-local-and-remote-ref for {head_branch}"
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

- **`state == open`, `use_merge_queue == false`** (we just merged this run via `pr safe-merge --delete-branch`): the remote branch is already gone. `prune-local-and-remote-ref` deletes the local branch AND prunes the now-stale remote-tracking ref.
- **`state == open`, `use_merge_queue == true`** (the platform merged the queued PR, corroborated by the landing gate above): the remote branch was deleted by the platform, not by this step. The observable result is the same as the row above — `prune-local-and-remote-ref` deletes the local branch and prunes the stale tracking ref — but a `status: partial` here is the *expected* shape when the local clone had already dropped the tracking ref, not evidence that the merge did not happen.
- **`state == merged`** (PR was already merged on a prior run, possibly without `--delete-branch`): the remote branch may still exist. `prune-local-and-remote-ref` deletes the local branch; the remote-tracking ref may or may not be present — the internal `show-ref` guard produces a `status: partial` no-op when the tracking ref is already absent on this re-entry path.

### Log Completion (PR Mode)

The completion line MUST render the merge clause from `{merge_mechanism}` rather than asserting a bare `merged PR #{pr_number}`. An unconditional claim is false on two of the three paths: on the merge-queue path this step never merged anything (the platform did, and this step only corroborated it), and on the `state == merged` re-entry path this run merged nothing at all. Pick exactly one clause:

| `{merge_mechanism}` | Merge clause |
|---------------------|--------------|
| `pr_safe_merge` | `merged PR #{pr_number} directly via pr safe-merge` |
| `merge_queue` | `PR #{pr_number} enqueued via pr merge-queue and corroborated merged by the platform queue` |
| *(unrecorded — `state == merged` on entry)* | `PR #{pr_number} was already merged before this run` |

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup complete: {merge_clause}, pulled latest on {base_branch}"
```

This line is a work-log message and carries no length bound; the bounded rendering of the same distinction is **Branch A** in § "Mark Step Complete".

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

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the cleanup outcome. The payload differs by branch and must match the branch actually executed above.

### Structured facts recorded here

This step declares the `records_facts` union `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed`. The union is a step-level declaration, NOT a per-branch mandate — each of the six `--outcome done` call sites below (**Branches A through F**) records only the **honest subset** its own path produced, per [ext-point-finalize-step.md](../../extension-api/standards/ext-point-finalize-step.md) § "Structured step facts". The path conditions:

| Fact | Recorded iff |
|------|--------------|
| `action` | The executing path reached **Rebase Branch onto Base** and parsed its `worktree-rebase-to` TOON. The value is that TOON's `action` — `noop` when the rebase replayed nothing, `rebased` when it moved HEAD. A path that never rebased records NO `action`; its absence is the honest signal, not a gap to fill. |
| `upstream_commit_count` | Same condition as `action` — it is read from the same rebase-path payload. |
| `merge_mechanism` | The merge actually **landed** and was corroborated (`{merge_landed} == true`). Value is `pr_safe_merge` when `ci pr safe-merge` returned a corroborated `merged: true`, or `merge_queue` when § "Wait for the Queue Merge to Land (bounded)" observed the platform queue merge the enqueued PR. A path that enqueued but whose merge never landed (**Branch F**) records NO `merge_mechanism` — dispatching a merge-shaped verb is not the same fact as a merge, and that branch reports the enqueue in its `display_detail` instead. A path that never merged at all likewise records none. |
| `work_performed` | **Every** `--outcome done` call site below, `true` or `false`, never omitted — the one declared exception to the honest-subset rule. |

`--display-detail` on every branch is a **rendering of the facts that branch recorded**. In particular it MUST NOT assert a rebase or a merge the recorded facts do not support — a fixed literal claiming a rebase unconditionally is exactly what the per-branch facts exist to prevent. It MUST equally not render an *enqueue* as a merge, nor a queue merge as a merge this step performed: `merge_mechanism == merge_queue` records that the PLATFORM merged the PR and this step corroborated the landing, so its rendering says so rather than reusing the direct-merge phrasing.

**Length discipline.** Every `--display-detail` below is bounded (≤80 chars, ASCII, no trailing period) and MUST be checked against its placeholders' **worst-case expansion**, never its literal form. **This rule binds the figures published here too** — every count below is re-derived by measuring the expanded string, never transcribed. The two placeholder-bearing branches:

- **Branch A** — worst case `already current with base, queue-merged, corroborated, cleanup complete`, **71 chars**: the longest rebase clause combined with the longest merge clause.
- **Branch E** — worst case `merged under barrier-ask-override, gap recorded`, **47 chars**. `{kind}` does NOT range over the whole `bound_via: grant` set: this site checks with `--gap-class review-barrier-gap`, and `barrier-ask-override` is the only § "Merge-Authorization Roster" row whose `authorizes:` is `review-barrier-gap`, so it is the only value `admissible_kinds` can yield here — and it is also the literal the `ask` path substitutes. The longest grant kind overall is `rereview-timeout-override` (25 chars, which would expand to 52), but it authorizes `rereview-timeout` and can never be admissible at this site.

Branch B carries one placeholder (`{base_branch}`) and is checked the same way. Branches C, D, and F carry none, so each is its own worst case; the longest of those three is Branch F at **59 chars**.

The `loop_back` call site in the pre-merge comment barrier is deliberately untouched — it is not a `done` record and carries no fact obligation.

**Branch A — PR mode (rebase + landed merge + cleanup)** (PR was rebased onto base, the merge **landed** and was corroborated, base branch pulled, feature branch deleted locally and on remote, worktree removed). Branch A is the **clean-barrier** payload: use it only when the pre-merge review barrier resolved via its clean path. When the merge proceeded past a reported gap under an authorization, emit **Branch E** instead. When the PR was enqueued but the queue merge never landed, emit **Branch F** instead — Branch A requires `{merge_landed} == true`. It is the only clean-path branch that reaches both the rebase and a landed merge, so it carries all four facts:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --fact action={action} \
  --fact upstream_commit_count={upstream_commit_count} \
  --fact merge_mechanism={merge_mechanism} \
  --fact work_performed=true \
  --display-detail "{rendered_detail}"
```

Render `{rendered_detail}` as `"{rebase_clause}, {merge_clause}, cleanup complete"`, composing the two clauses independently from the two facts: `action` decides the rebase clause and `merge_mechanism` decides the merge clause. Both axes must be rendered as clauses rather than interpolated raw — a single-axis form such as `merged via {merge_mechanism}` reads as "this step merged it via the queue" and so claims for the queue path a merge this step never performed:

| `action` | Rebase clause |
|----------|---------------|
| `rebased` | `rebased onto base` |
| `noop` | `already current with base` |

| `merge_mechanism` | Merge clause |
|-------------------|--------------|
| `pr_safe_merge` | `merged directly` |
| `merge_queue` | `queue-merged, corroborated` |

The `merge_queue` clause is deliberately not the word "merged" alone: the platform performed the merge and this step observed it land, which is a different fact from this step having merged the PR itself. Worst-case expansion is the 71-char string checked in § "Length discipline" above.

**Branch B — local-only mode** (no PR was created; only the local switch-to-base-branch was performed). This path never reaches the rebase and never merges, so it records neither `action`, nor `upstream_commit_count`, nor `merge_mechanism` — but it DID perform its characteristic local cleanup, so `work_performed=true`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --fact work_performed=true \
  --display-detail "local-only: switched to {base_branch}"
```

**Branch C — declined by user** (interactive prompt was rejected; cleanup was not performed). Nothing was rebased, merged, or cleaned up, so `work_performed=false` and no other fact is recorded:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --fact work_performed=false \
  --display-detail "declined by user"
```

**Branch D — no PR found** (PR mode, `pr view` returned `status: error` — there is no PR for the current branch, so there is nothing to clean up on the remote side). The path exits before the rebase and before any merge, so it records `work_performed=false` alone:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --fact work_performed=false \
  --display-detail "no PR, nothing to clean up"
```

**Branch E — merged under an authorization** (PR mode, but the pre-merge review barrier reported a gap and the merge proceeded anyway — either because § "Authorization check — the only admissible evidence on a blocked path" returned `any_admissible: true`, or because the operator selected "Merge anyway (record reason)" in the `{barrier_mode} == ask` branch and a `barrier-ask-override` ruling was granted). This branch REPLACES Branch A on those paths: Branch A's rendered detail describes an ordinary rebase-and-merge and so reads exactly like a passed gate, which is the phrasing the barrier's decision-log rule forbids, and an authorized bypass that renders as a clean merge is invisible to the operator reading the step output.

`{kind}` is the authorization kind actually relied on (the single value of `admissible_kinds` on the check path, or `barrier-ask-override` on the ask path). The form is fixed-width by construction — the unbounded gap expansion belongs to the `decision`-log line only, never here.

This branch reaches the same rebase and merge Branch A does, so it records the same four facts; only the rendered detail differs, and it differs precisely because the gap must stay visible:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --fact action={action} \
  --fact upstream_commit_count={upstream_commit_count} \
  --fact merge_mechanism={merge_mechanism} \
  --fact work_performed=true \
  --display-detail "merged under {kind}, gap recorded"
```

**Branch F — enqueued, merge not yet landed** (PR mode, `use_merge_queue == true`: the rebase, force-push, and `ci pr merge-queue` enqueue all succeeded, but § "Wait for the Queue Merge to Land (bounded)" did not observe the queue merge the PR within `merge_queue_wait_budget_seconds` — or observed it dequeued, or could not observe its state at all). The post-merge tail was skipped and the merge mutex released; the head branch and its remote-tracking ref are intact.

This branch reached the rebase, so it records `action` and `upstream_commit_count`. It performed real work — rebase, force-push, enqueue — so `work_performed=true`. It records **no `merge_mechanism`**, because no merge landed: recording `merge_queue` here would assert exactly the fact this branch exists to deny, and would make Branch F indistinguishable from Branch A to any consumer reading the facts rather than the detail string:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \
  --fact action={action} \
  --fact upstream_commit_count={upstream_commit_count} \
  --fact work_performed=true \
  --display-detail "enqueued to merge queue, merge not landed, cleanup deferred"
```

The detail is a fixed literal (59 chars, no placeholders), so its worst case is its literal form. Re-entering finalize once the queue merge lands takes the `state == merged` path, which performs the deferred local cleanup.
