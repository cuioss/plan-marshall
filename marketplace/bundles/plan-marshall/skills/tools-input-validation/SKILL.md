---
name: tools-input-validation
description: Shared input validation module for plan-marshall scripts — validates plan IDs, file paths, enums, and skill notation
user-invocable: false
---

# Input Validation Base Skill

**Role**: Shared Python module providing input validation functions for plan-marshall scripts. Prevents path traversal, invalid plan IDs, and malformed inputs from reaching filesystem operations.

## Enforcement

**Execution mode**: Library module; import validators as documented in usage examples.

**Prohibited actions:**
- Do not validate plan IDs with custom regex; use `validate_plan_id()`
- Do not validate file paths without `validate_relative_path()`
- Do not bypass validation in scripts that accept user/LLM input

**Constraints:**
- All plan IDs must match `^[a-z][a-z0-9-]*$`
- Relative paths must reject absolute paths and traversal sequences
- Use raising validators for fail-fast behavior, bool validators for conditional logic

## What This Skill Provides

- Canonical regex constants for the full identifier vocabulary (single source of truth)
- Plan ID validation (kebab-case format)
- Lesson, session, task, component, hash, memory, phase, field, module, package, domain, and resource-name validators
- Relative path validation (rejects absolute paths and traversal)
- Enum membership validation
- Skill notation validation (bundle:skill format)
- Both raising (ValueError) and bool return styles
- Argparse builder helpers (`add_<id>_arg(parser)`) that wire the validator into argparse `type=` so malformed input is rejected at the script boundary

## When to Use

Import `input_validation` module in Python scripts that:
- Accept `plan_id` arguments for path construction
- Accept file paths from user/LLM input
- Need enum validation for argument values
- Reference skill notation strings

## Module: input_validation.py

**Location**: `scripts/input_validation.py`

### Functions

**Raising Validators** (return validated value or raise ValueError)

**1. validate_plan_id(plan_id: str) -> str**
- **Purpose**: Validate plan_id matches `^[a-z][a-z0-9-]*$`
- **Input**: `plan_id` string
- **Output**: The validated plan_id string
- **Raises**: `ValueError` if invalid

**2. validate_relative_path(file_path: str) -> str**
- **Purpose**: Reject absolute paths and `..` traversal
- **Input**: `file_path` string
- **Output**: The validated file_path string
- **Raises**: `ValueError` if empty, absolute, or contains traversal

**3. validate_enum(value: str, allowed: list, label: str) -> str**
- **Purpose**: Check value is in allowed list
- **Input**: `value`, list of `allowed` values, `label` for error message
- **Output**: The validated value string
- **Raises**: `ValueError` if not in allowed list

**4. validate_skill_notation(skill: str) -> str**
- **Purpose**: Validate `bundle:skill` format
- **Input**: `skill` notation string
- **Output**: The validated skill string
- **Raises**: `ValueError` if not in `bundle:skill` format

**5. validate_script_notation(notation: str) -> str**
- **Purpose**: Validate `bundle:skill:script` format (3-part executor notation)
- **Input**: `notation` string
- **Output**: The validated notation string
- **Raises**: `ValueError` if not in `bundle:skill:script` format

**Bool Companions** (drop-in replacements for existing patterns)

**6. is_valid_plan_id(plan_id: str) -> bool**
- **Purpose**: Check if plan_id is valid (no exception)
- **Input**: `plan_id` string
- **Output**: `True` if valid, `False` otherwise

**7. is_valid_relative_path(file_path: str) -> bool**
- **Purpose**: Check if file path is valid relative path (no exception)
- **Input**: `file_path` string
- **Output**: `True` if valid, `False` otherwise

## Lesson-ID Reference Scanner (Live-Anchored)

These helpers detect lesson-ID-shaped tokens embedded in arbitrary prose
(typically task titles and descriptions) and verify them against the live
`manage-lessons` inventory. They are the single source of truth for
"is this a real lesson ID?" checks across the bundle, used by
`manage-tasks` (at-write-time validation) and `plan-doctor` (post-hoc
plan diagnostics).

All three helpers reuse the canonical `LESSON_ID_RE` constant — no new
regex literal is introduced. The embedded scanner uses an unanchored
derivative (`_LESSON_ID_EMBEDDED_RE`) of the same pattern with non-digit
boundary lookarounds so adjacent digits don't bleed into a match.

### Live-Anchor Discipline

Per lesson `2026-04-29-10-001`, the canonical regex shape is asserted
against actual repo data at runtime — not only in the test suite. On
first invocation per process, `scan_lesson_id_tokens` and
`verify_lesson_ids_exist` call `verify_lesson_id_regex_against_inventory`,
which:

- Spawns `manage-lessons list` and parses the TOON inventory.
- If the inventory has IDs and at least one matches `LESSON_ID_RE`,
  caches success for the rest of the process.
