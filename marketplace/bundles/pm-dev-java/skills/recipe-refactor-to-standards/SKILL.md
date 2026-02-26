---
name: recipe-refactor-to-standards
description: Recipe skill for refactoring production code to comply with configured implementation profile standards, package by package
user-invokable: false
---

# Recipe: Refactor to Implementation Standards

Predefined recipe skill for refactoring production code to comply with the currently configured implementation profile standards. Iterates module-by-module, package-by-package.

**Profile**: `implementation`
**Skills applied**: Dynamically resolved from `resolve-domain-skills --domain java --profile implementation` (core + implementation defaults and optionals)

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

---

## Step 1: Resolve Skills

Resolve the skills for the `implementation` profile from the configured skill domains. This picks up whatever skills are currently configured — including project-level skills attached to the domain.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-domain-skills --domain java --profile implementation
```

**Output (TOON)**:
```toon
status	success
domain	java
profile	implementation
defaults	{"pm-dev-java:java-core": "Core Java patterns including modern features and performance optimization"}
optionals	{"pm-dev-java:java-cdi": "CDI patterns...", "pm-dev-java:java-maintenance": "Java code maintenance..."}
```

Store all resolved skill names (keys from `defaults` and `optionals`). Build the comma-separated `--skills` argument for deliverables.

---

## Step 2: List Modules

Query the project architecture for available modules:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules
```

**Output (TOON)**:
```toon
modules[4]:
  - my-parent
  - my-core
  - my-api
  - my-web
```

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, modules without source files).

---

## Step 3: Load Packages Per Module

For each selected module, query full module details including all packages:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  module --name {module_name} --full
```

**Output (TOON)** — relevant fields:
```toon
module:
  name: my-core
  path: my-core

paths:
  sources[1]:
    - src/main/java

key_packages[3]{name,description}:
de.cuioss.portal.auth,Authentication core logic
de.cuioss.portal.auth.impl,Authentication implementation
de.cuioss.portal.auth.model,Authentication data model

packages[3]{name,path,has_package_info,file_count}:
de.cuioss.portal.auth	my-core/src/main/java/de/cuioss/portal/auth	true	5
de.cuioss.portal.auth.impl	my-core/src/main/java/de/cuioss/portal/auth/impl	false	3
de.cuioss.portal.auth.model	my-core/src/main/java/de/cuioss/portal/auth/model	false	2

commands[3]:
  - module-tests
  - verify
  - quality-gate
```

The `key_packages` table contains the packages discovered during architecture analysis. The `packages` table (in `--full` mode) includes `file_count` — the number of direct source files per package. The actual file list is available in `derived-data.json` for programmatic access.

Build package inventory from architecture data. Skip modules with empty `key_packages`.

---

## Step 4: Analysis

For each package, run read-only quality analysis:

```
Task: pm-dev-java:java-quality-agent
  model: haiku
  Input:
    target: {sources_path}/{package_as_path}/
    module: {module_name}
    plan_id: {plan_id}
```

Where `{package_as_path}` is the package name with dots replaced by `/` (e.g., `de.cuioss.portal.auth` → `de/cuioss/portal/auth`).

Record compliance findings per package:
- Current compliance level (percentage)
- Specific violations found (patterns, modern features, method design, performance)
- Number of files needing changes

Skip packages with 100% compliance (no deliverable needed).

---

## Step 5: Deliverable Creation

Create one deliverable per package with compliance gaps > 0.

Each deliverable:
- **Title**: `Refactor: {module}/{package_name}`
- **Description**: Summary of quality findings and what needs to change
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `java`
  - `module`: `{module_name}`
  - `profile`: `implementation`
- **Skills**: All skills resolved in Step 1 (comma-separated)
- **Affected files**: All `.java` files in the package (from architecture data `files` field)

Write each deliverable via manage-plan-documents:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  deliverable add \
  --plan-id {plan_id} \
  --title "Refactor: {module}/{package_name}" \
  --description "{compliance_summary}" \
  --change-type tech_debt \
  --domain java \
  --module {module} \
  --profile implementation \
  --skills "{resolved_skills_csv}" \
  --files "{file_list}"
```

---

## Step 6: Outline Writing

Write `solution_outline.md` with all deliverables, grouped by module:

```markdown
# Solution Outline: Refactor to Implementation Standards

## Scope
{N} packages across {M} modules requiring refactoring to comply with implementation profile standards.

## Resolved Skills
{list of resolved skills from Step 1}

## Module: {module_name}

### Deliverable {n}: Refactor {module}/{package_name}
- **Files**: {count} Java files
- **Findings**: {summary}
- **Profile**: implementation

...
```

---

## Task Execution

Each task uses `java-refactor-agent` (Sonnet) with the package scope. The agent:
1. Loads the skills specified in the deliverable (resolved from implementation profile)
2. Applies refactoring rules to all files in the package
3. Verifies build passes after changes

---

## Related

- `plan-marshall:manage-plan-marshall-config resolve-domain-skills` — Dynamic skill resolution
- `plan-marshall:analyze-project-architecture architecture module` — Module/package query
- `pm-dev-java:java-quality-agent` — Read-only quality analysis agent
- `pm-dev-java:java-refactor-agent` — Refactoring execution agent
