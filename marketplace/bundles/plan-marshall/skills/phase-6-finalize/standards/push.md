---
name: default:push
description: Push the converged branch
order: 10
mutates_source: false
---

# Push

Pure executor for the `push` finalize step. A **pure push barrier**: it carries NO commit logic. Every deliverable was committed on the feature branch during phase-5-execute, and the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) commits each `mutates_source: true` step's output before this barrier runs — so the steady-state expectation here is a **clean working tree**. This step asserts the tree is clean and pushes the converged branch to remote; it produces NO commit. The squash-merge-at-merge convention is unchanged: per-deliverable feature-branch commits collapse into a single squashed commit on `main` at merge.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `push` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion and records `outcome=done` — the `display_detail` payload reports the push outcome. The `commit_and_push == false` (local-only) case is handled at composition time by the manifest's `commit_push_disabled` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`), so this step is never dispatched in that case.

## Inputs

- `commit_and_push` from phase-5-execute config (boolean, default `true`). The `false` (local-only) value is filtered out at manifest composition time by the `commit_push_disabled` pre-filter and never reaches this executor — so whenever this step runs, `commit_and_push` is `true` and the converged feature branch is to be pushed.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST use `git -C {worktree_path}`.

### Freshness precondition

Before the push runs, invoke the deterministic freshness gate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  pre-commit-verify-freshness --plan-id {plan_id}
```

Parse `status` from the returned TOON. The contract is **fail-closed**: only `status: fresh` permits the executor to proceed. Any other status halts `push` immediately — record `outcome=failed` with a `display_detail` carrying the reason, the current working-tree `worktree_sha`, and the ledger path so the orchestrator's recovery path has the structured signal it needs to dispatch a fresh `verify` run. The gate is tier-agnostic and build-tool-agnostic — it scans the unified change-ledger for a `kind=build` entry matching the current `worktree_sha`; see `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md`.

| `status` value | `push` action |
|----------------|---------------|
| `fresh` | Proceed to **Execution** below. |
| `stale` | Halt. Record `outcome=failed` with `display_detail` `"stale: worktree_sha={worktree_sha} ledger={ledger_path}"`. Do NOT push. |
| `undecidable` | Halt. Record `outcome=failed` with `display_detail` `"undecidable: {reason}"` (`reason` is `no_registry` or `head_unresolvable`). Do NOT push. |

The freshness gate is **complementary to**, NOT redundant with, the `pre-push-quality-gate` step. The quality-gate verifies *what the code is* (mypy + ruff + tests on the on-disk tree); freshness verifies *that the most recent `verify` run actually observed this version of the code*. A worktree that was modified after the most recent successful build passes neither: the quality-gate may pass against the new tree if the orchestrator re-runs it, but the freshness gate fails because no `kind=build` change-ledger entry carries the current working-tree `worktree_sha`. The two gates together close the gap that `loop-exit-guard` cannot close on its own — `loop-exit-guard` answers "is the queue empty?" while freshness answers "has a `verify` run actually observed this version of the code?"

The `--force` escape mirrors phase-5 Step 12a's escape — orchestrator-only, log-recorded, never auto-invoked. When the orchestrator drives finalize with `--force` AND the freshness gate returned a non-`fresh` status, the dispatcher records a `decision`-level WARNING (`(plan-marshall:phase-6-finalize:push) Worktree-freshness precondition overridden via --force — proceeding with status={status}` — append `reason={reason}` only when status is `undecidable`; the `stale` branch does not emit a `reason` field) and then allows `push` to proceed.

## Execution

### Assert a clean tree

```bash
git -C {worktree_path} status --porcelain
```

A clean tree (empty output) is the contractual expectation — the dispatcher's commit instrumentation committed every `mutates_source: true` step's output upstream of this barrier. A non-empty result indicates an upstream contract violation (a mutating step's edits were not committed before the barrier); STOP and return an error TOON to the orchestrator naming the dirty tree, rather than pushing an inconsistent state.

### Push the converged branch

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-git"
```

```text
Skill: plan-marshall:workflow-integration-git
```

Execute the git_workflow skill's **Workflow: Commit Changes** with `push: true` and NO `message`:
- `push`: true (always push in finalize)
- `worktree_path`: `{worktree_path}` resolved at finalize entry

Against the clean tree this barrier asserts, the Commit Changes workflow's Step 2 reports "No changes to commit" and falls straight through to its Step 6 push — so this barrier creates no commit; it only pushes the already-converged branch.

## Mark Step Complete

Record that this step ran on the live plan. The `push` step is NOT a member of `HEAD_DEPENDENT_STEPS` — it is a pure barrier the dispatcher re-invokes explicitly after a post-PR `mutates_source` step commits (see `phase-6-finalize/SKILL.md` Step 3 item 5f § "Post-PR re-push"), so it does NOT capture or forward `--head-at-completion`.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the push outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step push --outcome done \
  --display-detail "pushed {branch}"
```
