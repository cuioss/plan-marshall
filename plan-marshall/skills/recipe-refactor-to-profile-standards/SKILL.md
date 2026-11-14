---
name: recipe-refactor-to-profile-standards
description: Domain-invariant recipe for refactoring code to comply with configured profile standards, package by package
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Refactor to Profile Standards

Generic, domain-invariant recipe skill for refactoring code to comply with the configured profile standards. A single run spans ALL auto-detected domains × one chosen profile, enforcing a per-domain user-selected standards-skill set, iterating module-by-module, package-by-package. The detected domains, chosen profile, derived package source, and per-domain selected skills are persisted to `status.json` metadata by the selection flow and passed as input parameters by phase-3-outline.

**No separate analysis step** — each deliverable is one package. The task executor loads the profile skills and handles both analysis and fixing in a single pass. Packages that are already compliant complete quickly with no changes.

## Input

All values below are read from `status.json` metadata, where the built-in selection flow (`workflow/selection-flow.md`) persists them — see that document for the gather mechanics (domain auto-detect, dynamic profile single-select, data-driven `package_source`, per-domain paginated skill multi-select). Do not inline-copy the selection screens.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_domains` | string | Yes | Comma-separated auto-detected domain list (e.g., `java,javascript`). One run spans every listed domain. |
| `recipe_profile` | string | Yes | Single profile name — any profile a detected domain exposes (NOT limited to `implementation`/`module_testing`; e.g. `documentation`, `integration_testing`). |
| `recipe_package_source` | string | Yes | Architecture `manage-architecture module --full` field to iterate, derived data-driven from the selected profile's declared `package_source` (`packages`/`test_packages` today; open to any architecture field a future profile declares). |
| `recipe_selected_skills__{domain}` | string | Yes (one per detected domain) | Per-domain comma-separated list of the user-finalized standards-skill notations to enforce for that domain. One field per domain in `recipe_domains` that exposes `recipe_profile`. |

---

## Step 0: Gather + expand + persist the coverage cell

This recipe implements the [coverage-gathering contract](../persona-plan-marshall-agent/standards/coverage-gathering-contract.md). At invocation, gather the `(thoroughness, scope)` cell from the user via the contract's canonical `AskUserQuestion` shape — a `scope` question (`component`/`module`/`overall` + an explicit `inherit (default — behave exactly as today)`) and a `thoroughness` question (`T1`…`T5` + `inherit`). The coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) constrains the offered scope options when the user picks `T4`/`T5`. Then expand the identifier and persist BOTH the identifier and the expanded instruction to `status.json` metadata (this recipe is plan-bound):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness {T} --scope {S}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value {T}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value {S}
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

`coverage expand` applies the coupling check at expand time and emits `error_type: coverage_coupling_violation` for an incoherent cell — re-prompt the gather on that error (do NOT re-implement the coupling math). Consume the **expanded instruction** (NOT the raw cell) in Steps 2–3. `inherit/inherit` (the default) reproduces today's module/package full-read iteration. See `persona-plan-marshall-agent/standards/thoroughness.md` for the ladders and `coverage-gathering-contract.md` for the gather shape and cell→instruction table — restate neither here.

---

## Step 1: Resolve Per-Domain Selected Skills

The authoritative skill set per domain is the user-finalized `recipe_selected_skills__{domain}` set persisted by the selection flow — NOT the full `defaults`+`optionals` resolution. Iterate the detected domains and read each domain's selected set.

For each `{domain}` in `recipe_domains`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field recipe_selected_skills__{domain}
```

The returned comma-separated notations ARE the enforced skill set for that domain — build the per-domain `--skills` argument directly from it. `resolve-domain-skills` MAY still be consulted to validate or expand the notations for the chosen profile, but it is NOT the authoritative source; the user-selected set is:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain {domain} --profile {recipe_profile}
```

Store the per-domain selected skill sets keyed by domain, for use when building each deliverable's `--skills` argument in Step 3 (a deliverable for domain `D` carries domain `D`'s selected set).

---

## Step 2: List Modules

Query the project architecture for available modules:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, modules without source/test files).

**Coverage breadth (from Step 0's expanded instruction)**: the gathered scope rung pre-filters this module list and the per-package radius — `component` → a single component/package sub-tree; `module` → a bundle set; `overall` → every module. `inherit/inherit` pre-filters nothing (today's full module/package iteration).

---

## Step 3: Load Packages and Collect Deliverable Data

Iterate per domain in `recipe_domains` × that domain's selected modules. One plan spans all detected domains; each deliverable's `domain` is the iterated domain, and it carries that domain's selected skill set (from Step 1) as `--skills`.

For each selected module (within the current domain), query full module details:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  module --module {module_name} --full
```

