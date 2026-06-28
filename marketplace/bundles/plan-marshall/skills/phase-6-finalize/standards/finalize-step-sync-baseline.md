---
name: default:finalize-step-sync-baseline
description: Early baseline rebase — rebase the worktree feature branch onto origin/{base_branch} at the start of finalize
order: 3
mutates_source: true
default_on: true
presets:
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
configurable:
  - key: auto_rebase_threshold
    default: no_overlap_only
    description: Gate the pre-rebase auto-proceed decision — no_overlap_only permits auto-rebase only when the rebase would touch a disjoint file set; auto_resolvable also permits an auto-reconcilable overlap; never always defers to the operator.
---

# Sync Baseline (Early Rebase)

Pure executor for the `sync-baseline` finalize step. Rebases the worktree feature branch onto `origin/{base_branch}` at the very start of the phase-6-finalize pipeline (`order: 3`, before `pre-push-quality-gate` at `order: 5`), so every downstream local quality gate and remote CI run validates the actual to-be-landed tree rather than a tree that predates upstream commits landed during the finalize window. This narrows the stale-tree window: when `origin/{base_branch}` advanced between plan creation and finalize, the local gates now run against the rebased history instead of discovering the divergence only at the late `branch-cleanup` rebase (`order: 70`).

The step reuses the existing `git-workflow` verbs unchanged — `baseline-reconcile --no-emit` to classify the rebase, and `worktree-rebase-to` to perform it. It introduces NO new git primitive. It performs **NO force-push and NO `ci wait`**: at `order: 3` the feature branch has not yet been pushed (`default:push` is `order: 10`) and no PR exists (`default:create-pr` is `order: 20`), so there is no remote ref to update and no CI to wait on. The late `branch-cleanup` rebase (`order: 70`) remains the correctness backstop: in the common case where no new commits landed during the finalize window, that late rebase degrades to `action: noop`.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-sync-baseline` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion: a clean rebase (or a no-op when the branch is already up to date) records `outcome=done`; a conflict or a failed rebase records `outcome=failed` and halts the phase so the operator can resolve the in-progress rebase in the worktree.

## Inputs

- `{worktree_path}` and `{main_checkout}` have been resolved at finalize entry (see SKILL.md Step 0 — Resolve Worktree and Main Checkout Paths). This document MUST NOT re-resolve them. The `git-workflow` verbs invoked below identify the worktree internally via `--plan-id {plan_id}` (which auto-resolves through `manage-status get-worktree-path`); no path forwarding is required at the call sites.
- `base_branch` — the plan's target branch, available from references context (`base_branch` field, written at `phase-1-init`). It is consumer-configured via `project.default_base_branch` with a per-plan override via `references.base_branch`. Read it from references context if not already in scope:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
    get-context --plan-id {plan_id}
  ```

  Extract `base_branch` from the returned context as `{base_branch}`.
- `auto_rebase_threshold` — this step's own configurable knob (declared in the `configurable:` frontmatter above, default `no_overlap_only`), read from the plan-local execution-manifest step-params snapshot:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
    step-params get --plan-id {plan_id} --phase 6-finalize --step-id finalize-step-sync-baseline
  ```

  Read `auto_rebase_threshold` off the returned `params` object as `{threshold}`. Default: `no_overlap_only`. Accepted values (the same set as `branch-cleanup`'s pre-rebase gate):

  - `no_overlap_only` — auto-proceed only when the classifier returns `classification: no_overlap`.
  - `auto_resolvable` — also auto-proceed when the classifier returns `classification: overlap_no_content_conflict` AND `auto_reconciled: true`.
  - `never` — always prompt the operator; skip the classifier entirely.

## Execution

### Classify the rebase

Dispatch the existing `baseline-reconcile` probe to classify the upcoming rebase against `origin/{base_branch}`. `--no-emit` suppresses Q-Gate finding emission (those are a phase-2-refine concern; this step consumes the classification directly). The probe performs only `fetch + diff + merge-tree` and never mutates the working tree:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  baseline-reconcile --plan-id {plan_id} --no-emit
```

Parse the returned TOON for `classification`, `auto_reconciled`, `conflict_count`, `conflicts[]`, and `upstream_commit_count`.

If the script exits non-zero (per the **Exit-code convention** above) → STOP and return an error TOON to the dispatcher carrying the stderr verbatim. Do NOT silently fall back to `needs_user` on classifier failure — a broken probe is a different signal than a real conflict and must surface as an error.

**Threshold bypass (`{threshold} == never`)**: when the threshold is `never`, skip the classifier dispatch entirely and force `{decision} = needs_user`. Log the bypass and proceed to the **Pre-rebase gate**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Sync baseline: classifier bypassed (threshold=never), pre-rebase gate will fire"
```

### Compute the gate decision

Apply the following rules in order; the first match wins:

- `classification == no_overlap` → `{decision} = auto_proceed` (regardless of threshold, except `never` which already short-circuited above).
- `classification == overlap_no_content_conflict` AND `auto_reconciled == true` AND `{threshold} == auto_resolvable` → `{decision} = auto_proceed`.
- `classification == overlap_no_content_conflict` AND (`auto_reconciled == false` OR `{threshold} == no_overlap_only`) → `{decision} = needs_user`.
- `classification == overlap_with_content_conflict` → `{decision} = needs_user` (genuine conflict requiring human resolution).

Log the classifier decision for grep-ability and retrospective audit:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Sync baseline classifier: classification={classification}, auto_reconciled={auto_reconciled}, threshold={threshold}, decision={decision}, upstream_commits={upstream_commit_count}"
```

