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

This returns the aggregated skills: core defaults + core optionals + implementation defaults + implementation optionals (plus project_skills if attached).

Store the resolved `defaults` and `optionals` skill lists for use in Step 4. Build the comma-separated `--skills` argument from all resolved skill names.

---

## Step 2: Scope Selection

Use module mapping from refine phase. If empty, discover all modules:

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
  discover-modules
```

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, test-only modules).

---

## Step 3: Discovery

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

## Step 4: Analysis

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

## Step 5: Deliverable Creation

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
- **Skills**: All skills resolved in Step 1 (comma-separated)
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

### Deliverable {n}: Refactor {module}/{package}
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
- `pm-dev-java:java-quality-agent` — Read-only quality analysis agent
- `pm-dev-java:java-refactor-agent` — Refactoring execution agent
