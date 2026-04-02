---
name: manage-memories
description: Memory layer operations for persistent session storage
user-invocable: false
scope: global
---

# Claude Memory Skill

Memory layer operations for persistent session storage (via `file-operations-base` skill).

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify memory files directly; all mutations go through the script API
- Do not invent script arguments not listed in the Operations Reference
- Do not bypass the metadata envelope format for memory files

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory {command} {args}`
- Memory files are global-scoped (stored in `.plan/memories/`)
- Content for save operations must be valid JSON

## What This Skill Provides

- CRUD operations for memory storage files
- Category-based organization
- Timestamp-based file naming for context files
- Age-based cleanup
- Memory file format validation

## When to Activate This Skill

Activate this skill when:
- Persisting session context
- Cleaning up old memory files

---

## Memory Categories

| Category | Purpose | Typical Lifetime |
|----------|---------|------------------|
| `context` | Session context snapshots | Short (days) |

---

## Workflow: Memory Operations

**Pattern**: Command Chain Execution

Manage the memory layer for session persistence (via `file-operations-base` skill).

### Parameters

- **operation** (required): One of `save`, `load`, `list`, `query`, `cleanup`
- **category** (optional): One of `context`
- **identifier** (optional): File identifier or summary name
- **content** (optional): JSON content for save operations

### Step 1: Execute Operation

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:{operation} [--category {category}] [--identifier {identifier}] [--content '{content}']
```

### Step 2: Process Result

Parse TOON output and handle accordingly.

### Operations Reference

| Operation | Description | Required Params |
|-----------|-------------|-----------------|
| `save` | Save memory file (creates directories on-the-fly) | category, identifier, content |
| `load` | Load memory file | category, identifier |
| `list` | List files in category | category (optional) |
| `query` | Find files by pattern | pattern |
| `cleanup` | Remove old files | --older-than |

### Example Usage

```bash
# Save context snapshot (directories created on-the-fly)
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory save --category context --identifier "feature-auth" --content '{"notes": "Working on auth feature"}'

# Load memory file
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory load --category context --identifier "2025-12-02-feature-auth"

# List context files from last 7 days
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory list --category context --since 7d

# Find files matching pattern
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory query --pattern "auth*" --category context

# Cleanup old context files
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory cleanup --category context --older-than 7d
```

---

## Workflow: Validate Memory File

**Pattern**: Command Chain Execution

Validate memory file format and structure.

### Parameters

- **file_path** (required): Path to memory file

### Step 1: Execute Validation

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory validate {file_path}
```

### Step 2: Process Result

```
status: success
success: true
valid: true
file: /path/to/file.json
format: memory
checks[2]{check,passed}:
  json_syntax,true
  required_fields,true
```

---

## Memory File Format

All memory files use a metadata envelope:

```json
{
  "meta": {
    "created": "2025-11-25T10:30:00Z",
    "category": "context",
    "summary": "feature-auth",
    "session_id": "optional-session-id"
  },
  "content": {
    // Category-specific content
  }
}
```

### Required Meta Fields

| Field | Type | Description |
|-------|------|-------------|
| created | string | ISO 8601 timestamp with Z suffix |
| category | string | One of: context |
| summary | string | Human-readable identifier |

---

## Scripts

| Script | Notation |
|--------|----------|
| manage-memory | `plan-marshall:manage-memories` |
| validate-memory | `plan-marshall:manage-memories` |

All scripts:
- Use Python stdlib only (json, argparse, pathlib, datetime) plus toon_parser
- Output TOON to stdout
- Exit code 0 for success, 1 for errors
- Support `--help` flag

---

## Integration Points

### With Scripts Library
- Memory scripts are discovered via scripts-library.toon
- Use portable notation from Scripts table above

### With planning Bundle
- Memory operations enable task state persistence
- Cleanup operations maintain memory hygiene

---

## References

- `references/memory-layer-format.md` - Complete memory file format documentation

## Related Skills

- `manage-lessons` — Global lessons learned (complementary persistence)
- `manage-run-config` — Runtime configuration (complementary persistence)
