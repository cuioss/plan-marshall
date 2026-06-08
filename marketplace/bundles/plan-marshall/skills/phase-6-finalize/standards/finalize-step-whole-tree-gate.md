---
name: default:finalize-step-whole-tree-gate
description: Whole-tree completeness gate for clean-slate/breaking plans — greps the entire marketplace tree (not the diff) for surviving references to symbols/contracts the plan deleted and flags request-mandate items absent from the diff; runs pre-commit so a survivor BLOCKS the push
order: 9
---

# Finalize Step: whole-tree-gate

Whole-tree completeness gate for the `default:finalize-step-whole-tree-gate` finalize step. Runs BEFORE `commit-push` materialises the commit so a surviving deleted-symbol reference (or an unrepresented request mandate) BLOCKS the push rather than landing a half-applied clean-slate deletion. It is the NOT-diff-scoped complement to the diff-scoped finalize gates: where the simplify / self-review passes reason about the plan's own change surface, this gate sweeps the ENTIRE `marketplace/` tree for survivors of deletions the plan was meant to make.

The gate is gated into the manifest at composition time by the `whole_tree_gate_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`), which activates it only for clean-slate/breaking, code-bearing plans (`compatibility == breaking` AND `change_type ∈ {tech_debt, feature, enhancement, bug_fix}` AND `affected_files_count > 0`). A `deprecation` / `smart_and_ask` plan deliberately keeps old surfaces alongside new ones, so a surviving reference there is the expected outcome, not a defect — hence the gate never fires for those compatibility postures.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-whole-tree-gate` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). The composer's `whole_tree_gate_inactive` pre-filter is the only place the step is gated in or out, so this executor is never dispatched for the compatibility / change-type / empty-changeset plans the rule excludes.

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST target `{worktree_path}`.

## Workflow

### Step 1: Surface survivors and mandate gaps

Run the deterministic surfacing helper. It resolves the plan diff (`{base}...HEAD`) via `git -C {worktree_path}`, extracts the identifiers/contracts the plan DELETED (removed lines), greps the entire `marketplace/` tree (NOT the diff, NOT only touched skills) with word-boundary anchoring for surviving references, and compares the request's enumerated mandate against the diff's touched files:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:whole_tree_gate \
  scan --plan-id {plan_id}
```

The helper excludes `.plan/archived-plans/**` and vendored snapshots from the sweep, and emits `survivors[]{file,line,identifier}` plus `mandate_gaps[]`.

### Step 2: Classify each survivor (cognitive pass)

For each `survivors[]` row, classify it as a **genuine omission** (a deleted symbol/contract that still survives where it should have been removed → FAIL) versus a **legitimate retained reference** (e.g. a same-named identifier in an unrelated context the deletion never targeted → PASS). Each `mandate_gaps[]` row is a request-mandate item with no diff representation and is treated as a genuine gap unless the cognitive pass establishes it was satisfied by a path the surfacer did not attribute.

On any genuine survivor or unresolved mandate gap, the gate FAILs: do NOT mark the step done, and return a structured `blocked` payload to the orchestrator so the failure routes through the standard finalize triage loop (the same fix-task / suppress / accept branch the other finalize gates use).

### Step 3: Terminate

When zero genuine survivors and zero unresolved mandate gaps remain, capture `git -C {worktree_path} rev-parse HEAD` and mark the step done:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-whole-tree-gate --outcome done
```

## Error Handling

A non-zero exit from `whole_tree_gate scan` (e.g. the diff could not be resolved) is a hard error: STOP and return the script's stderr verbatim to the orchestrator. Do NOT mark the step done on a surfacer failure — an un-run sweep is indistinguishable from a passed one and would silently undo the gate's purpose.
