---
name: recipe-marshal-json-config-audit
description: Domain-invariant recipe that audits and improves .plan/marshal.json across five aspects (default-surfacing, dead-config, docs, naming, units) at a hard-coded T4/module cell
user-invocable: false
allowed-tools: Read, Glob, Bash, AskUserQuestion, Skill
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: marshal.json Configuration Audit

Generic, domain-invariant recipe skill that drives a plan to **audit and improve `.plan/marshal.json`** — the project configuration file `setup` / `marshall-steward` seed and every phase consumes. Where `recipe-refactor-to-profile-standards` brings code into compliance with profile standards and `recipe-simplify-codebase` sweeps surplus structure, this recipe inspects the live configuration along five aspects and collects one deliverable per aspect.

Like `recipe-simplify-codebase` it is an LLM-driven, SKILL.md-only deliverable-collection workflow (no scripts): the phase-3-outline recipe path loads it to produce a config-audit `solution_outline.md`.

Unlike the interactive recipes, this recipe **hard-codes** its `(thoroughness, scope)` cell instead of gathering it from the user. It implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — expand and consume — but **skips the gather step**, supplying a fixed identifier + expanded instruction per the contract's gather → expand → consume model.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |
| `recipe_domain` | `plan-marshall-plugin-dev` |
| `recipe_profile` | `implementation` |

There is no `recipe_scope` / `recipe_thoroughness` input — the cell is fixed (see Step 1). The package-source parameter is omitted because the recipe audits a single config file and does not iterate packages. The recipe is plan-bound; it persists the resolved cell to status.json metadata.

---

## Step 1: Declare + expand + persist the hard-coded coverage cell (NO gather)

The config audit is a project-wide, relation-tracing task: aspect 2 (dead-config detection) requires tracing every config key to its usages across the codebase before any key can be classified dead — that is global relation tracing. The recipe therefore hard-codes the cell **`thoroughness=T4, scope=module`**:

- `scope=module` — the radius is the `plan-marshall` bundle that owns `marshal.json` plus its config-consuming code. The coupling floor for T4 is `component`; `module` satisfies it.
- `thoroughness=T4` — full-read + global relations: build a config-key → usage relation model across the codebase before classifying any key as dead.

This recipe does **NOT** raise an `AskUserQuestion` for the cell — it skips the contract's gather step entirely and supplies the fixed pair directly. Expand the identifier into the operational instruction block and persist BOTH the identifier and the expanded instruction to `status.json` metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness T4 --scope module
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value T4
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value module
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

The ladders (T1–T5), the grade-to-the-floor rule, and the coupling constraint are defined once in [`dev-agent-behavior-rules/standards/thoroughness.md`](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/thoroughness.md), and the cell → instruction expansion table lives in [`dev-agent-behavior-rules/standards/coverage-gathering-contract.md`](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md); do NOT restate either here. `coverage expand` enforces the coupling constraint and emits `error_type: coverage_coupling_violation` for an incoherent cell — the fixed `T4 / module` pair satisfies the constraint by construction, so a violation here is a contract bug, not a re-gather case.

Consume the **expanded instruction** (NOT the raw cell) when collecting the audit deliverables in Step 3.

---

## Step 2: Resolve the audit radius

