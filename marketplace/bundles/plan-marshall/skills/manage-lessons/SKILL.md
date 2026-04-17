---
name: manage-lessons
description: Manage lessons learned with global scope
user-invocable: false
scope: global
---

# Manage Lessons Skill

Manage lessons learned with global scope. Stores lessons as markdown files with key=value metadata headers. A lesson's lifecycle state ("unapplied" vs "applied") is encoded by its on-disk location, not by metadata: unapplied lessons live in `.plan/local/lessons-learned/{id}.md`, and become applied by being moved into a plan directory as `.plan/local/plans/{plan_id}/lesson-{id}.md` via `convert-to-plan`.

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
created=2025-12-02

# Build fails with missing dependency

When running a Maven clean install, the build fails with a missing
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
| `created` | Creation date |
| `bundle` | Optional: bundle that the lesson relates to (e.g., `pm-dev-java`). Used for filtering when applying lessons to specific bundles. |

---

## Operations

Script: `plan-marshall:manage-lessons:manage-lessons`

### add

Allocate a new lesson file with metadata header and title (empty body). The call returns the absolute path of the created file; the caller then writes the body directly to that path via the Write tool. There is **no** inline-body API form — this is the single, canonical flow.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component maven-build \
  --category bug \
  --title "Build fails with missing dependency" \
  [--bundle planning]
```

**Parameters**:
- `--component` (required): Component that lesson applies to
- `--category` (required): `bug`, `improvement`, or `anti-pattern`
- `--title` (required): Lesson title
- `--bundle`: Optional bundle reference

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
path: /abs/path/to/.plan/local/lessons-learned/2025-12-02-001.md
component: maven-build
category: bug
```

**Write the body**:

After the call returns, use the Write tool with the returned `path` value to populate the lesson body. The file already contains the metadata header and the `# {title}` heading; append body content below the title.

```
Write(path, body_markdown)
```

Body content may include arbitrary markdown, including sections with `##` headings, code fences, and multiple paragraphs — all written directly through the Write tool, bypassing shell argument quoting entirely.

### update

Update lesson metadata.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --id 2025-12-02-001 \
  [--component new-component] \
  [--category bug|improvement|anti-pattern]
```

**Parameters**:
- `--id` (required): Lesson ID to update
- `--component`: Update component name
- `--category`: Update category

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
field: component
value: new-component
previous: maven-build
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
created: 2025-12-02
title: Build fails with missing dependency

content: |
  When running a Maven clean install...
```

### list

List lessons with filtering.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list \
  [--component maven-build] \
  [--category bug]
```

**Parameters**:
- `--component`: Filter by component name
- `--category`: Filter by category (`bug`, `improvement`, `anti-pattern`)

**Output** (TOON):
```toon
status: success
total: 5
filtered: 2
lessons:
  - id: 2025-12-02-001
    component: maven-build
    category: bug
    title: Build fails with missing dependency
  - id: 2025-12-02-002
    component: plan-files
    category: improvement
    title: Add validation for plan_id format
```

### convert-to-plan

Move a lesson out of the global lessons-learned directory and into a plan directory as `lesson-{id}.md`. This is how a lesson transitions from "unapplied" to "applied" — the lifecycle state is encoded in the file's location, not in metadata.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons convert-to-plan \
  --id 2025-12-02-001 \
  --plan-id my-plan
```

**Parameters**:
- `--id` (required): Lesson ID to move
- `--plan-id` (required): Target plan directory under `.plan/local/plans/`

**Output** (TOON):
```toon
status: success
lesson_id: 2025-12-02-001
plan_id: my-plan
source: .plan/local/lessons-learned/2025-12-02-001.md
destination: .plan/local/plans/my-plan/lesson-2025-12-02-001.md
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
| `add` | `--component --category --title [--bundle]` | Allocate a new lesson file and return its absolute `path`. Caller writes body via Write tool. |
| `update` | `--id [--component] [--category]` | Update lesson metadata |
| `get` | `--id` | Get single lesson |
| `list` | `[--component] [--category] [--full]` | List with filtering. `--full` includes lesson body content. |
| `from-error` | `--context` | Create from JSON error context (programmatic; body synthesized from context) |
| `convert-to-plan` | `--id --plan-id` | Move lesson into a plan directory as `lesson-{id}.md`. This is the move-semantics replacement for marking a lesson "applied". |

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
| `not_found` | Lesson ID doesn't exist (get, update, convert-to-plan) |
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
| `plugin-apply-lessons-learned` | list, convert-to-plan | Apply lessons to marketplace components by moving them into a plan directory |
| `phase-6-finalize` | list | Query unapplied lessons (those still in `.plan/local/lessons-learned/`) for promotion |

## Related

- `manage-findings` — Findings promoted to lessons at 6-finalize
- `manage-memories` — Complementary global persistence (session context)
- `manage-run-config` — Complementary global persistence (execution state)
