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

Allocate a new lesson file with metadata header and title (empty body). The call returns the absolute path of the created file; the caller then populates the body via `set-body` (canonical form, see below) — typically by writing a body file under `{plan_dir}/work/lesson-body-{id}.md` and passing it via `--file`.

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

### set-body

Populate (or replace) the body of an existing lesson. This is the **canonical** form for writing lesson bodies. Two mutually exclusive input modes are supported: `--file PATH` (preferred, shell-safe for arbitrary markdown) and `--content STRING` (secondary form, suitable only for tiny single-line payloads).

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id 2025-12-02-001 \
  --file /abs/path/to/.plan/local/plans/{plan_id}/work/lesson-body-2025-12-02-001.md
```

**Parameters**:
- `--lesson-id` (required): Lesson ID whose body to set
- `--file` (preferred): Absolute path to a markdown file containing the body. Use this for any non-trivial content — sections with `##` headings, code fences, multi-paragraph prose — because the body never passes through a shell argument.
- `--content` (secondary, tiny payloads only): Inline string body. Use only for single-line or very short content; any payload containing newlines, backticks, quotes, or shell metacharacters MUST use `--file` instead.

`--file` and `--content` are mutually exclusive — exactly one must be provided.

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
path: /abs/path/to/.plan/local/lessons-learned/2025-12-02-001.md
body_bytes_written: 1234
```

**Path-allocate flow (canonical)**:

The standard sequence for creating a lesson with a non-trivial body is:

1. `add` — allocate the lesson file and capture the returned `id`.
2. `Write {plan_dir}/work/lesson-body-{id}.md` — write the body markdown directly to a plan-scoped staging file using the Write tool. This bypasses shell quoting entirely and supports arbitrary markdown content.
3. `set-body --lesson-id {id} --file {path}` — apply the staged body to the lesson file. The script reads the file from disk and replaces the body section while preserving the metadata header and title.

Worked example:

```
# Step 1: allocate
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component maven-build --category bug \
  --title "Build fails with missing dependency"
# → returns id=2025-12-02-001

# Step 2: stage body via Write tool (no shell quoting concerns)
Write("/abs/path/to/.plan/local/plans/my-plan/work/lesson-body-2025-12-02-001.md", body_markdown)

# Step 3: apply
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id 2025-12-02-001 \
  --file /abs/path/to/.plan/local/plans/my-plan/work/lesson-body-2025-12-02-001.md
```

The inline `--content STRING` form is the secondary path — reserve it for tiny single-line payloads (e.g., a one-sentence note) where staging a file would be overhead. For anything multi-line, code-bearing, or containing shell-significant characters, always use the path-allocate flow above.

### update

Update lesson metadata.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --lesson-id 2025-12-02-001 \
  [--component new-component] \
  [--category bug|improvement|anti-pattern]
```

**Parameters**:
- `--lesson-id` (required): Lesson ID to update
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
  --lesson-id 2025-12-02-001
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
  --lesson-id 2025-12-02-001 \
  --plan-id my-plan
```

**Parameters**:
- `--lesson-id` (required): Lesson ID to move
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
| `add` | `--component --category --title [--bundle]` | Allocate a new lesson file and return its absolute `path`. Caller populates body via `set-body`. |
| `set-body` | `--lesson-id (--file PATH \| --content STRING)` | Populate or replace lesson body. `--file` is the canonical form (shell-safe for arbitrary markdown); `--content` is the secondary form for tiny single-line payloads only. |
| `update` | `--lesson-id [--component] [--category]` | Update lesson metadata |
| `get` | `--lesson-id` | Get single lesson |
| `list` | `[--component] [--category] [--full]` | List with filtering. `--full` includes lesson body content. |
| `from-error` | `--context` | Create from JSON error context (programmatic; body synthesized from context) |
| `convert-to-plan` | `--lesson-id --plan-id` | Move lesson into a plan directory as `lesson-{id}.md`. This is the move-semantics replacement for marking a lesson "applied". |

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
| `not_found` | Lesson ID doesn't exist (get, update, set-body, convert-to-plan) |
| `invalid_category` | Category not in: bug, improvement, anti-pattern |
| `invalid_context` | JSON context parsing failed (from-error) |
| `invalid_input` | `set-body` invoked without exactly one of `--file` / `--content`, or both supplied |
| `file_not_found` | `set-body --file PATH` points at a non-existent path or a non-regular file (directory, broken symlink, special file) |
| `file_read_error` | `set-body --file PATH` failed with an `OSError` while reading (permission denied, I/O error, etc.) |
| `malformed_lesson` | `set-body` target lesson file is missing its metadata header / title structure |
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