### Pre-rebase gate

The pre-rebase gate decides whether the rebase fires silently or prompts the operator. It is **bypassed when `{decision} == auto_proceed`** (clean or auto-resolvable rebase under a permissive threshold) and **mandatory when `{decision} == needs_user`** (genuine conflict, or a classifier-bypassed `never` threshold).

#### Auto-proceed path (`{decision} == auto_proceed`)

Skip the `AskUserQuestion` block entirely, log the bypass, and proceed to **Rebase the worktree branch**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Sync baseline: pre-rebase auto-proceed (classification={classification}), gate bypassed"
```

#### Interactive path (`{decision} == needs_user`)

Fire an `AskUserQuestion` before any destructive rebase. The rebase is local-only — there is no force-push or merge at this order, so the prompt covers only the rebase itself:

```
AskUserQuestion:
  questions:
    - question: "Rebase the feature branch onto origin/{base_branch} before the finalize quality gates run?"
      header: "Sync Baseline — Pre-rebase"
      description: |
        **Branch**: {head_branch} → {base_branch}
        **Classifier**: classification={classification}, auto_reconciled={auto_reconciled}, upstream_commits={upstream_commit_count}

        origin/{base_branch} advanced since this plan's baseline. Rebasing now
        makes the downstream local quality gates and CI validate the actual
        to-be-landed tree. This is a LOCAL rebase only — no force-push and no
        CI wait happen at this step (the branch is not yet pushed).
      options:
        - label: "Yes, rebase"
          description: "Rebase the worktree branch onto origin/{base_branch} now"
        - label: "No, skip"
          description: "Leave the branch as-is; the late branch-cleanup rebase remains the backstop"
      multiSelect: false
```

**If the operator selects "No, skip"**: skip the rebase and record a no-op outcome via **Mark Step Complete (Skipped)** below. Log the decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Sync baseline skipped: operator declined at pre-rebase gate — late branch-cleanup rebase remains the backstop"
```

### Rebase the worktree branch

Reached on the auto-proceed path, or when the operator selected "Yes, rebase". Dispatch the rebase via the structured `worktree-rebase-to` verb so the result is consumed as a TOON payload:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
  worktree-rebase-to --plan-id {plan_id} --base {base_branch}
```

Parse the returned TOON and branch on `status`:

- `status: success` → continue to **Mark Step Complete (Success)**. The `action` field distinguishes `noop` (the branch was already at `origin/{base_branch}`, nothing to rebase) from `rebased` (the rebase produced a new history). Both are success.
- `status: conflict` → ABORT the step with `outcome=failed`. The rebase is left in progress with conflict markers so the operator can resolve them in the worktree. The classifier's merge-tree probe is best-effort — overlapping renames and a few other rare cases produce a clean probe but a real-rebase conflict. Log the returned `conflicts[]` file list and record the failure via **Mark Step Complete (Failure)**:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Sync baseline: worktree-rebase-to onto {base_branch} produced conflicts in {conflicts} — resolve manually in the worktree (rebase is left in progress) and re-run finalize"
  ```

  Do NOT proceed to any downstream step. The conflicted rebase state is intentionally preserved so the operator can run `git rebase --continue` or `git rebase --abort` as appropriate.

- `status: error` → ABORT the step with `outcome=failed` using the returned `error` and `message` fields. Record the failure via **Mark Step Complete (Failure)**:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Sync baseline: worktree-rebase-to failed - {error}: {message}"
  ```

Log the successful rebase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Sync baseline: rebased onto origin/{base_branch} (action={action}, upstream_commits={upstream_commit_count})"
```

## Mark Step Complete

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Mark Step Complete (Success)** — the rebase completed (`action: rebased`) or was a no-op (`action: noop`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-sync-baseline --outcome done \
  --display-detail "rebased onto origin/{base_branch} (action={action})"
```

**Mark Step Complete (Skipped)** — the operator declined the rebase at the pre-rebase gate. The step still records `done` with an honest detail (no rebase was performed; the late `branch-cleanup` rebase remains the backstop):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-sync-baseline --outcome done \
  --display-detail "rebase skipped by operator; branch-cleanup remains the backstop"
```

**Mark Step Complete (Failure)** — the rebase produced a conflict (`status: conflict`) or failed (`status: error`). The dispatcher's failure handling halts the phase on `outcome=failed`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-sync-baseline --outcome failed \
  --display-detail "rebase onto origin/{base_branch} failed: {error_or_conflict_summary}"
```