Use the `{recipe_package_source}` field from the output as the architecture table to iterate. `recipe_package_source` is data-driven from the selected profile (valid for any profile, not assumed to be `packages`/`test_packages` only):
- when it is `packages` — iterate the `packages` table (production source packages)
- when it is `test_packages` — iterate the `test_packages` table (test source packages)
- for any other architecture field a future profile declares — iterate that named table

Skip modules where the selected table is empty.

**If a package has `file_count: 0`**: The architecture module did not resolve files for this package. Discover files via the canonical `manage-files discover` subcommand:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root {module_path}/{package_path} \
  --glob "**/*.md" \
  --glob "**/*.py" \
  --include-files
```

Capture the returned `paths` array as the discovered file list. Skip packages that have no files on disk.

Collect one deliverable per package (in-memory, for use in Step 4):
- **Title**: `Refactor ({recipe_profile}): {module}/{package_name}` — derived from the selected profile so it reads cleanly for any profile (no hardcoded `packages`/`test_packages` title branch)
- **Description**: `Refactor to comply with {recipe_profile} profile standards`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `{domain}` (the iterated domain from `recipe_domains`)
  - `module`: `{module_name}`
  - `profile`: `{recipe_profile}`
- **Skills**: the current domain's user-selected skill set from Step 1 (`recipe_selected_skills__{domain}`, comma-separated)
- **Affected files**: All files in the package (from architecture data `files` field, or via `manage-files discover` when the architecture record reports `file_count: 0`)

> **Coverage contract**: the per-package read depth is governed by the cell gathered + expanded in Step 0 — no longer an implicit fixed rung. The gathered thoroughness rung sets the depth: `T2` → full-read each file in the package; `T3` → also trace each file's callers and tests; `T4`/`T5` → build a scope-wide relation model across the radius before any change. The unit's thoroughness grades to the FLOOR across its packages (a campaign where some packages were only sampled is graded at the sampled rung). The coupling constraint `reject thoroughness ≥ T4 ∧ scope < component` is why a `T4`/`T5` sweep operates at package/module scope, never change-set. `inherit/inherit` reproduces today's full-read iteration. See the two-dial ladders and the grade-to-the-floor rule in [`persona-plan-marshall-agent/standards/thoroughness.md`](../persona-plan-marshall-agent/standards/thoroughness.md), and the gather/expand/consume obligation in [`coverage-gathering-contract.md`](../persona-plan-marshall-agent/standards/coverage-gathering-contract.md).

---

## Step 4: Outline Writing

**4a. Read the deliverable template** to understand the required structure:

```text
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Read an example** to see the full document skeleton:

```text
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/examples/refactoring.md
```

**4c. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4d. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include these sections in order:
- `# Solution: Refactor to {recipe_profile} Standards` header with `plan_id`, `created`, `compatibility` metadata
- `## Summary` — scope description ({N} packages across {M} modules spanning the detected domains)
- `## Overview` — per-domain selected-skills list and module breakdown
- `## Deliverables` — all deliverables from Step 3, grouped by domain then module, using the template structure from 4a

**4e. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Related

- `workflow/selection-flow.md` — Built-in recipe selection flow (domain auto-detect, dynamic profile single-select, data-driven `package_source`, per-domain skill multi-select) that persists the multi-domain input field set
- `plan-marshall:manage-config resolve-domain-skills` — Per-domain skill validation/expansion for the chosen profile
- `plan-marshall:manage-architecture architecture module` — Module/package query
- `plan-marshall:plan-marshall` recipe workflow — Sets metadata and invokes phase-3-outline
- `plan-marshall:phase-3-outline` Step 2.5 — Loads this skill with input parameters