The radius is the `plan-marshall` module that owns `marshal.json` and its config-consuming code. Query the project architecture to enumerate the module's files so the relation-tracing aspects (2, 3) have a concrete usage surface:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture files --module plan-marshall
```

The config file under audit is `.plan/marshal.json` (the live project config seeded by `setup` / `marshall-steward`). The relation model the T4 cell promises is built across this module's config-reading code (`manage-config`, the phase skills, `marshall-steward`) — every key in `marshal.json` is traced to the code that reads it.

---

## Step 3: Collect the five audit deliverables

Collect **one deliverable per audit aspect** below. Each deliverable carries: a title, a description, `change_type`, `execution_mode: automated`, `module: plan-marshall`, affected files, and resolved verification commands. Record each deliverable's `T4 × module` cell for the floor-graded self-report (the quality signal — there is no blocking gate); the running plan consumes the expanded instruction (from `status.json` metadata `coverage_instruction`) to govern review depth and breadth per the coverage-gathering contract.

### Aspect 1 — Default-surfacing completeness (`change_type: tech_debt`)

Verify that every config default `setup` / `marshall-steward` is supposed to write is materialised in `.plan/marshal.json`. Trace each code-side default to the file and flag any that exists in code but is absent from the file (code-default-but-not-in-file gaps). The deliverable materialises the missing defaults into `marshal.json`.

### Aspect 2 — Dead-config detection (`change_type: tech_debt`)

For every key present in `marshal.json`, trace every codebase usage and verify the value is actually consumed with real effect (not a no-op read, not an orphaned reference). Produce an unused/orphaned-key list.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the orphaned-key list; **deletion happens ONLY after explicit user confirmation**. The running task MUST raise an `AskUserQuestion` presenting the proposed removals and MUST NOT delete any key until the user confirms. The audit proposes; the user confirms.

### Aspect 3 — Documentation coverage (`change_type: tech_debt`)

Verify that every config key in `marshal.json` is surfaced in `doc/user/configuration.adoc`. Flag undocumented keys. The deliverable adds the missing documentation rows.

### Aspect 4 — Naming-scheme consistency (`change_type: analysis`)

Assess whether the keys follow a uniform, conflict-free naming scheme. Report inconsistencies and conflicts (e.g. mixed separators, divergent prefixes, two keys that mean the same thing). This aspect is report-only — renames are breaking and are surfaced for a deliberate decision, not auto-applied.

### Aspect 5 — Unit sanity (`change_type: analysis`)

Assess whether each value's unit is sensible (e.g. a raw `50000` token budget vs `50` thousands or `"50K"`). Report values whose units read poorly.

**Follow-up-plan escape hatch**: a broad units rework touches many call sites and may belong in a SEPARATE follow-up plan rather than being forced into the audit plan. When the assessment finds that fixing units would cascade beyond the config file, the deliverable records the finding and recommends a follow-up plan instead of widening this one.

---

## Step 4: Outline Writing

**4a. Read the deliverable template**:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4c. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include, in order:
- `# Solution: marshal.json Configuration Audit` header with `plan_id`, `created`, `compatibility` metadata.
- `## Summary` — the audit cell (`module × T4`), the config file under audit (`.plan/marshal.json`), and the five aspects.
- `## Overview` — the audit radius (the `plan-marshall` module) and the relation model the T4 cell builds.
- `## Deliverables` — one deliverable per audit aspect (Aspects 1–5 above), each carrying its `T4 × module` cell declaration, the aspect-2 user-confirmation gate, and the aspect-5 follow-up-plan note.

**4d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Enforcement

**Execution mode**: Deliverable-collection recipe — declare the hard-coded cell, resolve the radius, collect the five audit deliverables, write the solution outline. Loaded by phase-3-outline's recipe path; not user-invocable.

**Prohibited actions:**
- Never raise an `AskUserQuestion` for the coverage cell — the cell is hard-coded `T4 / module` (Step 1). The only `AskUserQuestion` this recipe drives is the aspect-2 deletion-confirmation gate in the running plan.
- Never restate the thoroughness ladders, the grade-to-the-floor rule, the coupling constraint, or the cell → instruction expansion table — cross-reference `dev-agent-behavior-rules/standards/thoroughness.md` and `coverage-gathering-contract.md`.
- Never delete an orphaned config key without explicit user confirmation (aspect-2 gate).
- Never access `.plan/` files directly — all access goes through `python3 .plan/execute-script.py` manage-* scripts.

**Constraints:**
- The persisted cell is `coverage_thoroughness=T4`, `coverage_scope=module`, plus the `coverage expand`-produced `coverage_instruction`, written to `status.json` metadata.
- Each collected deliverable declares `module: plan-marshall` and its `T4 × module` cell for the floor-graded self-report.
- A broad units rework (aspect 5) is recommended as a separate follow-up plan rather than widening the audit plan.

## Related

- `plan-marshall:dev-agent-behavior-rules` `standards/thoroughness.md` — the scope × thoroughness ladders, grade-to-the-floor rule, and coupling constraint (single source of truth).
- `plan-marshall:dev-agent-behavior-rules` `standards/coverage-gathering-contract.md` — the coverage-gathering contract this recipe implements (expand → consume; persistence; cell → instruction table). This recipe skips the gather step.
- `plan-marshall:manage-config` `coverage expand` — the static identifier → instruction expander that enforces the coupling constraint.
- `plan-marshall:recipe-simplify-codebase` — the sibling SKILL.md-only recipe whose deliverable-collection shape this recipe mirrors.
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements; project-local recipes are discovered from `.claude/skills/recipe-*` by `manage-config list-recipes`.
- `plan-marshall:phase-3-outline` Step 2.5 — loads this skill with input parameters.
