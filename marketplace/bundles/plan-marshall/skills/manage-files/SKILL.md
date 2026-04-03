---
name: manage-files
description: Generic file I/O operations for plan directories
user-invocable: false
scope: plan
---

# Manage Files Skill

Generic file operations for plan directories. Provides basic CRUD operations for any file within a plan directory.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not pass absolute paths or `..` traversals in `--file` arguments
- File paths are always relative to the plan directory
- plan_id must be kebab-case format

## Storage Location

Files are stored in plan directories:

```
.plan/plans/{plan_id}/
```

For domain-specific files within the plan directory, use the dedicated manage-* skills (see Relationship to Domain Skills below).

---

## Operations

Script: `plan-marshall:manage-files:manage-files`

### read

Read file content from a plan directory.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file notes.md
```

**Output**: Raw file content (no wrapping)

### write

Write content to a file in a plan directory.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id {plan_id} \
  --file request.md \
  --content "# Request Title

Task description with multiline content.

## Section

More content here..."
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--file` (required): Relative file path within plan directory
- `--content`: Content to write (mutually exclusive with `--stdin`)
- `--stdin`: Read content from stdin instead of `--content`

**Note**: The `--content` parameter supports multiline content. Do NOT use `--stdin` with shell heredocs or cat commands — the executor handles content passing; stdin is only for piped input from other scripts.

**Content requirement**: Content must be non-empty. Empty content produces an error (`missing_content`).

**Output**: TOON with `status: success`, `action: created`/`updated`. Exit code 0 on success, 1 on error.

**Side effect**: Successful writes are logged via `log_entry()` to the plan's work log.

### remove

Remove a file from a plan directory.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files remove \
  --plan-id {plan_id} \
  --file old-file.md
```

**Output**: Confirmation message to stderr, exit code 0 on success

### list

List files in a plan directory.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files list \
  --plan-id {plan_id} \
  [--dir subdir]
```

**Output** (TOON format): File listing with `status: success` and `files` array

### exists

Check if a file exists. Returns TOON output with `exists: true/false`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} \
  --file references.json
```

**Output** (TOON format):

When file exists:
```toon
status: success
plan_id: my-feature
file: references.json
exists: true
path: .plan/plans/my-feature/references.json
```

When file does not exist:
```toon
status: success
plan_id: my-feature
file: missing.md
exists: false
path: .plan/plans/my-feature/missing.md
```

On validation error (invalid plan_id or path):
```toon
status: error
plan_id: Invalid_Plan
error: invalid_plan_id
message: Invalid plan_id format: Invalid_Plan
```

**Note**: Always exits 0 for both exists=true and exists=false (both are valid query results). Only exits 1 for actual errors (invalid plan_id, invalid path). Check `status` and `exists` fields to determine result.

### mkdir

Create a subdirectory in a plan directory.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files mkdir \
  --plan-id {plan_id} \
  --dir requirements
```

**Output** (TOON format):

```toon
status: success
plan_id: my-feature
action: created
dir: requirements
path: /path/to/.plan/plans/my-feature/requirements
```

The `action` field is `created` if the directory was newly created, or `exists` if it already existed.

### create-or-reference

Create a plan directory if it doesn't exist, or reference an existing one. This is an atomic operation that replaces the two-step pattern of listing plans and checking for conflicts.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files create-or-reference \
  --plan-id {plan_id}
```

**Output** (TOON format):

When plan is newly created:
```toon
status: success
plan_id: my-feature
action: created
path: /path/to/.plan/plans/my-feature
```

When plan already exists:
```toon
status: success
plan_id: my-feature
action: exists
path: /path/to/.plan/plans/my-feature
current_phase: refine
domain: java
```

**Use case**: Called by plan-init to atomically check/create plan directories.

---

## Key Design Principles

1. **plan_id only** - Never pass full paths, script resolves base via `base_path()`
2. **Relative file paths** - `--file` accepts relative paths within plan dir (e.g., `requirements/REQ-001.toon`)
3. **Generic file operations** - Not domain-specific (no parse-plan, write-config)
4. **Plain output** - `read` returns raw content; mutations return minimal status
5. **Minimal validation** - Rejects empty content on write; no structural validation of content

---

## Validation Rules

| Check | Validation |
|-------|------------|
| plan_id format | kebab-case, no special chars |
| file path | No `..`, no absolute paths, no leading `/` |
| directory | Must exist (unless mkdir) |
| content | Non-empty for write |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id contains invalid characters (must be kebab-case) |
| `file_not_found` | File does not exist (read, remove) |
| `missing_content` | Write called with empty or missing content |
| `invalid_path` | Path contains `..` or absolute path components |
| `permission_error` | File system permission denied |

---

## Integration

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | create-or-reference, write | Create plan directory and initial files |
| `phase-3-outline` | write, read | Generic file I/O for plan artifacts |
| `phase-5-execute` | read, write, list | File operations during task execution |

### Relationship to Domain Skills

| Skill | Manages | Use manage-files for |
|-------|---------|---------------------|
| manage-references | references.json | N/A (use manage-references) |
| manage-status | status.json | N/A (use manage-status) |
| manage-plan-documents | request.md | N/A (use manage-plan-documents) |
| manage-solution-outline | solution_outline.md | N/A (use manage-solution-outline) |
| manage-tasks | tasks/*.toon | N/A (use manage-tasks) |
| manage-files | any other file | Generic read/write/list |

## Related Skills

- `manage-plan-documents` — Typed plan document operations (request.md)
- `manage-references` — Reference tracking for plans (references.json)
- `manage-logging` — Logging operations that complement file I/O
