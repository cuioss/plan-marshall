# Manage-* Skills Shared Contract

Shared contract that all manage-* skills follow. Part of the [ref-workflow-architecture](../SKILL.md) documentation.

## Enforcement Contract

All manage-* skills follow these rules:

**Execution mode**: Run scripts via the executor; parse TOON output for status and route accordingly.

```
python3 .plan/execute-script.py plan-marshall:{skill}:{script} {command} {args}
```

**Prohibited actions:**
- Do not modify managed files directly; all mutations go through the script API
- Do not invent script arguments not listed in the skill's Operations section
- Do not bypass the executor to call scripts directly

**Constraints:**
- Scripts are invoked only through `python3 .plan/execute-script.py` with 3-part notation
- Entry-point scripts use either hyphens (e.g., `manage-files.py`) or underscores (e.g., `manage_status.py`) — the filename must match the 3-part executor notation
- Scripts imported as Python modules by other scripts use underscores (e.g., `run_config.py`, `plan_logging.py`)
- Internal modules use underscore prefix (e.g., `_tasks_core.py`, `_cmd_crud.py`)
- All script output uses TOON format (see `plan-marshall:ref-toon-format` for full specification)

## Script Implementation Patterns

Recommended patterns for manage-* script implementations:

**Output**: Use `output_toon()` from `file_ops` for all TOON output. For success/error shortcuts, use `output_success()` and `output_toon_error()` from `file_ops`. Avoid defining skill-local output wrappers.

**Error handling**: Command handler functions (`cmd_*`) should return `int` (0 for success, 1 for error). Avoid `sys.exit(1)` in command handlers — return error codes instead, letting `main()` propagate them via `safe_main`.

**Module structure**: Scripts with 3+ commands should use the modular pattern:
- `_*_core.py` — Shared utilities (path resolution, JSON I/O, validation)
- `_cmd_*.py` — Command group handlers (one file per logical group)
- Entry-point script — Argument parsing and dispatch only

**Boolean arguments**: Use `add_boolean_arg()` from `input_validation` when the script already imports it. Otherwise, the inline pattern `type=lambda x: x.lower() == 'true'` is acceptable for scripts that don't need the full input_validation module.

**Naming conventions**:
- `_cmd_*.py` prefix for command modules (not `_ref_cmd_*` or other prefixes)
- `_*_core.py` for shared core module (abbreviated skill name, e.g., `_tasks_core.py`)

## Module Split Guidelines

Scripts with **3+ commands AND >400 lines** should use the modular pattern:
- `_*_core.py` — Shared utilities
- `_cmd_*.py` — Command group handlers
- Entry-point script — Argument parsing and dispatch only

Individual `_cmd_*.py` modules should stay under **500 lines**. When a module exceeds this, split by sub-domain (e.g., CRUD vs resolution, query vs lifecycle).

Scripts with <400 lines or 1-2 commands may remain monolithic (e.g., manage-files, manage-lessons).

## Recommended Command Patterns

### `get-context`

Plan-scoped skills that are frequently queried together should provide a `get-context` command that returns combined state in a single call. This reduces multiple script invocations to one.

```bash
python3 .plan/execute-script.py plan-marshall:{skill}:{script} get-context --plan-id {plan_id}
```

Implemented by: manage-status, manage-references.

## SKILL.md Structure

All manage-* skills must include `scope:` in YAML frontmatter (`plan`, `global`, or `hybrid`).

Two accepted SKILL.md templates exist:

**CRUD pattern** (most manage-* skills):
1. Enforcement (referencing manage-contract.md)
2. Storage Location
3. File Format
4. Operations (command reference with examples)
5. Integration (producer/consumer tables)
6. Error Responses
7. Related

**Workflow pattern** (manage-architecture, manage-config):
1. Enforcement (referencing manage-contract.md)
2. Scripts (command group overview)
3. Workflow Steps (sequential numbered steps)
4. Error Handling
5. Integration
6. Related

Both patterns require Enforcement, Integration, and Related sections.

## Shared Formats

Canonical format definitions used across all manage-* skills. Individual skill standards reference this section rather than redefining these formats.

### Timestamp Format

All timestamps use ISO 8601 format in UTC timezone:

```
YYYY-MM-DDTHH:MM:SSZ
```

**Rules**:
- Always UTC (Z suffix, never timezone offset)
- Seconds precision (no milliseconds)
- Generated via `now_utc_iso()` from `file_ops`

**Examples**: `2025-12-11T12:14:26Z`, `2026-03-27T10:00:00Z`

### Hash ID Generation

Hash IDs are 6-character hex strings (`HASH_ID_LENGTH = 6` in constants.py).

Two patterns exist depending on the domain:

**Non-deterministic** (unique per record): `hashlib.sha256(f'{utc_iso}{secrets.token_hex(8)}'.encode()).hexdigest()[:6]`
- Used by: `jsonl_store.py` for manage-findings (finding IDs, assessment IDs, Q-Gate IDs)
- Deduplication uses title matching, not hash comparison

**Deterministic** (same input = same hash): `hashlib.sha256(message.encode()).hexdigest()[:6]`
- Used by: `plan_logging.py` for log entry hashes (enables visual grouping of identical messages)

### Metadata Conventions

