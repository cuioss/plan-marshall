---
name: recipe-refactor-to-profile-standards
description: Domain-invariant recipe for refactoring code to comply with configured profile standards, package by package
user-invokable: false
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
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules
```

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, modules without source/test files).

---

## Step 3: Load Packages and Create Deliverables

For each selected module, query full module details:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  module --name {module_name} --full
```

Use the `{recipe_package_source}` field from the output:
- If `recipe_package_source` is `packages` — iterate the `packages` table (production source packages)
- If `recipe_package_source` is `test_packages` — iterate the `test_packages` table (test source packages)

Skip modules where the selected table is empty.

Create one deliverable per package:
- **Title**: `Refactor: {module}/{package_name}` (when `recipe_package_source` is `packages`) or `Refactor tests: {module}/{package_name}` (when `recipe_package_source` is `test_packages`)
- **Description**: `Refactor to comply with {recipe_profile} profile standards`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `{recipe_domain}`
  - `module`: `{module_name}`
  - `profile`: `{recipe_profile}`
- **Skills**: All skills resolved in Step 1 (comma-separated)
- **Affected files**: All files in the package (from architecture data `files` field)

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  deliverable add \
  --plan-id {plan_id} \
  --title "{title}" \
  --description "Refactor to comply with {recipe_profile} profile standards" \
  --change-type tech_debt \
  --domain {recipe_domain} \
  --module {module} \
  --profile {recipe_profile} \
  --skills "{resolved_skills_csv}" \
  --files "{file_list}"
```

---

## Step 4: Outline Writing

Write `solution_outline.md` with all deliverables, grouped by module:

```markdown
# Solution Outline: Refactor to {recipe_profile} Standards

## Scope
{N} packages across {M} modules to refactor for {recipe_profile} profile standards compliance.

## Resolved Skills
{list of resolved skills from Step 1}

## Module: {module_name}

### Deliverable {n}: {title}
- **Files**: {count}
- **Profile**: {recipe_profile}

...
```

---

## Related

- `plan-marshall:manage-plan-marshall-config resolve-domain-skills` — Dynamic skill resolution
- `plan-marshall:analyze-project-architecture architecture module` — Module/package query
- `pm-workflow:plan-marshall` recipe workflow — Sets metadata and invokes phase-3-outline
- `pm-workflow:phase-3-outline` Step 2.5 — Loads this skill with input parameters
