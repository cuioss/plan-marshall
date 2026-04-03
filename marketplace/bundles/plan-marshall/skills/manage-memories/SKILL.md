---
name: manage-memories
description: Memory layer operations for persistent session storage
user-invocable: false
scope: global
---

# Manage Memories Skill

Memory layer operations for persistent session storage (via `tools-file-ops` skill).

**Scope: global** means memory files persist across plans in `.plan/memories/`. They are not tied to any specific plan_id. Cleanup is governed by `system.retention.memory_days` in marshal.json.

> **Not to be confused with** Claude Code's built-in auto-memory system (`~/.claude/projects/*/memory/`). This skill manages structured session context in `.plan/memories/` for plan-marshall workflows. The two memory systems are independent.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not bypass the metadata envelope format for memory files
- Memory files are global-scoped (stored in `.plan/memories/`)
- Content for save operations must be valid JSON

## Memory Categories

| Category | Purpose | Typical Lifetime |
|----------|---------|------------------|
| `context` | Session context snapshots | Short (days, controlled by `system.retention.memory_days` in marshal.json) |

---

## Workflow: Memory Operations

**Pattern**: Command Chain Execution

Manage the memory layer for session persistence (via `tools-file-ops` skill).

### Parameters

- **command** (required): One of `save`, `load`, `list`, `query`, `cleanup`, `validate`
- **category** (optional): Currently `context` (session snapshots)
- **identifier** (optional): File identifier or summary name
- **content** (optional): JSON content for save operations

### Step 1: Execute Operation

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory {operation} [--category {category}] [--identifier {identifier}] [--content '{content}']
```

### Step 2: Process Result

Parse TOON output and handle accordingly.

### Operations Reference

#### save

Save a memory file (creates directories on-the-fly).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--category` | Yes | Category: `context` |
| `--identifier` | Yes | Human-readable name (date prefix auto-added for context) |
| `--content` | Yes | JSON content string |

#### load

Load a memory file by category and identifier.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--category` | Yes | Category: `context` |
| `--identifier` | Yes | Full filename without extension (including date prefix, e.g., `2025-12-02-feature-auth`) |

#### list

List files in a category.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--category` | No | Category to list (omit for all categories) |
| `--since` | No | Time filter (e.g., `7d` for last 7 days) |

#### query

Find files matching a glob pattern.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pattern` | Yes | Glob pattern (e.g., `auth*`) |
| `--category` | No | Limit search to category |

#### cleanup

Remove old files by age.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--category` | No | Category to clean (omit for all) |
| `--older-than` | Yes | Age threshold (e.g., `7d`, `30d`) |

#### validate

Validate memory file format and structure.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `file_path` | Yes | Positional: path to memory file |

### Example Usage

```bash
# Save context snapshot (directories created on-the-fly)
# File will be stored as: .plan/memories/context/YYYY-MM-DD-feature-auth.json
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory save --category context --identifier "feature-auth" --content '{"notes": "Working on auth feature"}'

# Load memory file (use the full filename including date prefix)
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
| category | string | One of: `context` |
| summary | string | Human-readable identifier |
| session_id | string | (Optional) Claude session ID for provenance tracking |

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

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plan-marshall:plan-marshall` orchestrator | save | Persist session context snapshots at phase boundaries |
| Phase agents (any) | save | Store intermediate working state |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plan-marshall:plan-marshall` orchestrator | load, query | Restore context from prior sessions |
| `manage-run-config` cleanup | cleanup | Remove stale memory files based on `system.retention.memory_days` |

### Data Flow

Memory files are created during plan execution to persist session context. The `manage-run-config` cleanup process uses `system.retention.memory_days` from marshal.json to determine when to purge old memory files.

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_category` | Category not in valid set (currently only `context`) |
| `file_not_found` | Memory file doesn't exist (load) |
| `invalid_content` | Content is not valid JSON (save) |
| `validation_failed` | Memory file missing required meta fields or invalid JSON structure |

## References

- `standards/memory-layer-format.md` - Complete memory file format documentation

## Related Skills

- `manage-lessons` — Global lessons learned (complementary persistence)
- `manage-run-config` — Runtime configuration (complementary persistence)
