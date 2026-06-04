---
name: recipe-simplify-codebase
description: Domain-invariant recipe for deliberate wide-scope simplification campaigns across a scope x thoroughness cell, with a T4+ relation-graph pre-deliverable
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Simplify Codebase

Generic, domain-invariant recipe skill for **deliberate wide-scope simplification campaigns** — the missing vehicle for sweeping surplus structure out of a codebase at a chosen `scope × thoroughness` cell. Where `recipe-refactor-to-profile-standards` brings code into compliance with profile standards, this recipe runs the cognitive minimum-viable-code review across a declared radius and deletes surplus structure the static doctors cannot reach.

The per-batch worker is `finalize-step-simplify`'s cognitive engine — **reused, not reinvented** — widened past its live-footprint change-set cap and fed a dependency-structured batch plan. The scaffold mirrors `recipe-refactor-to-profile-standards`'s module/package iteration. Domain-invariant by construction: the minimum-viable-code anti-pattern set is language-agnostic (as `finalize-step-simplify` proves), so this recipe applies uniformly to Java, Python, JavaScript, documentation, and marketplace changesets alike.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_scope` | string | Yes | Campaign scope — one of `component`, `module`, `overall` |
| `recipe_thoroughness` | string | Yes | Campaign thoroughness rung — one of `T1`, `T2`, `T3`, `T4`, `T5` |

The two dials are the scope × thoroughness contract. Their ladders, the grade-to-the-floor rule, and the coupling constraint are defined once in [`dev-agent-behavior-rules/standards/thoroughness.md`](../dev-agent-behavior-rules/standards/thoroughness.md); this recipe implements the [coverage-gathering contract](../dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — it gathers, expands, and consumes the cell per that contract and does NOT restate the ladders or re-derive the coupling check. `recipe_scope` / `recipe_thoroughness` are accepted as the pre-gathered values when the recipe workflow already supplied them; otherwise Step 0 gathers them.

---

## Step 0: Gather + expand + persist the coverage cell

When `recipe_scope` / `recipe_thoroughness` were not supplied as inputs, gather the `(thoroughness, scope)` cell from the user via the contract's canonical `AskUserQuestion` shape — a `scope` question (`component`/`module`/`overall` + an explicit `inherit (default — behave exactly as today)`) and a `thoroughness` question (`T1`…`T5` + `inherit`), coupling-constrained when `T4`/`T5` is picked. Then expand the identifier into the operational instruction block and persist BOTH the identifier and the expanded instruction to `status.json` metadata (this recipe is plan-bound):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness {recipe_thoroughness} --scope {recipe_scope}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value {recipe_thoroughness}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value {recipe_scope}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

Consume the **expanded instruction** (NOT the raw cell) in Steps 2–4. `inherit/inherit` reproduces today's module/package iteration.

---

## Step 1: Validate the scope × thoroughness cell (coupling constraint)

Before any discovery, validate the gathered cell against the coupling constraint by delegating to the resolver — do NOT re-implement the `thoroughness ≥ T4 ∧ scope < component` rejection here. `coverage resolve` reads `marshal.json` only (it has NO `--audit-plan-id` flag and no per-plan tier), so validate the gathered literal pair directly via `coverage expand`, which applies the same coupling check at expand time:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  coverage expand --thoroughness {recipe_thoroughness} --scope {recipe_scope}
```

The expander (and `coverage resolve` for project-default cells) enforces the coupling constraint and emits `error_type: coverage_coupling_violation` for an incoherent cell — re-prompt the gather on that error. The constraint, stated for reference only: a campaign with `recipe_thoroughness ∈ {T4, T5}` REQUIRES `recipe_scope ≥ component` — relation-tracing thoroughness cannot be honoured below `component` scope because the relations' other ends lie outside the radius. Abort (re-gather) when the requested cell violates it.

---

## Step 2: Resolve the campaign radius

Query the project architecture for the units in radius for `recipe_scope`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

- `recipe_scope == component` — present the module list and let the user select a single component/sub-tree as the radius.
- `recipe_scope == module` — iterate every selected module.
- `recipe_scope == overall` — the radius is the whole codebase (every module).

