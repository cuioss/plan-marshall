---
name: default:pre-push-quality-gate
description: Run quality-gate per affected bundle as the last gate before commit-push
order: 5
---

# Pre-Push Quality Gate

Pure executor for the `pre-push-quality-gate` finalize step. Runs `quality-gate` once per unique bundle derived from `references.modified_files`, immediately before `default:commit-push` (`order: 10`). This is the deterministic last-line guard against type/lint regressions reaching remote CI — converting soft "consider quality-gate" guidance into a hard precondition for push.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_push_quality_gate_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`). When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a failed bundle invocation records `outcome=failed` and halts the phase. The `commit_strategy == none` case is also filtered at composition time (the `commit_strategy_none` pre-filter strips both `commit-push` AND `pre-push-quality-gate`), so this step is never dispatched without a downstream push.

## Inputs

- `references.modified_files` — list[string] of repo-relative paths recorded by Phase 5. Source for bundle derivation.
- `phase-6-finalize.pre_push_quality_gate.activation_globs` — list[string] of fnmatch globs. The manifest composer already gated activation on this list; the executor re-reads it to scope which `modified_files` entries should contribute to bundle derivation (defense-in-depth — only entries that match a configured glob feed bundle derivation).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All build invocations below MUST pass `--project-dir {worktree_path}` (Bucket B requirement).

## Execution

### Read modified_files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  list get --plan-id {plan_id}
```

Extract the `modified_files` array from the TOON output.

### Read activation_globs

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field pre_push_quality_gate.activation_globs \
  --trace-plan-id {plan_id}
```

Extract `value` (list[string]). The manifest composer guarantees the list is non-empty when this step is dispatched, but the executor reads it again for defense-in-depth.

### Derive unique bundle set

For each entry `path` in `modified_files`:

1. Skip the entry if it matches none of the `activation_globs` (using `fnmatch.fnmatch`).
2. If the entry begins with `marketplace/bundles/`, take path segment 2 as the bundle (e.g., `marketplace/bundles/plan-marshall/skills/.../foo.py` → `plan-marshall`).
3. Otherwise, if the entry begins with `test/`, take path segment 1 as the bundle (e.g., `test/plan-marshall/.../test_foo.py` → `plan-marshall`).
4. Otherwise, the entry contributes no bundle (drop silently).

Collect the resulting bundle names into a sorted, de-duplicated list `bundles`. Let `N = len(bundles)`.

### Run quality-gate per bundle

For each `bundle` in `bundles` (in sorted order):

```bash
python3 .plan/execute-script.py plan-marshall:build-python:python_build \
  run --command-args "quality-gate {bundle}" --project-dir {worktree_path}
```

Inspect the TOON output. On `status: error`, halt: stop iterating, record the failing bundle, and proceed to **Mark Step Complete (Failure)** below. The underlying `python_build` TOON output already carries `errors[N]{file,line,message,category}` — surface the offending file/line via the standard finalize TOON.

If every bundle succeeds (`status: success` for all `N` invocations), proceed to **Mark Step Complete (Success)**.

## Mark Step Complete

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — all bundles green**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-push-quality-gate --outcome done \
  --display-detail "quality-gate green for {N} bundle(s)"
```

**Branch B — at least one bundle failed**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-push-quality-gate --outcome failed \
  --display-detail "quality-gate failed for {bundle}"
```

The dispatcher's existing failure handling halts the phase on `outcome=failed` and surfaces the offending file/line through the finalize TOON, matching the contract used by the other gating steps.
