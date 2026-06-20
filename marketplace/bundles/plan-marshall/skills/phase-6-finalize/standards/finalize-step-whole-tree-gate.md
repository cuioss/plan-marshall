---
name: default:finalize-step-whole-tree-gate
description: Whole-tree invariant backstop — the NOT-diff-scoped pre-push gate. Beyond the deleted-symbol survivor sweep (greps the entire tree for surviving references to symbols/contracts the plan deleted and flags request-mandate items absent from the diff), it conditionally runs two whole-tree facet checks — a marketplace-wide static-analysis sweep and a re-run of the whole-tree grep-sweep guard tests — each gated on the plan's changed set intersecting the corresponding trigger; runs pre-commit so any genuine finding BLOCKS the push
order: 9
---

# Finalize Step: whole-tree-gate

Whole-tree invariant backstop for the `default:finalize-step-whole-tree-gate` finalize step. Runs BEFORE `commit-push` materialises the commit so any whole-tree invariant the plan violated BLOCKS the push rather than landing on the branch. It is the NOT-diff-scoped complement to the diff-scoped finalize gates: where the simplify / self-review passes reason about the plan's own change surface, this gate verifies invariants that only surface when the ENTIRE tree is considered, not just the diff.

The gate's scope is **three** whole-tree checks, not one:

1. **Deleted-symbol survivor sweep** (always runs) — greps the ENTIRE tree for surviving references to symbols/contracts the plan deleted, and flags request-mandate items absent from the diff. This is the original gate behaviour: it catches a half-applied clean-slate deletion that the diff-scoped gates cannot see.
2. **Marketplace-wide static-analysis sweep** (conditional) — when the plan's changed set touches the static-analysis rule surface, the gate runs the marketplace-wide static-analysis quality gate over the full tree rather than the build-map-scoped subset, so a rule change that breaks an untouched component is caught before the push.
3. **Whole-tree grep-sweep guard re-run** (conditional) — when the plan's changed set touches a whole-tree grep-sweep guard test, the gate re-runs those guard tests with the full tree as scan root rather than the module-scoped subset, so a guard that depends on the whole-tree scan is exercised against the whole tree.

Checks 2–3 are each conditional on the plan's changed set intersecting the corresponding trigger; the survivor sweep (check 1) always runs when the gate is active. The concrete per-facet Workflow steps live in the Workflow section below.

