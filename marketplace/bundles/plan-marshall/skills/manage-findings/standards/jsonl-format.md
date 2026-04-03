# Findings JSONL Format

Storage format specifications for plan-level findings and phase-scoped Q-Gate findings.

## Storage Files

| File | Scope | Purpose |
|------|-------|---------|
| `findings.jsonl` | Plan | Long-lived findings, promotable to lessons or architecture |
| `qgate-{phase}.jsonl` | Phase | Per-phase verification findings, not promotable |

Both files live in `.plan/plans/{plan_id}/artifacts/`.

## Plan Finding Record

Each line in `findings.jsonl` is a JSON object:

```json
{
  "hash_id": "a3f2c1",
  "timestamp": "2026-03-27T10:00:00Z",
  "type": "bug",
  "title": "Null check missing in validation",
  "detail": "The validate() method does not check for null input",
  "severity": "warning",
  "resolution": "pending",
  "file_path": "src/main/java/Validator.java",
  "line": 42,
  "component": "jwt-validator",
  "module": "cui-jwt",
  "rule": "NP_NULL_ON_SOME_PATH",
  "promoted": false,
  "promoted_to": null
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `hash_id` | string | 6-character hex hash (auto-generated from title + type) |
| `timestamp` | string | ISO 8601 UTC (auto-generated on add) |
| `type` | string | One of: `bug`, `improvement`, `anti-pattern`, `triage`, `tip`, `insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment`. The first three (`bug`, `improvement`, `anti-pattern`) map to lesson categories — see `manage-lessons/standards/file-format.md` |
| `title` | string | Short description of the finding |
| `detail` | string | Full description with context |
| `severity` | string | `error`, `warning`, or `info` (default: `warning`) |
| `resolution` | string | `pending`, `fixed`, `suppressed`, `accepted`, or `taken_into_account` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path to affected file |
| `line` | int | Line number in affected file |
| `component` | string | Component identifier |
| `module` | string | Module name |
| `rule` | string | Rule identifier (e.g., linter rule, Sonar rule) |

### Promotion Fields

| Field | Type | Description |
|-------|------|-------------|
| `promoted` | bool | Whether this finding has been promoted (default: `false`) |
| `promoted_to` | string/null | Target identifier: `architecture` or lesson hash_id |

## Q-Gate Finding Record

Each line in `qgate-{phase}.jsonl` is a JSON object:

```json
{
  "hash_id": "b4e3d2",
  "timestamp": "2026-03-27T10:05:00Z",
  "type": "build-error",
  "title": "Compilation failure in module cui-jwt",
  "detail": "Cannot find symbol: class JwtValidator",
  "severity": "error",
  "resolution": "pending",
  "source": "qgate",
  "iteration": 1,
  "file_path": "src/main/java/JwtService.java",
  "component": "cui-jwt"
}
```

### Additional Q-Gate Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | `qgate` (automated verification) or `user_review` (user feedback) |
| `iteration` | int | Verification cycle number (1 = first build attempt, 2 = after fixes) |

Q-Gate findings do NOT have `promoted`/`promoted_to` fields — they are not promotable.

## Hash ID Generation

Hash IDs are 6-character hex strings computed deterministically:

- **Plan findings**: Hash of `title + type`
- **Q-Gate findings**: Hash of `title + type + phase`

Same inputs always produce the same hash. This enables deduplication in Q-Gate operations.

## Deduplication (Q-Gate Only)

When adding a Q-Gate finding, the system checks for existing findings with the same title in the phase file:

| Existing State | Action | Returned Status |
|----------------|--------|-----------------|
| No match | Create new record | `success` |
| Match with `pending` resolution | No change | `deduplicated` |
| Match with non-pending resolution | Reset to `pending` | `reopened` |

## Valid Phases

Q-Gate files are created per phase: `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`.

Phase `1-init` is excluded — it creates plan infrastructure and has no verification step.
