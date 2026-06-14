---
name: recipe-modularization-audit-plan-marshall-skills
description: Domain-invariant recipe that drives a modularization-audit campaign over a gathered skill corpus at a hard-coded T5/overall cell — detects over-long step sequences, numbering defects, and document bloat, and emits one extraction/renumber deliverable per offending skill
user-invocable: false
mode: workflow
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion, Skill
implements: plan-marshall:extension-api/standards/ext-point-recipe
recipe_domain: plan-marshall-plugin-dev
recipe_profile: implementation
---

# Recipe: Modularization Audit for plan-marshall Skills

Generic, domain-invariant recipe skill that drives a plan to **audit a corpus of skill documents for modularization opportunities** — over-long inline step sequences that belong in referenced sub-documents, numbering defects, and document bloat. Where `recipe-marshal-json-config-audit` audits the live `.plan/marshal.json` config file and `recipe-plugin-compliance` sweeps marketplace bundles for architecture compliance, this recipe inspects every `SKILL.md` and sub-document beneath a resolved target root and collects one remediation deliverable per offending skill.

Like `recipe-marshal-json-config-audit` it is an LLM-driven, SKILL.md-only deliverable-collection workflow (no scripts): the phase-3-outline recipe path loads it to produce a modularization-audit `solution_outline.md`.

This recipe has **two orthogonal, independent dials** at its runtime:

- A **hard-coded COVERAGE CELL** (`thoroughness=T5`, `scope=overall`) — the depth and breadth of the audit. It is NOT gathered from the user. The recipe implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — expand and consume — but **skips the gather step** for the cell, supplying the fixed identifier + expanded instruction per the contract's gather → expand → consume model.
- A **gathered CORPUS ROOT** — the tree the audit is rooted at. It IS gathered, via `AskUserQuestion` (Step 1). The cell governs HOW DEEPLY/BROADLY the audit runs; the corpus root governs WHAT TREE it runs over. The two are distinct and never conflated: the no-gather prohibition applies to the CELL ONLY, never to the target.

Both the resolved cell and the resolved target root are persisted to `status.json` metadata.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |

The recipe's discovery metadata (`recipe_domain`, `recipe_profile`) is declared in this skill's YAML frontmatter — `manage-config list-recipes` reads it from frontmatter, the sole source of truth; the markdown body is never scanned for these keys.

There is no `recipe_scope` / `recipe_thoroughness` input — the COVERAGE CELL is fixed (see Step 1). The CORPUS ROOT is NOT a static input either — it is gathered at Step 1 via `AskUserQuestion`. The recipe is plan-bound; it persists BOTH the resolved cell AND the resolved target root to `status.json` metadata.

---

## Step 1: Gather the target corpus root + declare the hard-coded coverage cell

This step does TWO distinct things — gather the corpus root, then declare/expand/persist the fixed coverage cell.

### Gather the CORPUS ROOT (via `AskUserQuestion`)

Raise an `AskUserQuestion` to resolve the tree the audit is rooted at. Offer:

- **DEFAULT** (pre-selected) = `marketplace/bundles/plan-marshall` — audit all of that bundle's skills.
- **ALTERNATIVE** = `.claude/skills` — the project-local skills tree.
- **VARIANT** = an Other / free-text explicit path to a narrower resource, e.g. a single skill dir such as `marketplace/bundles/plan-marshall/skills/marshall-steward`, or any sub-path.

