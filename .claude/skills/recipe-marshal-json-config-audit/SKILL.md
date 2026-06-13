---
name: recipe-marshal-json-config-audit
description: Domain-invariant recipe that audits and improves .plan/marshal.json across nine aspects (default-surfacing, dead-config, docs, naming, units, plus the D5 governance principles — ownership, house-rules, placement, anti-speculation) at a hard-coded T4/module cell
user-invocable: false
allowed-tools: Read, Glob, Bash, AskUserQuestion, Skill
implements: plan-marshall:extension-api/standards/ext-point-recipe
recipe_domain: plan-marshall-plugin-dev
recipe_profile: implementation
---

# Recipe: marshal.json Configuration Audit

Generic, domain-invariant recipe skill that drives a plan to **audit and improve `.plan/marshal.json`** — the project configuration file `setup` / `marshall-steward` seed and every phase consumes. Where `recipe-refactor-to-profile-standards` brings code into compliance with profile standards and `recipe-simplify-codebase` sweeps surplus structure, this recipe inspects the live configuration along nine aspects and collects one deliverable per aspect.

The first five aspects are the structural-hygiene audit (default-surfacing, dead-config, docs, naming, units). Aspects 6–9 enforce the **config-design governance principles** — the ownership, house-rules, placement, and anti-speculation rules defined once in [`config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md). The governance aspects xref that standard for every rule body and never inline it.

Like `recipe-simplify-codebase` it is an LLM-driven, SKILL.md-only deliverable-collection workflow (no scripts): the phase-3-outline recipe path loads it to produce a config-audit `solution_outline.md`.

Unlike the interactive recipes, this recipe **hard-codes** its `(thoroughness, scope)` cell instead of gathering it from the user. It implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — expand and consume — but **skips the gather step**, supplying a fixed identifier + expanded instruction per the contract's gather → expand → consume model.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |

The recipe's discovery metadata (`recipe_domain`, `recipe_profile`) is declared in this skill's YAML frontmatter — `manage-config list-recipes` reads it from frontmatter, the sole source of truth; the markdown body is never scanned for these keys.

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

## Step 3: Collect the nine audit deliverables

Collect **one deliverable per audit aspect** below. Each deliverable carries: a title, a description, `change_type`, `execution_mode: automated`, `module: plan-marshall`, affected files, and resolved verification commands. Record each deliverable's `T4 × module` cell for the floor-graded self-report (the quality signal — there is no blocking gate); the running plan consumes the expanded instruction (from `status.json` metadata `coverage_instruction`) to govern review depth and breadth per the coverage-gathering contract.

Aspects 1–5 are the structural-hygiene audit; aspects 6–9 enforce the config-design governance principles. Every governance aspect cross-references [`config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md) for its rule body and MUST NOT restate the rule text — the standard is the single source of truth.

### Aspect 1 — Default-surfacing completeness (`change_type: tech_debt`)

Verify that every config default `setup` / `marshall-steward` is supposed to write is materialised in `.plan/marshal.json`. Trace each code-side default to the file and flag any that exists in code but is absent from the file (code-default-but-not-in-file gaps). The deliverable materialises the missing defaults into `marshal.json`.

### Aspect 2 — Dead-config detection (`change_type: tech_debt`)

For every key present in `marshal.json`, trace every codebase usage and verify the value is actually consumed with real effect (not a no-op read, not an orphaned reference). Produce an unused/orphaned-key list.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the orphaned-key list; **deletion happens ONLY after explicit user confirmation**. The running task MUST raise an `AskUserQuestion` presenting the proposed removals and MUST NOT delete any key until the user confirms. The audit proposes; the user confirms.

### Aspect 3 — Documentation coverage (`change_type: tech_debt`)

Verify that every config key in `marshal.json` is surfaced in `doc/user/configuration.adoc`. Flag undocumented keys. The deliverable adds the missing documentation rows.

### Aspect 4 — Naming-scheme consistency (`change_type: tech_debt`)

Assess whether the keys follow a uniform, conflict-free naming scheme. Identify inconsistencies and conflicts (e.g. mixed separators, divergent prefixes, two keys that mean the same thing), and propose the renames that resolve them.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the rename list; **renames happen ONLY after explicit user confirmation**. Renames are breaking, so the running task MUST raise an `AskUserQuestion` presenting the proposed renames and MUST NOT apply any rename until the user confirms. On confirmation, the deliverable applies the renames in `marshal.json` (and the config-reading code that consumes each renamed key, within the module/T4 scope cell). The audit proposes; the user confirms; the recipe applies on agreement.

### Aspect 5 — Unit sanity (`change_type: tech_debt`)

