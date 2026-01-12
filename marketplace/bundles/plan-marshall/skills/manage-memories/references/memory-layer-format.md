# Memory Layer Format

File format specifications for memory layer session persistence (via `file-operations-base` skill).

## Directory Structure

```
{memory-storage}/
└── context/         # Session context snapshots
```

## Memory File Envelope

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
| category | string | Currently: context |
| summary | string | Human-readable identifier |

### Optional Meta Fields

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Claude Code session identifier |

---

## Categories

### context

Session context snapshots. Short-lived, typically cleaned up after days.

**File naming**: `{date}-{summary}.json`

**Example**: `2025-11-25-feature-auth.json`

**Content structure**:
```json
{
  "meta": { ... },
  "content": {
    "pending": ["Implement token refresh"],
    "notes": "Working on authentication feature"
  }
}
```

---

## Operations

### Save

Creates or updates a memory file. Directories are created on-the-fly.

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory save \
  --category context \
  --identifier "feature-auth" \
  --content '{"decisions": ["Use JWT"]}'
```

For `context` category, date prefix is auto-added.

### Load

Retrieves memory file content.

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory load \
  --category context \
  --identifier "task-42"
```

### List

Lists files in category.

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory list \
  --category context \
  --since 7d
```

### Query

Finds files by pattern.

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory query \
  --pattern "auth*" \
  --category context
```

### Cleanup

Removes old files.

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory cleanup \
  --category context \
  --older-than 7d
```

---

## Lifecycle Recommendations

| Category | Typical Lifetime | Cleanup Strategy |
|----------|-----------------|------------------|
| context | Days | Auto-cleanup after 7d |
