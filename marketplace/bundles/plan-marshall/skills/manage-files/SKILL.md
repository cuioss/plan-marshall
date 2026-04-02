---
name: manage-files
description: Generic file I/O operations for plan directories
user-invocable: false
scope: plan
---

# Manage Files Skill

Generic file operations for plan directories. Provides basic CRUD operations for any file within a plan directory.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse output for status and route accordingly.

**Prohibited actions:**
- Do not modify .plan/ files directly; all mutations go through the script API
- Do not invent script arguments not listed in the Operations section
- Do not pass absolute paths or `..` traversals in `--file` arguments

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-files:manage-files {command} {args}`
- File paths are always relative to the plan directory
- plan_id must be kebab-case format

## What This Skill Provides

- Generic file read/write/remove operations
- Directory listing and creation
- File existence checking
- Plan directory create-or-reference (atomic check/create)
- Minimal content validation (rejects empty content on write; no structural validation)

## When to Activate This Skill

Activate this skill when:
- Reading or writing arbitrary files in a plan directory
- Creating subdirectories within a plan
- Listing plan contents
- Checking if files exist

**Note**: For typed plan documents (`request.md`, `solution_outline.md`), use `plan-marshall:manage-plan-documents` instead. For domain-specific files (references.json, status.toon), use the dedicated manage-* skills.

---

## Storage Location

Files are stored in plan directories:

```
.plan/plans/{plan_id}/
  request.md
  solution_outline.md
  references.json
  status.toon
  tasks/
```

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

### delete-plan

Delete an entire plan directory. Used when user selects "Replace" for an existing plan during plan-init.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files delete-plan \
  --plan-id {plan_id}
```

**Output** (TOON format):

On success:
```toon
status: success
plan_id: my-feature
action: deleted
path: /path/to/.plan/plans/my-feature
files_removed: 5
```

On error (plan not found):
```toon
status: error
plan_id: my-feature
error: plan_not_found
message: Plan directory does not exist: /path/to/.plan/plans/my-feature
```

**Use case**: Called by plan-init when user selects "Replace" to delete existing plan before creating new one. See `plan-marshall:phase-1-init/standards/plan-overwrite.md` for the full workflow.

**Warning**: This recursively deletes the entire plan directory including all subdirectories (logs, tasks, work artifacts). There is no undo.

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

All errors return TOON with `status: error` and exit code 1 (except `exists` which always exits 0).

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id contains invalid characters (must be kebab-case) |
| `file_not_found` | File does not exist (read, remove) |
| `plan_not_found` | Plan directory does not exist (delete-plan) |
| `missing_content` | Write called with empty or missing content |
| `invalid_path` | Path contains `..` or absolute path components |
| `permission_error` | File system permission denied |

```toon
status: error
plan_id: my-plan
error: file_not_found
message: File does not exist: config.json
```

---

## Integration Points

### With Domain Skills

Domain-specific skills (manage-references, manage-lifecycle) may use this skill for basic file operations, or import shared libraries directly.

### With Orchestration Skills

Plan orchestration skills (plan-init, solution-outline, task-plan, plan-execute) use this skill for generic file I/O.

---

## Relationship to Domain Skills

| Skill | Manages | Use manage-files for |
|-------|---------|---------------------|
| manage-references | references.json | N/A (use manage-references) |
| manage-lifecycle | status.toon | N/A (use manage-lifecycle) |
| manage-plan-documents | request.md | N/A (use manage-plan-documents) |
| manage-solution-outline | solution_outline.md | N/A (use manage-solution-outline) |
| manage-tasks | tasks/*.toon | N/A (use manage-tasks) |
| manage-files | any other file | Generic read/write/list |

## Related Skills

- `manage-plan-documents` — Typed plan document operations (request.md, solution_outline.md)
- `manage-references` — Reference tracking for plans (references.json)
