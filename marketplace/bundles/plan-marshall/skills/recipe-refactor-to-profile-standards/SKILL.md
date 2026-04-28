---
name: recipe-refactor-to-profile-standards
description: Domain-invariant recipe for refactoring code to comply with configured profile standards, package by package
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Refactor to Profile Standards

Generic, domain-invariant recipe skill for refactoring code to comply with the configured profile standards. Iterates module-by-module, package-by-package. Domain, profile, and package source are passed as input parameters by phase-3-outline.

**No separate analysis step** — each deliverable is one package. The task executor loads the profile skills and handles both analysis and fixing in a single pass. Packages that are already compliant complete quickly with no changes.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_domain` | string | Yes | Domain key (e.g., `java`, `javascript`) |
| `recipe_profile` | string | Yes | Profile name (`implementation` or `module_testing`) |
| `recipe_package_source` | string | Yes | Architecture field to iterate (`packages` or `test_packages`) |

---

## Step 1: Resolve Skills

Resolve the skills for the selected profile from the configured skill domains:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain {recipe_domain} --profile {recipe_profile}
```

**Output (TOON)**:
```toon
status	success
domain	{recipe_domain}
profile	{recipe_profile}
defaults	{"bundle:skill-a": "Description A"}
optionals	{"bundle:skill-b": "Description B"}
```

Store all resolved skill names (keys from `defaults` and `optionals`). Build the comma-separated `--skills` argument for deliverables.

---

## Step 2: List Modules

Query the project architecture for available modules:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, modules without source/test files).

---

## Step 3: Load Packages and Collect Deliverable Data

For each selected module, query full module details:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  module --name {module_name} --full
```

Use the `{recipe_package_source}` field from the output:
- If `recipe_package_source` is `packages` — iterate the `packages` table (production source packages)
- If `recipe_package_source` is `test_packages` — iterate the `test_packages` table (test source packages)

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
- **Title**: `Refactor: {module}/{package_name}` (when `recipe_package_source` is `packages`) or `Refactor tests: {module}/{package_name}` (when `recipe_package_source` is `test_packages`)
- **Description**: `Refactor to comply with {recipe_profile} profile standards`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `{recipe_domain}`
  - `module`: `{module_name}`
  - `profile`: `{recipe_profile}`
- **Skills**: All skills resolved in Step 1 (comma-separated)
- **Affected files**: All files in the package (from architecture data `files` field, or via `manage-files discover` when the architecture record reports `file_count: 0`)

---

## Step 4: Outline Writing

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
- `# Solution: Refactor to {recipe_profile} Standards` header with `plan_id`, `created`, `compatibility` metadata
- `## Summary` — scope description ({N} packages across {M} modules)
- `## Overview` — resolved skills list and module breakdown
- `## Deliverables` — all deliverables from Step 3, grouped by module, using the template structure from 4a

**4e. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Related

- `plan-marshall:manage-config resolve-domain-skills` — Dynamic skill resolution
- `plan-marshall:manage-architecture architecture module` — Module/package query
- `plan-marshall:plan-marshall` recipe workflow — Sets metadata and invokes phase-3-outline
- `plan-marshall:phase-3-outline` Step 2.5 — Loads this skill with input parameters