- If the inventory is empty (greenfield repo or wiped state), emits a
  one-time WARNING to `stderr` and treats the anchor as a no-op so
  greenfield use isn't a hard error.
- If the inventory has IDs but NONE match `LESSON_ID_RE`, raises
  `LessonRegexAnchoringError` with the regex pattern and a sample of the
  unmatched IDs. The cache is NOT set, so every subsequent scanner call
  keeps failing until the regex (or the IDs) is corrected. This is the
  failure mode that exists precisely because regex-vs-inventory drift can
  otherwise produce a silent "no IDs match anything" false-clean signal.

### Public API

**8. scan_lesson_id_tokens(text: str) -> list[str]**
- **Purpose**: Return every lesson-ID-shaped token embedded in `text`.
- **Input**: arbitrary `text` (e.g., a task title + description).
- **Output**: list of matching tokens in order of appearance.
- **Raises**: `LessonRegexAnchoringError`, `LessonInventoryUnavailable`
  via the first-use anchor check.

**9. verify_lesson_ids_exist(tokens: Iterable[str]) -> dict[str, bool]**
- **Purpose**: Return `{token: present}` for each token by lookup against
  the live `manage-lessons` inventory. Duplicates de-duplicated.
- **Input**: iterable of candidate lesson-ID tokens.
- **Output**: dict mapping each unique token to `True` if found in the
  live inventory, `False` otherwise.
- **Raises**: `LessonInventoryUnavailable` when the subprocess fails —
  NEVER silently returns "all present". Also `LessonRegexAnchoringError`
  via the first-use anchor check.

**10. verify_lesson_id_regex_against_inventory() -> None**
- **Purpose**: Runtime live-anchor check (see "Live-Anchor Discipline"
  above). Idempotent within a process.
- **Output**: `None` on success or empty-inventory no-op.
- **Raises**: `LessonRegexAnchoringError` when live IDs exist but none
  match `LESSON_ID_RE`; `LessonInventoryUnavailable` on subprocess
  failure.

### Typed Exceptions

**`LessonInventoryUnavailable(RuntimeError)`** — raised whenever
`manage-lessons list` cannot be invoked, exits non-zero, or returns
output the TOON parser rejects. Callers MUST surface this; silently
degrading to "all present" defeats the entire purpose of the scanner.

**`LessonRegexAnchoringError(RuntimeError)`** — raised when the live
inventory contains IDs but none of them match `LESSON_ID_RE`. Carries
`regex` (the pattern that failed to anchor) and `sample_ids` (a slice of
the unmatched IDs) for diagnostics.

### Usage

```python
from input_validation import (
    LessonInventoryUnavailable,
    LessonRegexAnchoringError,
    scan_lesson_id_tokens,
    verify_lesson_ids_exist,
)

text = "Per lesson 2026-04-29-10-001, anchor regex against live inventory."
try:
    tokens = scan_lesson_id_tokens(text)
    presence = verify_lesson_ids_exist(tokens)
    missing = [tok for tok, ok in presence.items() if not ok]
    if missing:
        raise ValueError(f"Unresolved lesson IDs: {missing}")
except LessonRegexAnchoringError as exc:
    # Hard fail — the regex shape has drifted from the inventory.
    raise
except LessonInventoryUnavailable as exc:
    # Hard fail — inventory unreachable; do not silently pretend
    # everything is present.
    raise
```

## Error Responses

```toon
status: error
error: validation_failed
message: Plan ID contains invalid characters: bad!!id
```

## Canonical Identifier Registry

| Identifier | Regex | Builder | Adoption status |
|------------|-------|---------|-----------------|
| `plan_id` | `^[a-z][a-z0-9-]*$` | `add_plan_id_arg` | Adopted across all 32 swept scripts (Wave A/B/C) |
| `lesson_id` | `^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]+$` | `add_lesson_id_arg` | Adopted: `manage-lessons` (with `action='append'`), `phase-1-init` |
| `session_id` | `^[A-Za-z0-9_-]{1,128}$` | `add_session_id_arg` | Adopted: `manage_session`, `manage-memories`, `manage-metrics`, `compile-report` |
| `task_number` | `^[0-9]+$` | `add_task_number_arg` | Adopted: `manage-tasks` (post-validate int coercion) |
| `task_id` | `^TASK-[0-9]+$` | `add_task_id_arg` | Adopted: `manage-tasks` (legacy id form) |
| `component` | `^[a-z0-9-]+(:[a-z0-9-]+)*$` | `add_component_arg` | Adopted: `manage-lessons`, `manage-findings`, `sonar_rest` |
| `hash_id` | `^[a-f0-9]{4,}$` | `add_hash_id_arg` | Adopted: `manage-findings` (assessment / qgate) |
| `memory_id` | `^[a-z0-9_-]+$` | `add_memory_id_arg` | Adopted: `manage-memories` |
| `phase_id` | `^[1-6]-(init\|refine\|outline\|plan\|execute\|finalize)$` | `add_phase_arg` | Adopted: `phase_handshake`, `manage-logging`, `manage-metrics`, `manage_status` |
| `field_name` | `^[a-z][a-z0-9_]*$` | `add_field_arg` | Adopted: `manage-config`, `manage-references`, `manage-run-config`, `manage_status`, `manage-interface` |
| `module_name` | `^[a-z][a-z0-9_-]*$` | `add_module_arg` | Adopted: `architecture`, `manage-findings`, `profiles` |
| `package_name` | `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$` | `add_package_arg` | Adopted: `architecture` |
| `domain_name` | `^[a-z][a-z0-9-]*$` | `add_domain_arg` | Adopted: `architecture`, `manage-config`, `manage-tasks` |
| `resource_name` | `^[a-zA-Z0-9_-]+$` | `add_name_arg` | Adopted: `architecture`, `profiles` |