Present the resolved radius to the user for confirmation/filtering. The user may exclude modules (parent POMs, generated trees, vendored directories).

---

## Step 3 (T4+ only): Relation-graph pre-deliverable

**When `recipe_thoroughness ∈ {T4, T5}`, a relation-graph pre-deliverable is MANDATORY** — this is the step the manual sweeps lacked. Before any simplification batch, build the cross-component relationship model for the campaign radius:

- the call graph (who calls what),
- the cross-reference graph (who references / imports what),
- the duplicate-contract map (the same invariant authored in more than one place).

Derive the sweep batches **from this graph** — dependency-structured, leaf-first — NOT from arbitrary categories. A node is only swept after the nodes it depends on, so a simplification never strands a now-dangling reference in an untouched sibling. The relation graph is emitted as the campaign's first deliverable; every subsequent sweep deliverable cites the graph nodes it covers.

For `recipe_thoroughness ∈ {T1, T2, T3}` this step is skipped — those rungs do not promise global relation tracing, so the sweep batches are derived directly from the radius units in Step 2.

---

## Step 4: Collect simplification deliverables

Collect one deliverable per sweep batch (one batch per radius unit at T1–T3; one batch per relation-graph cluster at T4+):

- **Title**: `Simplify: {unit_or_cluster_name}`
- **Description**: `Cognitive minimum-viable-code review and surplus deletion across {unit_or_cluster_name}`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `module`: `{module_name}`
- **Per-deliverable scope × thoroughness declaration**: record the deliverable's `recipe_scope` × `recipe_thoroughness` cell for the floor-graded self-report (the quality signal — there is no blocking gate). The contract's runtime consumer, `finalize-step-simplify`, reads the expanded instruction (from `status.json` metadata `coverage_instruction`) to govern its review depth and breadth per the coverage-gathering contract.
- **Affected files**: every file in the batch (from architecture data, or via `manage-files discover` when the architecture record reports `file_count: 0`).
- **Per-batch worker**: the `finalize-step-simplify` cognitive engine, widened past the live-footprint cap and fed the batch file set (and, at T4+, the relation-graph cluster). Cross-reference [`phase-6-finalize/standards/finalize-step-simplify.md`](../phase-6-finalize/standards/finalize-step-simplify.md) — do NOT re-author the anti-pattern review logic; this recipe only widens its scope and supplies the batch plan.

The unit's achieved thoroughness grades to the FLOOR across its batches (a campaign where some batches were only sampled is graded at the sampled rung — see the grade-to-the-floor rule in the central standard).

---

## Step 5: Outline Writing

**5a. Read the deliverable template**:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**5b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**5c. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include, in order:
- `# Solution: Simplify {recipe_scope}` header with `plan_id`, `created`, `compatibility` metadata.
- `## Summary` — the campaign cell (`{recipe_scope} × {recipe_thoroughness}`) and the radius ({N} units / {M} modules).
- `## Overview` — the radius breakdown and, at T4+, the relation-graph pre-deliverable.
- `## Deliverables` — the relation-graph pre-deliverable first (T4+ only), then one sweep deliverable per batch, each carrying its per-deliverable scope × thoroughness declaration.

**5d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Related

- `plan-marshall:dev-agent-behavior-rules` `standards/thoroughness.md` — the scope × thoroughness ladders, grade-to-the-floor rule, and coupling constraint (single source of truth).
- `plan-marshall:dev-agent-behavior-rules` `standards/coverage-gathering-contract.md` — the coverage-gathering contract this recipe implements (gather → expand → consume; persistence; cell→instruction table).
- `plan-marshall:manage-config` `coverage expand` / `coverage resolve` — the static identifier→instruction expander and the project-default resolver that enforce the coupling constraint.
- `plan-marshall:phase-6-finalize` `standards/finalize-step-simplify.md` — the cognitive simplification engine this recipe reuses (widened past the change-set cap).
- `plan-marshall:recipe-refactor-to-profile-standards` — the sibling recipe whose module/package iteration scaffold this recipe mirrors.
- `plan-marshall:phase-3-outline` Step 2.5 — loads this skill with input parameters.
