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

This returns the aggregated skills: core defaults + core optionals + module_testing defaults + module_testing optionals (plus project_skills if attached).

Store the resolved `defaults` and `optionals` skill lists for use in Step 4. Build the comma-separated `--skills` argument from all resolved skill names.

---

## Step 2: Load Architecture Data

Packages are already discovered and stored during architecture analysis. Load them from `derived-data.json`:

```bash
# Read the architecture data
Read .plan/project-architecture/derived-data.json
```

The `modules` object contains each module with its `packages` field and `stats.test_files` count. Test packages mirror the main package structure under `src/test/java/`.

---

## Step 3: Scope Selection

Present module list to user for confirmation/filtering. Skip modules with 0 test files (`stats.test_files == 0`).

For each selected module, derive test packages from the architecture `packages` data — the test directory mirrors the main source package structure. For each package `de.cuioss.portal.auth` with path `src/main/java/de/cuioss/portal/auth`, the corresponding test path is `src/test/java/de/cuioss/portal/auth`.

Only include packages where the test path actually contains `*Test.java` files.

Build test package inventory:

```
Module: my-module (10 test files)
  de.cuioss.portal.auth       - src/test/java/de/cuioss/portal/auth
  de.cuioss.portal.auth.impl  - src/test/java/de/cuioss/portal/auth/impl
```

Skip packages with no test files in the corresponding test directory.

---

## Step 4: Analysis

For each test package, run read-only verification analysis using the derived test path:

```
Task: pm-dev-java:java-verify-agent
  model: haiku
  Input:
    target: {test_package_path}/
    module: {module_name}
    plan_id: {plan_id}
```

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
- **Title**: `Refactor tests: {module}/{package.path}`
- **Description**: Summary of test quality findings and what needs to change
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `java`
  - `module`: `{module_name}`
  - `profile`: `module_testing`
- **Skills**: All skills resolved in Step 1 (comma-separated)
- **Affected files**: All `*Test.java` files in the package

Write each deliverable via manage-plan-documents:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  deliverable add \
  --plan-id {plan_id} \
  --title "Refactor tests: {module}/{package}" \
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

### Deliverable {n}: Refactor tests {module}/{package}
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
- `pm-dev-java:java-verify-agent` — Read-only verification agent
