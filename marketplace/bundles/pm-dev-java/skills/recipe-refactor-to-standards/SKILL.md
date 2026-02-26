---
name: recipe-refactor-to-standards
description: Recipe skill for refactoring production code to comply with java-core and java-maintenance standards, package by package
user-invokable: false
---

# Recipe: Refactor to Implementation Standards

Predefined recipe skill for refactoring production code to comply with applicable implementation skill standards. Iterates module-by-module, package-by-package.

**Profile**: `implementation`
**Skills applied**: `pm-dev-java:java-core` (core defaults), `pm-dev-java:java-maintenance` (implementation optionals)

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

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, test-only modules).

---

## Step 2: Discovery

For each selected module, scan `src/main/java/` for packages containing `.java` files.

Build package inventory:

```
Module: my-module
  de.cuioss.portal.auth       - 5 files
  de.cuioss.portal.auth.impl  - 3 files
  de.cuioss.portal.auth.model - 7 files
```

Skip packages with 0 `.java` files. Record file counts per package.

---

## Step 3: Analysis

For each package, run read-only quality analysis:

```
Task: pm-dev-java:java-quality-agent
  model: haiku
  Input:
    target: src/main/java/{package_path}/
    module: {module_name}
    plan_id: {plan_id}
```

Record compliance findings per package:
- Current compliance level (percentage)
- Specific violations found (patterns, modern features, method design, performance)
- Number of files needing changes

Skip packages with 100% compliance (no deliverable needed).

---

## Step 4: Deliverable Creation

Create one deliverable per package with compliance gaps > 0.

Each deliverable:
- **Title**: `Refactor: {module}/{package.path}`
- **Description**: Summary of quality findings and what needs to change
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `java`
  - `module`: `{module_name}`
  - `profile`: `implementation`
- **Skills**: `pm-dev-java:java-core`, `pm-dev-java:java-maintenance`
- **Affected files**: All `.java` files in the package

Write each deliverable via manage-plan-documents:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  deliverable add \
  --plan-id {plan_id} \
  --title "Refactor: {module}/{package}" \
  --description "{compliance_summary}" \
  --change-type tech_debt \
  --domain java \
  --module {module} \
  --profile implementation \
  --skills "pm-dev-java:java-core,pm-dev-java:java-maintenance" \
  --files "{file_list}"
```

---

## Step 5: Outline Writing

Write `solution_outline.md` with all deliverables, grouped by module:

```markdown
# Solution Outline: Refactor to Implementation Standards

## Scope
{N} packages across {M} modules requiring refactoring to comply with java-core and java-maintenance standards.

## Module: {module_name}

### Deliverable {n}: Refactor {module}/{package}
- **Files**: {count} Java files
- **Findings**: {summary}
- **Profile**: implementation
- **Skills**: java-core, java-maintenance

...
```

---

## Task Execution

Each task uses `java-refactor-agent` (Sonnet) with the package scope. The agent:
1. Loads java-core and java-maintenance skills
2. Applies refactoring rules to all files in the package
3. Verifies build passes after changes

---

## Related

- `pm-dev-java:java-core` — Core Java development standards
- `pm-dev-java:java-maintenance` — Java code maintenance standards
- `pm-dev-java:java-quality-agent` — Read-only quality analysis agent
- `pm-dev-java:java-refactor-agent` — Refactoring execution agent