Resolve the chosen value to `{target_root}` and persist it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field audit_target_root --value {target_root}
```

This is the ONE gather the recipe drives, and it is the CORPUS ROOT — never the coverage cell.

### Declare + expand + persist the hard-coded COVERAGE CELL (NO gather)

Hard-code `thoroughness=T5, scope=overall`:

- `scope=overall` — the audit is exhaustive over whatever tree is rooted at `{target_root}`: every `SKILL.md` plus every sub-document recursively.
- `thoroughness=T5` — exhaustive / adversarial with a loop-until-dry completeness sweep. Required because modularization detection must trace cross-document relationships (which step sequences belong in which sub-document) and re-attack its own coverage until no further over-long sequence or numbering defect surfaces.

Coupling is satisfied by construction (`overall ≥ component`). This recipe does **NOT** raise an `AskUserQuestion` for the cell — it skips the contract's gather step entirely for the cell and supplies the fixed pair directly. Expand the identifier into the operational instruction block and persist BOTH the identifier and the expanded instruction to `status.json` metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness T5 --scope overall
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value T5
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value overall
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

The ladders (T1–T5), the grade-to-the-floor rule, and the coupling constraint are defined once in [`dev-agent-behavior-rules/standards/thoroughness.md`](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/thoroughness.md), and the cell → instruction expansion table lives in [`dev-agent-behavior-rules/standards/coverage-gathering-contract.md`](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md); do NOT restate either here. `coverage expand` enforces the coupling constraint and emits `error_type: coverage_coupling_violation` for an incoherent cell — the fixed `T5 / overall` pair satisfies the constraint by construction, so a violation here is a contract bug, not a re-gather case.

Consume the **expanded instruction** (NOT the raw cell) when collecting the audit deliverables in Step 4.

---

## Step 2: Enumerate the audit corpus rooted at `{target_root}`

Recursively beneath the `{target_root}` resolved in Step 1, enumerate every skill directory and, within each, every `SKILL.md` plus every `.md` file under `standards/`, `references/`, and `workflow/` (recursively). When `{target_root}` is itself a single skill dir (the VARIANT case), the corpus is that one skill's `SKILL.md` plus its sub-documents.

Use `Glob` rooted at `{target_root}` for the sub-document enumeration — this is the documented fallback for sub-module markdown discovery, since `architecture files --module` stops at component granularity and does not reach the markdown files inside a component:

```
Glob: {target_root}/**/SKILL.md
Glob: {target_root}/**/standards/**/*.md
Glob: {target_root}/**/references/**/*.md
Glob: {target_root}/**/workflow/**/*.md
```

The recipe reads each enumerated document in full — the T5 thoroughness floor is full-read, so no document in the corpus is sampled or assumed.

---

## Step 3: Apply the per-document audit rules

For EACH enumerated document (the top-level `SKILL.md` AND every sub-document, recursively), the running plan applies three checks.

### Modularization opportunity

Detect long step / numbered sequences that should be extracted into referenced sub-documents loaded on demand. A sequence is an extraction candidate when it is long enough that the document carries more procedural detail than belongs inline — the two-digit-sequence-number signal in the "Numbering compliance" check is the primary trip-wire, and over-length per the plugin-doctor subdoc bloat thresholds ("No-bloat") is the secondary. The remediation is to extract the sequence into a `standards/` or `workflow/` sub-document and replace it inline with a thin reference plus a cross-link.

### Numbering compliance

Enforced across BOTH ordered-list items (`1.`, `2.`, … `10.`) AND numbered step / section headings (`### Step 1`, `## 10. Foo`):

- **single-digit-only** — any sequence that reaches a two-digit number (`10`, `11`, …) is a modularization signal: the sequence is too long and must be split into sub-documents (couples back to the "Modularization opportunity" check).
- **flat numbering** — no sub-numbering such as `2b`, `5.a.4`, `3.2`; all numbering is flat.
- **start-at-1** — numbering starts at `1` everywhere, never `0`.

### No-bloat (plugin-doctor)

Every resulting document (top-level plus any extracted sub-documents) must pass `pm-plugin-development:plugin-doctor`'s bloat classification. Cross-reference the subdoc thresholds owned by plugin-doctor — see [`pm-plugin-development:plugin-doctor` `doctor-skills.md`](../../../marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-skills.md) (sub-documents LARGE / BLOATED / CRITICAL line thresholds); do NOT restate the thresholds — delegate the gate to the doctor rule set. A `subdoc-bloat` BLOATED/CRITICAL finding is itself a modularization signal feeding back into the "Modularization opportunity" check.

---

## Step 4: Collect deliverables (one per skill with findings)

Collect **one deliverable per skill** in the corpus (rooted at `{target_root}`) that has at least one finding from the three audit checks in Step 3. Each deliverable carries:

