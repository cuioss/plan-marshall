---
name: recipe-refactor-to-test-standards
description: Recipe skill for refactoring test code to comply with configured module_testing profile standards, test-package by test-package
user-invokable: false
---

# Recipe: Refactor to Test Standards

Predefined recipe skill for refactoring test code to comply with the currently configured module_testing profile standards. Iterates module-by-module, test-package-by-test-package.

**Profile**: `module_testing`
**Skills applied**: Dynamically resolved from `resolve-domain-skills --domain java --profile module_testing` (core + module_testing defaults and optionals)

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

---

## Step 1: Resolve Skills

Resolve the skills for the `module_testing` profile from the configured skill domains. This picks up whatever skills are currently configured — including project-level skills attached to the domain.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-domain-skills --domain java --profile module_testing
```

**Output (TOON)**:
```toon
status	success
domain	java
profile	module_testing
defaults	{"pm-dev-java:junit-core": "JUnit 5 core testing patterns with AAA structure and coverage standards"}
optionals	{"pm-dev-java:java-core": "Core Java patterns...", "pm-dev-java:java-maintenance": "Java code maintenance..."}
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

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, modules without test files).

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
  test_sources[1]:
    - src/test/java

key_packages[3]{name,description}:
de.cuioss.portal.auth,Authentication core logic
de.cuioss.portal.auth.impl,Authentication implementation
de.cuioss.portal.auth.model,Authentication data model

packages[3]{name,path,has_package_info,file_count}:
de.cuioss.portal.auth	my-core/src/main/java/de/cuioss/portal/auth	true	5
de.cuioss.portal.auth.impl	my-core/src/main/java/de/cuioss/portal/auth/impl	false	3
de.cuioss.portal.auth.model	my-core/src/main/java/de/cuioss/portal/auth/model	false	2

test_packages[3]{name,path,file_count}:
de.cuioss.portal.auth	my-core/src/test/java/de/cuioss/portal/auth	3
de.cuioss.portal.auth.impl	my-core/src/test/java/de/cuioss/portal/auth/impl	2
de.cuioss.portal.auth.model	my-core/src/test/java/de/cuioss/portal/auth/model	1

commands[3]:
  - module-tests
  - verify
  - quality-gate
```

The `key_packages` table contains the packages discovered during architecture analysis. The `packages` and `test_packages` tables (in `--full` mode) include `file_count` — the number of direct source files per package. The actual file lists are available in `derived-data.json` for programmatic access.

Build test package inventory from `test_packages` in the architecture data. Skip modules with empty `test_packages`.

---

## Step 4: Analysis

For each test package, run read-only verification analysis using the derived test path:

```
Task: pm-dev-java:java-verify-agent
  model: haiku
  Input:
    target: {test_sources_path}/{package_as_path}/
    module: {module_name}
    plan_id: {plan_id}
```

Where `{package_as_path}` is the package name with dots replaced by `/` (e.g., `de.cuioss.portal.auth` -> `de/cuioss/portal/auth`).

Record compliance findings per package:
- AAA pattern compliance
- @Nested grouping usage
- Assertion pattern quality (modern vs legacy)
- Coverage level (if available)
- Number of test files needing changes

Skip packages with full compliance (no deliverable needed).

---

## Step 5: Deliverable Creation

Create one deliverable per test package with compliance gaps > 0.

Each deliverable:
- **Title**: `Refactor tests: {module}/{package_name}`
- **Description**: Summary of test quality findings and what needs to change
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `java`
  - `module`: `{module_name}`
  - `profile`: `module_testing`
- **Skills**: All skills resolved in Step 1 (comma-separated)
- **Affected files**: All test files in the package (from architecture data `test_packages` `files` field)

Write each deliverable via manage-plan-documents:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  deliverable add \
  --plan-id {plan_id} \
  --title "Refactor tests: {module}/{package_name}" \
  --description "{compliance_summary}" \
  --change-type tech_debt \
  --domain java \
  --module {module} \
  --profile module_testing \
  --skills "{resolved_skills_csv}" \
  --files "{file_list}"
```

---

## Step 6: Outline Writing

Write `solution_outline.md` with all deliverables, grouped by module:

```markdown
# Solution Outline: Refactor to Test Standards

## Scope
{N} test packages across {M} modules requiring refactoring to comply with module_testing profile standards.

## Resolved Skills
{list of resolved skills from Step 1}

## Module: {module_name}

### Deliverable {n}: Refactor tests {module}/{package_name}
- **Test files**: {count}
- **Findings**: {summary}
- **Profile**: module_testing

...
```

---

## Task Execution

Each task uses the `module_testing` profile executor. The agent:
1. Loads the skills specified in the deliverable (resolved from module_testing profile)
2. Applies test refactoring patterns (based on loaded standards)
3. Verifies tests still pass after changes

---

## Related

- `plan-marshall:manage-plan-marshall-config resolve-domain-skills` — Dynamic skill resolution
- `plan-marshall:analyze-project-architecture architecture module` — Module/package query
- `pm-dev-java:java-verify-agent` — Read-only verification agent