Assess whether each value's unit is sensible (e.g. a raw `50000` token budget vs `50` thousands or `"50K"`), and propose the value changes that make units read well.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the unit-corrected values; **value changes happen ONLY after explicit user confirmation**. The running task MUST raise an `AskUserQuestion` presenting the proposed value changes and MUST NOT apply any change until the user confirms. On confirmation, the deliverable applies the corrected values in `marshal.json`. The audit proposes; the user confirms; the recipe applies on agreement.

**Follow-up-plan escape hatch (scope-bounded)**: retain the follow-up-plan path ONLY for changes whose blast radius genuinely exceeds the audit's module/T4 scope cell. When the assessment finds that fixing units would cascade beyond the `plan-marshall` module — touching call sites across other modules — the deliverable records the finding and recommends a SEPARATE follow-up plan instead of widening this one. Unit changes that stay within the module/T4 cell are applied here on confirmation rather than deferred.

### Aspect 6 — Ownership: tool vs foreign system (`change_type: tech_debt`)

Apply **Rule 1** of [`config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md) § "Tool vs foreign system" to every key in `marshal.json`. The governing test — *store a foreign value only if the user may legitimately diverge from it* — and the three-outcome table (overridable seed / fake choice / refactor litter) are defined in the standard; do NOT restate them here. Using the T4 relation model (Step 2), classify each key that seeds from or mirrors a foreign system into one of the standard's three outcomes, and flag every **fake choice** (a structural rule enforces equality with the foreign source, so no independent value is valid) and every **refactor litter** key (looks overridable but has no read-path). The deliverable proposes the narrow-constraint replacement or removal per the standard's Action column.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the foreign-mirror removal/replacement list; **removal happens ONLY after explicit user confirmation**. Removing a foreign-mirror key is breaking, so the running task MUST raise an `AskUserQuestion` presenting the proposed changes and MUST NOT remove or rewrite any key until the user confirms. The audit proposes; the user confirms; the recipe applies on agreement.

### Aspect 7 — House-rules leak: tool vs the meta-project's own convention (`change_type: tech_debt`)

Apply **Rule 2** of [`config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md) § "Tool vs the meta-project's own convention" to every key. The three-tier model (universal truth / meta-project convention / consumer choice) and the recurring **tier-2-masquerading-as-tier-1-or-3** defect are defined in the standard; do NOT restate them here. Classify each key (and any `DEFAULT_*` seed it derives from) into the standard's three tiers, and flag every tier-2 house rule shipped as a `DEFAULT_*` seed or a runtime invariant — a plan-marshall opinion imposed on every consumer rather than seeded as advisory prose. The deliverable proposes demoting each leaked house rule to advisory prose (or removing the seed) per the standard's shipping policy.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the house-rule-leak demotion/removal list; **the change happens ONLY after explicit user confirmation**. Demoting or removing a shipped default is breaking, so the running task MUST raise an `AskUserQuestion` presenting the proposed changes and MUST NOT apply any change until the user confirms. The audit proposes; the user confirms; the recipe applies on agreement.

### Aspect 8 — Placement: intrinsic property vs workflow policy (`change_type: tech_debt`)

Apply **Rule 5** of [`config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md) § "Placement" to every key. The distinction — *a tool's intrinsic property* lives with the tool's provider/skill, *workflow policy about using the tool* lives with the phase/step that applies it — is defined in the standard; do NOT restate it here. Flag every key placed under the wrong owner (e.g. a wait-timeout consumed by the finalize step that lives under the CI provider's block instead of `plan.phase-6-finalize`). The deliverable proposes relocating each misplaced key to its correct owner, carrying the Rule 3 lossless-migration discipline (read-path + values move together) into the relocation.

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the relocation list; **relocations happen ONLY after explicit user confirmation**. Relocating a key is breaking, so the running task MUST raise an `AskUserQuestion` presenting the proposed relocations and MUST NOT move any key until the user confirms. The audit proposes; the user confirms; the recipe applies on agreement.

### Aspect 9 — Anti-speculation: no generalization before its second case (`change_type: tech_debt`)

Apply **Rule 6** of [`config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md) § "Don't ship a generalization before its second concrete case" to every block in `marshal.json`. The YAGNI test — a generalization built before a second concrete case exists is removal-worthy by default — is defined in the standard; do NOT restate it here. Using the T4 relation model, flag every condition-scoped policy engine, override layer, or generalized block introduced empty (no populated second case driving it). The deliverable proposes collapsing each speculative generalization back to its single concrete case (or removing it outright).

