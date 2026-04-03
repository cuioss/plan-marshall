---
name: ref-manage-contract
description: Shared contract for all manage-* skills covering enforcement rules, TOON output format, error responses, shared formats, and plan directory layout
user-invocable: false
---

# Manage-* Skills Shared Contract

**REFERENCE MODE**: Shared contract that all manage-* skills follow. Loaded by manage-* skills to avoid repeating identical sections.

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

Hash IDs are 6-character hex strings for unique record identification.

**Algorithm**: `hashlib.sha256(f'{utc_iso}{secrets.token_hex(8)}'.encode()).hexdigest()[:6]`

- IDs are unique per record, NOT deterministic from content
- Used by: manage-findings (finding IDs), manage-logging (log entry hashes)
- Deduplication (where applicable) uses title matching, not hash comparison

### Metadata Conventions

Three metadata styles exist across manage-* skills:

| Style | Used By | Format |
|-------|---------|--------|
| JSON fields | manage-status, manage-references, manage-tasks, manage-config | JSON with `created`/`updated` timestamp fields |
| Markdown key=value headers | manage-lessons | `key=value` lines before content body |
| JSON envelope | manage-memories | `{"meta": {...}, "data": {...}}` wrapper |

All styles include a `created` timestamp in the canonical format above.

### Phase Names

Standard 6-phase model (canonical source: `constants.PHASES`):

| Phase | Purpose |
|-------|---------|
| `1-init` | Initialize plan structure |
| `2-refine` | Clarify request until confident |
| `3-outline` | Create solution outline with deliverables |
| `4-plan` | Create tasks from deliverables |
| `5-execute` | Execute implementation tasks |
| `6-finalize` | Finalize with commit/PR |

The canonical phase name format is `{N}-{name}` (e.g., `1-init`). Context-specific prefixes exist:
- `manage-config` uses `phase-{N}-{name}` as JSON keys in `marshal.json`
- `manage-metrics` uses `phase.{N}-{name}.{field}` as TOON keys

### Profiles

Profiles control which skills are loaded during task execution. Two sets exist:

**Config profiles** (defined in `manage-config` skill_domains, control skill resolution):

| Profile | Phase | Purpose |
|---------|-------|---------|
| `implementation` | execute | Production code patterns |
| `module_testing` | execute | Unit and module test patterns |
| `integration_testing` | execute | Integration test patterns |
| `quality` | verify | Documentation and quality standards |

**Additional task profiles** (used in `manage-tasks`, not mapped to config skill domains):

| Profile | Purpose |
|---------|---------|
| `verification` | Verification-only tasks (no files to modify, runs commands only) |
| `standalone` | Tasks not tied to a specific skill domain |

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
| `missing_required` / `missing_argument` | Required parameter not provided | manage-lessons, manage-plan-documents, manage-tasks |
| `validation_error` | Data failed structural validation | manage-memories, manage-plan-documents |
| `invalid_phase` | Phase name not in valid set | manage-findings, manage-metrics, manage-status |

### Per-Skill Error Codes

#### manage-config
| Error Code | Cause |
|------------|-------|
| `not_initialized` | marshal.json missing |
| `invalid_domain` | Domain not in skill_domains |
| `invalid_field` | Unknown field for phase/noun |
| `skill_not_found` | Skill not in domain defaults/optionals |

#### manage-files
| Error Code | Cause |
|------------|-------|
| `missing_content` | Write called with empty content |
| `invalid_path` | Path contains `..` or absolute components |
| `permission_error` | File system permission denied |

#### manage-findings
| Error Code | Cause |
|------------|-------|
| `already_promoted` | Finding was previously promoted |
| `invalid_type` | Type not in finding types |
| `invalid_resolution` | Resolution not in valid values |

#### manage-lessons
| Error Code | Cause |
|------------|-------|
| `invalid_category` | Category not in: bug, improvement, anti-pattern |
| `invalid_context` | JSON context parsing failed (from-error) |

#### manage-memories
| Error Code | Cause |
|------------|-------|
| `invalid_category` | Category not in valid set |
| `invalid_content` | Content is not valid JSON |

#### manage-metrics
| Error Code | Cause |
|------------|-------|
| `no_data` | No metrics collected yet |
| `write_failed` | File system write error |
| `session_not_found` | JSONL session file not found (enrich) |

#### manage-plan-documents
| Error Code | Cause |
|------------|-------|
| `document_not_found` | Document does not exist |
| `section_not_found` | Requested section missing |

#### manage-references
| Error Code | Cause |
|------------|-------|
| `field_not_found` | Requested field does not exist |
| `type_mismatch` | List operation on non-list field |

#### manage-run-config
| Error Code | Cause |
|------------|-------|
| `not_initialized` | run-configuration.json missing |
| `key_not_found` | Configuration key does not exist |
| `invalid_value` | Value fails type validation |
| `invalid_category` | Warning category not in valid set |
| `marshal_not_found` | marshal.json missing (cleanup needs retention) |

#### manage-solution-outline
| Error Code | Cause |
|------------|-------|
| `parse_error` | Failed to parse document structure |
| `validation_failed` | Missing required sections or invalid numbering |
| `deliverable_not_found` | Deliverable number does not exist |

#### manage-status
| Error Code | Cause |
|------------|-------|
| `phase_not_found` | Phase not in status.json |
| `unknown_phase` | Phase name not in valid set (route) |
| `plan_not_found` | Plan directory does not exist |

#### manage-tasks
| Error Code | Cause |
|------------|-------|
| `task_not_found` | Task number does not exist |
| `step_not_found` | Step number not in task |
| `invalid_content` | TOON content parsing failed |
| `circular_dependency` | Task dependency creates a cycle |
| `invalid_outcome` | Step outcome not `done` or `skipped` |
| `plan_dir_not_found` | Plan directory does not exist |

## Plan Directory Layout

Plan-scoped manage-* skills store data under `.plan/plans/{plan_id}/`:

```
.plan/
  plans/
    {plan_id}/
      status.json          # manage-status
      references.json      # manage-references
      request.md           # manage-plan-documents
      solution_outline.md  # manage-solution-outline
      artifacts/
        findings.jsonl     # manage-findings (plan)
        assessments.jsonl  # manage-findings (assessments)
        qgate-{phase}.jsonl # manage-findings (Q-Gate)
      tasks/
        TASK-001.json      # manage-tasks
      logs/
        script-execution.log  # manage-logging
        work.log              # manage-logging
        decision.log          # manage-logging
      work/
        metrics.toon       # manage-metrics
      metrics.md           # manage-metrics
```

Global-scoped skills store data under `.plan/` directly:

```
.plan/
  marshal.json             # manage-config
  run-configuration.json   # manage-run-config
  memories/                # manage-memories
    context/               #   session snapshots
  lessons-learned/         # manage-lessons
    YYYY-MM-DD-NNN.md      #   individual lessons
    archived/              #   applied lessons
  logs/                    # manage-logging (global fallback)
  project-architecture/    # manage-architecture
    derived-data.json      #   module discovery output
    llm-enriched.json      #   LLM enrichment data
  archived-plans/          # manage-status (archive target)
    YYYY-MM-DD-{plan_id}/  #   archived plan directories
  temp/                    # temporary files (always cleaned)
```

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
