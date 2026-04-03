---
name: manage-lessons
description: Manage lessons learned with global scope
user-invocable: false
scope: global
---

# Manage Lessons Skill

Manage lessons learned with global scope. Stores lessons as markdown files with key=value metadata headers.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid category values: `bug`, `improvement`, `anti-pattern`
- Lessons are global-scoped (not plan-specific); no `--plan-id` parameter
- The `from-error` command expects JSON context as `--context` argument

## Storage Location

Lessons are stored globally:

```
.plan/lessons-learned/
  2025-12-02-001.md
  2025-12-02-002.md
  ...
```

---

## File Format

Markdown with key=value metadata header:

```markdown
id=2025-12-02-001
component=maven-build
category=bug
applied=false
created=2025-12-02

# Build fails with missing dependency

When running `mvn clean install`, the build fails with a missing
dependency error for `jakarta.json-api`.

## Solution

Add the dependency explicitly to pom.xml:

```xml
<dependency>
    <groupId>jakarta.json</groupId>
    <artifactId>jakarta.json-api</artifactId>
</dependency>
```

## Impact

This affects all projects using jakarta.json without explicit dependency.
```

### Metadata Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (date-sequence) |
| `component` | Component that lesson applies to |
| `category` | bug, improvement, anti-pattern |
| `applied` | Whether lesson has been applied (true/false) |
| `created` | Creation date |
| `bundle` | Optional: bundle that the lesson relates to (e.g., `pm-dev-java`). Used for filtering when applying lessons to specific bundles. |

---

## Operations

Script: `plan-marshall:manage-lessons:manage-lessons`

### add

Create a new lesson.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component maven-build \
  --category bug \
  --title "Build fails with missing dependency" \
  --detail "When running mvn clean install..." \
  [--bundle planning]
```

**Parameters**:
- `--component` (required): Component that lesson applies to
- `--category` (required): `bug`, `improvement`, or `anti-pattern`
- `--title` (required): Lesson title
- `--detail` (required): Lesson detail/content
- `--bundle`: Optional bundle reference

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
file: 2025-12-02-001.md
component: maven-build
category: bug
```

### update

Update lesson metadata.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --id 2025-12-02-001 \
  [--applied true|false] \
  [--component new-component] \
  [--category bug|improvement|anti-pattern]
```

**Parameters**:
- `--id` (required): Lesson ID to update
- `--applied`: Set applied status (true/false)
- `--component`: Update component name
- `--category`: Update category

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
field: applied
value: true
previous: false
```

### get

Get a single lesson.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get \
  --id 2025-12-02-001
```

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
component: maven-build
category: bug
applied: false
created: 2025-12-02
title: Build fails with missing dependency

content: |
  When running `mvn clean install`...
```

### list

List lessons with filtering.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list \
  [--component maven-build] \
  [--category bug] \
  [--applied true|false]
```

**Parameters**:
- `--component`: Filter by component name
- `--category`: Filter by category (`bug`, `improvement`, `anti-pattern`)
- `--applied`: Filter by applied status (true/false)

**Output** (TOON):
```toon
status: success
total: 5
filtered: 2
lessons:
  - id: 2025-12-02-001
    component: maven-build
    category: bug
    applied: false
    title: Build fails with missing dependency
  - id: 2025-12-02-002
    component: plan-files
    category: improvement
    applied: true
    title: Add validation for plan_id format
```

### from-error

Create lesson from error context (JSON).

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons from-error \
  --context '{"component":"maven-build","error":"Missing dependency","solution":"Add explicit dep"}'
```

**Parameters**:
- `--context` (required): JSON object with error context
  - `component`: Component name (defaults to "unknown")
  - `error`: Error message (required)
  - `solution`: Optional solution description

**Output** (TOON):
```toon
status: success
id: 2025-12-02-003
created_from: error_context
```

---

## Scripts

**Script**: `plan-marshall:manage-lessons:manage-lessons`

| Command | Parameters | Description |
|---------|------------|-------------|
| `add` | `--component --category --title --detail [--bundle]` | Create new lesson |
| `update` | `--id [--applied] [--component] [--category]` | Update lesson metadata |
| `get` | `--id` | Get single lesson |
| `list` | `[--component] [--category] [--applied]` | List with filtering |
| `from-error` | `--context` | Create from JSON error context |
| `archive` | `--id` | Mark lesson as applied and move to archived directory. Equivalent to `update --applied true` plus file relocation. |

---

## Categories

| Category | When to Use |
|----------|-------------|
| `bug` | Script is broken or produces wrong results |
| `improvement` | Script works but could be better |
| `anti-pattern` | Script was misused or documentation unclear |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `not_found` | Lesson ID doesn't exist (get, update, archive) |
| `invalid_category` | Category not in: bug, improvement, anti-pattern |
| `invalid_context` | JSON context parsing failed (from-error) |
| `missing_required` | Required parameter missing |

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-5-execute` | add, from-error | Document errors and solutions during execution |
| `phase-6-finalize` | add | Promote findings to lessons |
| `plugin-doctor` | add | Capture recurring component issues |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plugin-apply-lessons-learned` | list, update | Apply lessons to marketplace components |
| `phase-6-finalize` | list | Query unapplied lessons for promotion |

## Related Skills

- `manage-findings` — Findings promoted to lessons at 6-finalize
- `manage-memories` — Complementary global persistence (session context)
- `manage-run-config` — Complementary global persistence (execution state)