**User-confirmation gate (mandatory)**: this deliverable's audit step PROPOSES the speculative-generalization collapse/removal list; **the change happens ONLY after explicit user confirmation**. Collapsing or removing a config block is breaking, so the running task MUST raise an `AskUserQuestion` presenting the proposed changes and MUST NOT apply any change until the user confirms. The audit proposes; the user confirms; the recipe applies on agreement.

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
- `## Summary` — the audit cell (`module × T4`), the config file under audit (`.plan/marshal.json`), the five structural-hygiene aspects, and the four governance aspects (6–9) that enforce the `config-design-principles.md` rules. State that aspects 2, 4, 5, 6, 7, 8, and 9 fix on agreement (propose-then-apply-on-confirm), not assess-only.
- `## Overview` — the audit radius (the `plan-marshall` module) and the relation model the T4 cell builds.
- `## Deliverables` — one deliverable per audit aspect (Aspects 1–9 above), each carrying its `T4 × module` cell declaration, the user-confirmation gates for aspects 2, 4, 5, 6, 7, 8, and 9 (propose-then-apply-on-confirm), and the scope-bounded aspect-5 follow-up-plan escape hatch. The governance aspects (6–9) each cross-reference `config-design-principles.md` for their rule body.

**4d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Enforcement

**Execution mode**: Deliverable-collection recipe — declare the hard-coded cell, resolve the radius, collect the nine audit deliverables, write the solution outline. Loaded by phase-3-outline's recipe path; not user-invocable.

**Prohibited actions:**
- Never raise an `AskUserQuestion` for the coverage cell — the cell is hard-coded `T4 / module` (Step 1). The only `AskUserQuestion`s this recipe drives are the per-aspect confirmation gates (aspect-2 deletion, aspect-4 rename, aspect-5 value change, aspect-6 foreign-mirror removal, aspect-7 house-rule demotion, aspect-8 relocation, aspect-9 generalization collapse) in the running plan.
- Never restate the thoroughness ladders, the grade-to-the-floor rule, the coupling constraint, or the cell → instruction expansion table — cross-reference `dev-agent-behavior-rules/standards/thoroughness.md` and `coverage-gathering-contract.md`.
- Never restate the config-design governance rule bodies (Rule 1 ownership, Rule 2 house-rules, Rule 5 placement, Rule 6 anti-speculation) — aspects 6–9 cross-reference `manage-config/standards/config-design-principles.md` and MUST NOT inline the rule text.
- Never apply a confirmed-only change without explicit user confirmation: never delete an orphaned config key (aspect 2), apply a rename (aspect 4), apply a unit/value change (aspect 5), remove a foreign-mirror key (aspect 6), demote/remove a leaked house-rule default (aspect 7), relocate a misplaced key (aspect 8), or collapse/remove a speculative generalization (aspect 9) until the user confirms the proposed list via `AskUserQuestion`.
- Never access `.plan/` files directly — all access goes through `python3 .plan/execute-script.py` manage-* scripts.

**Constraints:**
- The persisted cell is `coverage_thoroughness=T4`, `coverage_scope=module`, plus the `coverage expand`-produced `coverage_instruction`, written to `status.json` metadata.
- Each collected deliverable declares `module: plan-marshall` and its `T4 × module` cell for the floor-graded self-report.
- A units rework (aspect 5) whose blast radius genuinely exceeds the module/T4 scope cell is recommended as a separate follow-up plan rather than widening the audit plan; unit changes that stay within the cell are applied on confirmation.

## Related

- `plan-marshall:dev-agent-behavior-rules` `standards/thoroughness.md` — the scope × thoroughness ladders, grade-to-the-floor rule, and coupling constraint (single source of truth).
- `plan-marshall:dev-agent-behavior-rules` `standards/coverage-gathering-contract.md` — the coverage-gathering contract this recipe implements (expand → consume; persistence; cell → instruction table). This recipe skips the gather step.
- `plan-marshall:manage-config` `coverage expand` — the static identifier → instruction expander that enforces the coupling constraint.
- `plan-marshall:manage-config` [`standards/config-design-principles.md`](../../../marketplace/bundles/plan-marshall/skills/manage-config/standards/config-design-principles.md) — the config-design governance rules (ownership, house-rules, field migration, placement, anti-speculation) that audit aspects 6–9 enforce. Single source of truth for every governance rule body; this recipe xrefs it and never inlines the rules.
- `plan-marshall:recipe-simplify-codebase` — the sibling SKILL.md-only recipe whose deliverable-collection shape this recipe mirrors.
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements; project-local recipes are discovered from `.claude/skills/recipe-*` by `manage-config list-recipes`.
- `plan-marshall:phase-3-outline` Step 2.5 — loads this skill with input parameters.
