---
name: recipe-plugin-compliance
description: Recipe skill that sweeps marketplace bundles for plugin architecture compliance
user-invocable: false
allowed-tools: Read, Glob, Grep, Bash, Skill
---

# Recipe: Plugin Compliance Sweep

Recipe skill for sweeping all marketplace bundles against plugin architecture standards. Loaded by phase-3-outline when this recipe is selected.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |
| `recipe_domain` | `plan-marshall-plugin-dev` |
| `recipe_profile` | `implementation` |
| `recipe_package_source` | `packages` |

## Workflow

### Step 0: Gather + expand + persist the coverage cell

This recipe implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md). At invocation, gather the `(thoroughness, scope)` cell from the user via the contract's canonical `AskUserQuestion` shape — a `scope` question (`change-set`/`artifact`/`component`/`module`/`overall` + an explicit `inherit (default — behave exactly as today)`) and a `thoroughness` question (`T1`…`T5` + `inherit`). The coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) constrains the offered scope options when the user picks `T4`/`T5`.

Validate + expand the gathered pair in one call: `manage-config coverage expand --thoroughness {T} --scope {S}` validates the literal pair (re-prompt on `coverage_coupling_violation`; do NOT re-implement the coupling math) AND returns the operational instruction block. Then persist BOTH the identifier and the expanded instruction to `status.json` metadata (this recipe is plan-bound):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness {T} --scope {S}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value {T}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value {S}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

Consume the **expanded instruction** (NOT the raw cell) in Steps 2 and 3 below. `inherit/inherit` (the default) is behavior-preserving — Steps 2–3 run exactly as before (all bundles, today's per-package surface sweep). See `dev-agent-behavior-rules/standards/thoroughness.md` for the ladders and `coverage-gathering-contract.md` for the gather shape and cell→instruction table — restate neither here.

### Step 1: Resolve Skills

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain plan-marshall-plugin-dev --profile implementation
```

Collect core + implementation defaults and optionals for skill references in deliverables.

### Step 2: List Modules

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get --domain plan-marshall-plugin-dev
```

Then list available modules (marketplace bundles):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

Present module list to user for filtering. User may select all or a subset.

**Coverage breadth (from Step 0's expanded instruction)**: the gathered scope rung pre-filters this module list — `component` → one bundle/skill; `module` → a bundle set; `overall` → all bundles (today's default). `inherit/inherit` pre-filters nothing (today's all-bundle sweep).

### Step 3: Create Deliverables Per Bundle

For each selected module (bundle), load its packages:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  module --name {module_name} --full
```

Iterate the `packages` field. For each package (skill/agent/command directory), create one deliverable:

```
Title: Compliance: {module}/{package}
change_type: tech_debt
execution_mode: automated
domain: plan-marshall-plugin-dev
module: {module_name}
profile: implementation
skills: {resolved from Step 1}
affected_files: {files from architecture data}
```

Focus areas per deliverable:
- SKILL.md/agent/command frontmatter correctness
- Enforcement block presence and structure (script-bearing skills)
- Standards document cross-references
- Script naming and output contract compliance

**Coverage depth (from Step 0's expanded instruction)**: the gathered thoroughness rung sets each deliverable's focus depth — `T1`/`T2` → the frontmatter + enforcement-block surface above; `T3` → also trace standards cross-references; `T4`/`T5` → also build a cross-skill relation-graph and run a loop-until-dry completeness pass per bundle. Record the per-deliverable cell. `inherit/inherit` keeps today's surface-only depth.

### Step 4: Write Solution Outline

**4a. Read the deliverable template** to understand the required structure:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Read an example** to see the full document skeleton:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/examples/refactoring.md
```

**4c. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4d. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include these sections in order:
- `# Solution: {title}` header with `plan_id`, `created`, `compatibility` metadata
- `## Summary` — 2-3 sentences describing approach
- `## Overview` — ASCII diagram showing scope
- `## Deliverables` — All deliverables from Step 3, grouped by module, using the template structure

**4e. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```
