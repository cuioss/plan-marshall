---
name: default:pre-submission-self-review
description: Pre-submission structural self-review (symmetric pairs, regex over-fit, wording, duplication, contract drift) before commit-push
order: 7
---

# Pre-Submission Self-Review

Pure executor for the `pre-submission-self-review` finalize step. Catches the class of structural defects that PR-review bots reliably surface but local quality gates systematically miss: missing initialization in symmetric save/restore pairs, regex/glob over-fit, ambiguous user-facing wording, duplicate prose sections covering the same contract, and schema/contract drift.

The step combines a deterministic helper that surfaces concrete candidates from the staged diff with an LLM cognitive review applied only to those candidates. The deterministic phase runs inline in the manifest dispatcher's context; the LLM cognitive phase is dispatched under `--phase phase-6` (no `--role` — pre-submission-self-review tracks the phase-6 default) via [`../workflow/pre-submission-self-review.md`](../workflow/pre-submission-self-review.md). On any finding the LLM returns, the step hard-fails and halts the phase, mirroring the gating-step convention established by `pre-push-quality-gate`.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_submission_self_review_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`). The composer drops the step when `commit_strategy == none` (transitively, via `commit_strategy_none`) OR `references.modified_files` is empty. When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a non-empty findings list records `outcome=failed` and halts the phase.

## Inputs

- `references.modified_files` — list[string] of repo-relative paths recorded by Phase 5. Defines the change footprint the deterministic helper inspects.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The deterministic helper invocation MUST identify the worktree via either `--plan-id {plan_id}` alone (preferred — `tools-self-review:self_review surface` auto-resolves the worktree path through `manage-status get-worktree-path`; `--plan-id` is also used for the modified-files lookup, so it is required either way) or by additionally supplying `--project-dir {worktree_path}` as an explicit override. The staged diff is computed against the worktree's base branch.

## Execution

### Step 1: Deterministic surface (inline)

Invoke the deterministic helper to surface concrete candidates from the staged diff. The helper reads `references.modified_files` for the active plan, computes the staged diff against the worktree's base branch, and emits the six candidate lists in a single TOON document on stdout.

```bash
python3 .plan/execute-script.py plan-marshall:tools-self-review:self_review \
  surface --plan-id {plan_id}
```

(Auto-resolves the worktree from `--plan-id`. Add `--project-dir {worktree_path}` only when the explicit override is required.)

If the helper exits non-zero, halt and proceed to **Mark Step Complete (Failure)** — surface the helper error in the `display_detail` payload. Do NOT dispatch the LLM cognitive phase below.

Capture the helper's TOON output as `{candidates_toon}` for forwarding to the cognitive-phase dispatch.

### Step 2: LLM cognitive phase (dispatch)

Compute the variant target via the role resolver:

```bash
target=$(python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models resolve-target --phase phase-6)
```

Dispatch the LLM workflow with the candidate envelope:

```
Task: plan-marshall:{target}
  prompt: |
    name: pre-submission-self-review
    plan_id: {plan_id}
    skills: []
    workflow: plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md

    candidates: |
      {candidates_toon}

    WORKTREE: {worktree_path}
```

The dispatched workflow loads the contract sources referenced in `candidates.contract_sources`, applies the five cognitive checks (symmetric pair test coverage, regex over-fit, wording disambiguation, duplication, contract drift), and returns a `findings[N]{file,line,defect_class,rationale}` list. Empty list → clean self-review; non-empty list → defect surface for the operator to address.

## Mark Step Complete

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — findings list is empty**: read the `display_detail` returned by the workflow verbatim (the workflow computes the candidate count for the human-readable message).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-submission-self-review --outcome done \
  --display-detail "{display_detail_from_workflow}"
```

**Branch B — findings list is non-empty**: surface the findings in the finalize TOON output (consumed by `output-template.md`) so the operator sees `file:line` and `defect_class` per finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-submission-self-review --outcome failed \
  --display-detail "{display_detail_from_workflow}"
```

The dispatcher's existing failure handling halts the phase on `outcome=failed`, matching the gating-step contract used by `pre-push-quality-gate`. The operator must address every finding (amend the diff: rename, tighten regex, rewrite wording, delete duplicate section, fix contract drift), re-run the step, and only then advance to `commit-push`.