The constants are exported from `input_validation.py` as `PLAN_ID_RE`, `LESSON_ID_RE`, etc., so consumers can reuse the canonical regex without re-deriving it. The `add_<id>_arg(parser)` builders wire `type=validate_<id>` into argparse so malformed input is rejected at the CLI boundary; pair them with `parse_args_with_toon_errors()` to centralise the `status: error / error: invalid_<field>` output path.

## Adoption

The cross-bundle sweep (lesson-2026-04-29-08-003) migrated all 32 in-scope scripts spanning `plan-marshall`, `pm-dev-java`, and `pm-documents` to the canonical builders. The current sweep state is enumerated by wave in [standards/identifier-validation-audit.md](standards/identifier-validation-audit.md), which is the single source of truth: it lists every migrated script, the in-scope flags adopted, the identifier-handling families covered, and the test directory exercising the 6-axis rejection-path coverage. The audit also enumerates the 47 `CERTAIN_EXCLUDE` scripts (helpers, providers, build runners with no in-scope flags) and the breaking-compat decisions that fell out of the sweep (e.g., `SESSION_ID_RE` relaxed from strict UUID, `COMPONENT_RE` rejects uppercase / path-shaped Sonar keys).

When adding a new script that accepts identifier-shaped flags or migrating new flags on an existing script, update both the audit document and the table above so the registry remains consistent.

## Python Usage

```python
from input_validation import is_valid_plan_id, validate_enum

# Plan ID validation (alphanumeric + hyphens, 1-64 chars)
if not is_valid_plan_id(args.plan_id):
    output_error('invalid_plan_id', f'Invalid plan_id format: {args.plan_id}')
    sys.exit(1)

# Enum validation
validate_enum(args.certainty, ['CERTAIN_INCLUDE', 'CERTAIN_EXCLUDE', 'UNCERTAIN'], 'certainty')
```

## Module: schema_validation.py

**Location**: `scripts/schema_validation.py`

Lightweight schema validation for plan-marshall JSON storage files. Returns a list of error strings (empty list = valid). No external dependencies.

### Functions

**1. validate_status(data: Any) -> list[str]**
- **Purpose**: Validate `status.json` — requires `plan_id` (str), `current_phase` (str), `phases` (list of dicts with `name` and `status`)

**2. validate_references(data: Any) -> list[str]**
- **Purpose**: Validate `references.json` — requires `plan_id` (str)

**3. validate_task(data: Any) -> list[str]**
- **Purpose**: Validate `TASK-*.json` — requires `task_id` (str), `title` (str), `status` (str), `steps` (list of dicts with `id` and `title`)

**4. validate_assessment(data: Any) -> list[str]**
- **Purpose**: Validate assessment records — requires `hash_id` (str), `file_path` (str), `certainty` (str, one of CERTAIN_INCLUDE/CERTAIN_EXCLUDE/UNCERTAIN), `confidence` (int or float)

**5. validate_finding(data: Any) -> list[str]**
- **Purpose**: Validate finding records — requires `hash_id` (str), `type` (str), `severity` (str), `message` (str)

### Schema Validation Usage

```python
from schema_validation import validate_status, validate_task

errors = validate_status(data)
if errors:
    output_error('schema_violation', '; '.join(errors))
    sys.exit(1)
```

## Usage Examples

```python
# Drop-in replacement for existing validate_plan_id pattern
from input_validation import is_valid_plan_id

if not is_valid_plan_id(args.plan_id):
    print(f'Error: Invalid plan_id format: {args.plan_id}', file=sys.stderr)
    sys.exit(1)

# New code: raising style with chaining
from input_validation import validate_plan_id, validate_relative_path

plan_id = validate_plan_id(args.plan_id)  # raises ValueError
file_path = validate_relative_path(args.file)  # raises ValueError

# Enum validation
from input_validation import validate_enum

validate_enum(args.status, ['pending', 'done', 'blocked'], 'status')
```