The gate is gated into the manifest at composition time by the `whole_tree_gate_inactive` pre-filter (see [`manage-execution-manifest/standards/decision-rules.md` § Pre-Filter: `whole_tree_gate_inactive`](../../manage-execution-manifest/standards/decision-rules.md#pre-filter-whole_tree_gate_inactive), the single source of truth for the activation predicate and the trigger-glob sets). The predicate is **additive** — the gate activates when EITHER arm holds:

- **Breaking arm** (unchanged) — clean-slate/breaking, code-bearing plans: `compatibility == breaking` AND `change_type ∈ {tech_debt, feature, enhancement, bug_fix}` AND `affected_files_count > 0`. This arm is what makes the survivor sweep fire: a `deprecation` / `smart_and_ask` plan deliberately keeps old surfaces alongside new ones, so a surviving reference under those postures is the expected outcome, not a defect.
- **Whole-tree-invariant-trigger arm** (additive) — the gate ALSO activates, regardless of compatibility posture, when the plan's changed set intersects the whole-tree invariant surface (the static-analysis rule trigger or the grep-sweep-guard-test trigger). This arm is what makes facet checks 2–3 reachable on non-breaking plans: a rule change or a guard-test change carries a whole-tree invariant risk even when the plan's compatibility posture is `deprecation` or `smart_and_ask`.

The concrete trigger-glob sets backing the additive arm are owned by `decision-rules.md`; this doc cross-references them and does not restate them. Which of facet checks 2–3 actually runs at gate time is decided by the same changed-set/trigger intersection — an activated gate runs the survivor sweep plus only the facet checks whose trigger fired.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-whole-tree-gate` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). The composer's `whole_tree_gate_inactive` pre-filter is the only place the step is gated in or out, so this executor is never dispatched for a plan that satisfies NEITHER the breaking arm NOR the whole-tree-invariant-trigger arm of the additive activation predicate documented above.

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST target `{worktree_path}`.

## Workflow

The workflow surfaces each active whole-tree check deterministically (the surfacer greps, runs the facet checks, and emits candidate rows — it makes no verdict), then classifies the surfaced rows in a single cognitive pass and terminates. Step 1 surfaces the always-on survivor sweep AND the two conditional facet checks (checks 2–3 above) in **one** `scan` call — the surfacer itself evaluates each facet's changed-set/trigger intersection and runs only the facets whose trigger fired. Sub-steps 1b/1c below document what each facet's surfaced result means; they are NOT separate script calls. The classification pass (Step 2) and the terminate condition (Step 3) span every surfaced row regardless of which check produced it.

### Step 1: Surface survivors, mandate gaps, and the facet checks

Run the deterministic surfacing helper. It resolves the plan diff (`{base}...HEAD`) via `git -C {worktree_path}`, extracts the identifiers/contracts the plan DELETED (removed lines), greps the entire `marketplace/` tree (NOT the diff, NOT only touched skills) with word-boundary anchoring for surviving references, compares the request's enumerated mandate against the diff's touched files, AND runs the two whole-tree facet checks (each gated on the changed set intersecting its trigger glob):

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:whole_tree_gate \
  scan --plan-id {plan_id}
```

The helper excludes `.plan/archived-plans/**` and vendored snapshots from the sweep, and emits `survivors[]{file,line,identifier}`, `mandate_gaps[]`, plus a `facets` block with one entry per facet (`doctor`, `sweep_test`). Each facet entry carries `triggered`, `ran`, `passed`, and a human-readable `summary`; the facet driver fires a facet only when the plan's changed set hits the matching trigger-glob category (the per-category trigger globs are owned by [`manage-execution-manifest/standards/decision-rules.md` § Pre-Filter: `whole_tree_gate_inactive`](../../manage-execution-manifest/standards/decision-rules.md#pre-filter-whole_tree_gate_inactive) — this doc cross-references them, it does not restate them).

#### Step 1b: Marketplace-wide static-analysis sweep (`facets.doctor`)

When the changed set touches a plugin-doctor / plan-doctor analyzer or rule script, the surfacer runs the marketplace-wide `plugin-doctor quality-gate` over the FULL `marketplace/` tree (no `--paths` filter — whole-tree, not the build-map-scoped subset). `facets.doctor.passed: false` (with `finding_count` and the doctor stdout in `summary`) is a SURFACED finding for the Step 2 cognitive pass, exactly like a `survivors[]` row. An untriggered facet reports `triggered: false, ran: false, passed: true` and contributes nothing.

#### Step 1c: Whole-tree grep-sweep guard re-run (`facets.sweep_test`)

When the changed set touches a whole-tree grep-sweep guard test, the surfacer re-runs the `whole_tree_sweep`-marked guard tests (`pytest -m whole_tree_sweep`) with the full tree as scan root. A pytest "no tests collected" outcome is a PASS (nothing to re-run). `facets.sweep_test.passed: false` is a surfaced test-failure finding for Step 2.

A facet whose seam hit an infrastructure failure (the doctor/pytest could not be invoked, or a seam timed out) reports `ran: false, passed: false` with an `error` key — an un-run facet is a FAIL surface, never silently treated as clean.

### Step 2: Classify each surfaced row (cognitive pass)

For each `survivors[]` row, classify it as a **genuine omission** (a deleted symbol/contract that still survives where it should have been removed → FAIL) versus a **legitimate retained reference** (e.g. a same-named identifier in an unrelated context the deletion never targeted → PASS). Each `mandate_gaps[]` row is a request-mandate item with no diff representation and is treated as a genuine gap unless the cognitive pass establishes it was satisfied by a path the surfacer did not attribute. For each `facets.{doctor,sweep_test}` entry with `passed: false`, classify the surfaced finding the same way: a genuine whole-tree invariant violation (a real doctor finding, a real guard-test failure, or an `error` indicating the facet could not run) → FAIL; a finding the cognitive pass establishes is a false positive or already remediated → PASS.

On any genuine survivor, unresolved mandate gap, or failed facet, the gate FAILs: do NOT mark the step done, and return a structured `blocked` payload to the orchestrator so the failure routes through the standard finalize triage loop (the same fix-task / suppress / accept branch the other finalize gates use).

**Compound / hyphenated contract-value discipline.** The surfacer's deleted-identifier extraction is anchored to *declared symbols* (Python `def`/`class`/module-level assignment) and otherwise to whitespace-and-word-level identifier tokens — so a deleted or renamed **compound / hyphenated contract value** (a routing discriminator such as `verification-failure`, an enum member, or a dash-bearing config key) is NOT a declared symbol, and its constituent words are individually legitimate everywhere in the tree. The survivor sweep alone is therefore UNRELIABLE for this class: it will report clean even when a consumer doc still carries the old whole compound token. Whenever the plan deletes or renames a compound/hyphenated contract value, the cognitive pass MUST also grep directly for the **whole hyphenated token** across `marketplace/` before trusting a clean sweep result — a `git -C {worktree_path} grep -n -- 'verification-failure'`-style direct search for the literal token, classifying each hit the same way as a `survivors[]` row. A clean survivor sweep does not discharge this obligation; only the direct whole-token grep does.

### Step 3: Terminate

When zero genuine survivors and zero unresolved mandate gaps remain, capture `git -C {worktree_path} rev-parse HEAD` and mark the step done:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-whole-tree-gate --outcome done \
  --display-detail "whole-tree gate clean: 0 survivors"
```

## Error Handling

A non-zero exit from `whole_tree_gate scan` (e.g. the diff could not be resolved) is a hard error: STOP and return the script's stderr verbatim to the orchestrator. Do NOT mark the step done on a surfacer failure — an un-run sweep is indistinguishable from a passed one and would silently undo the gate's purpose.
