---
name: recipe-refactor-to-test-standards
description: Recipe skill for refactoring test code to comply with junit-core standards, test-package by test-package
user-invokable: false
---

# Recipe: Refactor to Test Standards

Predefined recipe skill for refactoring test code to comply with JUnit 5 standards. Iterates module-by-module, test-package-by-test-package.

**Profile**: `module_testing`
**Skills applied**: `pm-dev-java:java-core` (core defaults), `pm-dev-java:junit-core` (module_testing defaults)

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

---

## Step 1: Scope Selection

Use module mapping from refine phase. If empty, discover all modules:

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
  discover-modules
```

Present module list to user for confirmation/filtering. User may exclude modules without test sources.

---

## Step 2: Discovery

For each selected module, scan `src/test/java/` for test packages containing `*Test.java` files.

Build test package inventory:

```
Module: my-module
  de.cuioss.portal.auth       - 3 test files
  de.cuioss.portal.auth.impl  - 5 test files
  de.cuioss.portal.auth.model - 2 test files
```

Skip packages with 0 test files. Record test file counts per package.

---

## Step 3: Analysis

For each test package, run read-only verification analysis:

```
Task: pm-dev-java:java-verify-agent
  model: haiku
  Input:
    target: src/test/java/{package_path}/
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

## Step 4: Deliverable Creation

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
- **Skills**: `pm-dev-java:java-core`, `pm-dev-java:junit-core`
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
  --skills "pm-dev-java:java-core,pm-dev-java:junit-core" \
  --files "{file_list}"
```

---

## Step 5: Outline Writing

Write `solution_outline.md` with all deliverables, grouped by module:

```markdown
# Solution Outline: Refactor to Test Standards

## Scope
{N} test packages across {M} modules requiring refactoring to comply with junit-core standards.

## Module: {module_name}

### Deliverable {n}: Refactor tests {module}/{package}
- **Test files**: {count}
- **Findings**: {summary}
- **Profile**: module_testing
- **Skills**: java-core, junit-core

...
```

---

## Task Execution

Each task uses the `module_testing` profile executor. The agent:
1. Loads java-core and junit-core skills
2. Applies test refactoring patterns (AAA, @Nested, modern assertions)
3. Verifies tests still pass after changes

---

## Related

- `pm-dev-java:java-core` — Core Java development standards
- `pm-dev-java:junit-core` — JUnit 5 core testing patterns
- `pm-dev-java:java-verify-agent` — Read-only verification agent