- a title (`Modularize: {skill}`),
- `change_type: tech_debt`,
- `execution_mode: automated`,
- `domain: plan-marshall-plugin-dev`,
- `module: plan-marshall`,
- the affected files — the `SKILL.md` plus the sub-documents to split / renumber, plus the new sub-documents to create,
- a resolved verification command: `python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate --paths {skill-dir} --marketplace-root marketplace`.

Each deliverable records its `T5 × overall` cell for the floor-graded self-report (the quality signal — there is no blocking gate); the running plan consumes the expanded instruction (from `status.json` metadata `coverage_instruction`) to govern review depth and breadth per the coverage-gathering contract.

The recipe is deliverable-collection only — it writes `solution_outline.md`; it does NOT edit the audited skills itself.

---

## Step 5: Outline writing

**Read the deliverable template**:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include, in order:

- `# Solution: Modularization Audit for plan-marshall Skills` header with `plan_id`, `created`, `compatibility` metadata.
- `## Summary` — the audit cell (`overall × T5`), the resolved corpus root (`{target_root}`), and the three per-document audit rules.
- `## Overview` — the audit radius (the corpus rooted at `{target_root}`) and the cross-document relation model the T5 cell builds.
- `## Deliverables` — one deliverable per offending skill (Step 4 above), each carrying its `T5 × overall` cell declaration and its resolved plugin-doctor verification command.

**Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Enforcement

**Execution mode**: Deliverable-collection recipe — gather the corpus root, declare the hard-coded cell, enumerate the corpus rooted at the resolved target, apply the three per-document audit rules, collect one deliverable per offending skill, write the solution outline. Loaded by phase-3-outline's recipe path; not user-invocable.

**Prohibited actions:**
- Never gather the COVERAGE CELL via `AskUserQuestion` — the cell is hard-coded `T5 / overall` (Step 1, "Declare + expand + persist the hard-coded COVERAGE CELL"). The no-gather prohibition applies to the CELL ONLY, NOT the target — the target IS gathered (Step 1, "Gather the CORPUS ROOT"). The only `AskUserQuestion` this recipe drives is the corpus-root gather.
- Never mutate any audited skill during the recipe — the recipe collects deliverables only.
- Never restate the thoroughness ladders, the grade-to-the-floor rule, the coupling constraint, the cell → instruction expansion table, or the plugin-doctor bloat thresholds — cross-reference `dev-agent-behavior-rules/standards/thoroughness.md`, `coverage-gathering-contract.md`, and `plugin-doctor/standards/doctor-skills.md`.
- Never access `.plan/` files directly — all access goes through `python3 .plan/execute-script.py` manage-* scripts.

**Constraints:**
- The ONE `AskUserQuestion` this recipe drives is the corpus-root gather in Step 1.
- The persisted metadata is `audit_target_root={resolved root}`, `coverage_thoroughness=T5`, `coverage_scope=overall`, plus the `coverage expand`-produced `coverage_instruction`, written to `status.json` metadata.
- Each collected deliverable declares `module: plan-marshall` and its `T5 × overall` cell for the floor-graded self-report.

## Related

- `plan-marshall:dev-agent-behavior-rules` `standards/thoroughness.md` — the scope × thoroughness ladders, grade-to-the-floor rule, and coupling constraint (single source of truth).
- `plan-marshall:dev-agent-behavior-rules` `standards/coverage-gathering-contract.md` — the coverage-gathering contract this recipe implements (expand → consume; persistence; cell → instruction table). This recipe skips the gather step for the cell.
- `plan-marshall:manage-config` `coverage expand` — the static identifier → instruction expander that enforces the coupling constraint.
- `recipe-marshal-json-config-audit` — the sibling project-local SKILL.md-only recipe whose deliverable-collection shape this recipe mirrors.
- `pm-plugin-development:plugin-doctor` — the no-bloat gate the recipe delegates to (subdoc bloat thresholds).
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements; project-local recipes are discovered from `.claude/skills/recipe-*` by `manage-config list-recipes`.
- `plan-marshall:phase-3-outline` Step 3 — loads this skill with input parameters.