Three metadata styles exist across manage-* skills:

| Style | Used By | Format |
|-------|---------|--------|
| JSON fields | manage-status, manage-references, manage-tasks, manage-config | JSON with `created`/`updated` timestamp fields |
| Markdown key=value headers | manage-lessons | `key=value` lines before content body |
| JSON envelope | manage-memories | `{"meta": {...}, "data": {...}}` wrapper |

All styles include a `created` timestamp in the canonical format above.

### Phase Names

Canonical source: `constants.PHASES`. See [phases.md](phases.md) for the full 6-phase model (`1-init` through `6-finalize`).

The canonical phase name format is `{N}-{name}` (e.g., `1-init`). Context-specific prefixes exist:
- `manage-config` uses `phase-{N}-{name}` as JSON keys in `marshal.json`
- `manage-metrics` uses `phase.{N}-{name}.{field}` as TOON keys

### Profiles

Profiles control which skills are loaded during task execution. See [task-executors.md](task-executors.md) for executor routing and profile naming conventions.

All profiles map to the unified `plan-marshall:task-executor` skill, which handles profile dispatch internally. Default profiles: `implementation`, `module_testing`, `integration_testing`, `verification`.

## Noun-Verb API Convention

All manage-* scripts follow the noun-verb CLI pattern:

```
python3 .plan/execute-script.py plan-marshall:{skill}:{script} {noun} {verb} [options]
```

Some skills use flat commands (single-level `{verb}`) when only one noun exists. Skills with multiple resource types use two-level subparsers (e.g., `manage-findings`: `qgate add`, `assessment query`).

Common flags:
- `--plan-id {id}` — Plan identifier (kebab-case, required for plan-scoped operations)
- `--help` — Show usage information
- `--force` — Override existence checks on create operations

## TOON Output Contract

All manage-* scripts return TOON-formatted output (see `plan-marshall:ref-toon-format` for the TOON specification).

### output_toon vs serialize_toon

| Function | Module | Behavior | Use When |
|----------|--------|----------|----------|
| `output_toon(data)` | `file_ops` | Serializes and prints to stdout | CLI command handlers returning results |
| `serialize_toon(data)` | `toon_parser` | Returns TOON string | Building error messages for stderr, composing output before printing |

### Success Response

```toon
status: success
message: {description of what was done}
{skill-specific fields}
```

### Error Response

```toon
status: error
error: {error_code}
message: {human-readable description}
```

Exit codes: `0` = success, `1` = error.

## Error Code Registry

### Common Error Codes

Error codes shared across multiple manage-* skills:

| Error Code | Cause | Used By |
|------------|-------|---------|
| `invalid_plan_id` | Plan ID not in kebab-case format | manage-files, manage-metrics, manage-plan-documents, manage-references, manage-status, manage-tasks |
| `file_not_found` | Expected file does not exist | manage-files, manage-memories, manage-references, manage-status |
| `not_found` | Requested resource does not exist | manage-findings, manage-lessons, manage-status |
| `file_exists` | Resource already exists on create | manage-plan-documents, manage-references, manage-status |
| `missing_required` | Required parameter not provided | manage-lessons, manage-plan-documents, manage-tasks |
| `validation_error` | Data failed structural validation | manage-memories, manage-plan-documents |
| `invalid_phase` | Phase name not in valid set | manage-findings, manage-metrics, manage-status |

Per-skill error codes are documented in each skill's own SKILL.md.

**Note**: manage-* skills use `snake_case` error codes (e.g., `invalid_plan_id`). Workflow scripts use `SCREAMING_SNAKE_CASE` codes from `ErrorCode` in `triage_helpers` (e.g., `FETCH_FAILURE`). These are separate registries for separate concerns.

## Plan Directory Layout

See [artifacts.md — Plan Directory Structure](artifacts.md#plan-directory-structure) for the canonical directory tree with file-to-skill mappings.

## Scope Model

| Scope | Description | Storage Root |
|-------|-------------|-------------|
| `plan` | Data tied to a specific plan_id | `.plan/plans/{plan_id}/` |
| `global` | Data shared across all plans | `.plan/` |
| `hybrid` | Both plan-scoped and global operations | Both |

### Skills by Scope

| Scope | Skills |
|-------|--------|
| `plan` | manage-files, manage-findings, manage-plan-documents, manage-references, manage-solution-outline, manage-status, manage-tasks |
| `global` | manage-lessons, manage-memories, manage-run-config |
| `hybrid` | manage-architecture, manage-config, manage-logging, manage-metrics |

## Cross-Skill Relationships

### Promotion: findings → lessons

`manage-findings` can promote findings to `manage-lessons` via the `promote` command. This creates a lesson from a finding's content and marks the finding as promoted. See `manage-findings` for the promotion API and `manage-lessons` for the resulting lesson format.

### Retention Settings

Retention defaults are defined in `manage-config/standards/data-model.md` under the `system.retention` section. Skills that perform cleanup (`manage-run-config cleanup`, `manage-memories cleanup`) read retention values from `marshal.json`.

### Phase Routing

`manage-status route` maps phases to workflow skills. This is a fallback mapping — the authoritative source is `manage-config`'s `skill_domains.system.workflow_skills` in `marshal.json`.
