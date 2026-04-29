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

## Error Responses

```toon
status: error
error: validation_failed
message: Plan ID contains invalid characters: bad!!id
```

## Canonical Identifier Registry

| Identifier | Regex | Use sites |
|------------|-------|-----------|
| `plan_id` | `^[a-z][a-z0-9-]*$` | All `manage-*` scripts |
| `lesson_id` | `^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]+$` | `manage-lessons`, `phase-1-init` |
| `session_id` | `^[A-Za-z0-9_-]{1,128}$` | `manage_session`, `set_terminal_title` |
| `task_number` | `^[0-9]+$` | `manage-tasks`, `execute-task` |
| `task_id` | `^TASK-[0-9]+$` | `manage-tasks` (legacy id form) |
| `component` | `^[a-z0-9-]+(:[a-z0-9-]+)*$` | `manage-lessons`, `manage-findings` |
| `hash_id` | `^[a-f0-9]{4,}$` | `manage-findings` (assessment / qgate) |
| `memory_id` | `^[a-z0-9_-]+$` | `manage-memories` |
| `phase_id` | `^[1-6]-(init\|refine\|outline\|plan\|execute\|finalize)$` | All phase scripts |
| `field_name` | `^[a-z][a-z0-9_]*$` | `manage-config`, `manage-references`, `manage-run-config` |
| `module_name` | `^[a-z][a-z0-9_-]*$` | `manage-architecture` |
| `package_name` | `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$` | `manage-architecture` |
| `domain_name` | `^[a-z][a-z0-9-]*$` | `manage-architecture`, `manage-config` |
| `resource_name` | `^[a-zA-Z0-9_-]+$` | Plugin component names (skill / agent / command) |

The constants are exported from `input_validation.py` as `PLAN_ID_RE`, `LESSON_ID_RE`, etc., so consumers can reuse the canonical regex without re-deriving it.

## Adoption

Scripts that accept identifier-shaped arguments should import the matching validator (or the `add_<id>_arg(parser)` builder) from this module rather than doing inline validation. Currently adopted for `--plan-id`: `manage-files`, `manage-references`, `manage-metrics`, `manage-status`, `manage-plan-documents`, `manage-solution-outline`, `manage-findings`, `manage-logging`. The remaining identifier validators (`lesson_id`, `session_id`, `task_number`, `task_id`, `component`, `hash_id`, `memory_id`, `phase_id`, `field_name`, `module_name`, `package_name`, `domain_name`, `resource_name`) are wired in their respective scripts as part of the audit-and-harden sweep documented in `standards/identifier-validation-audit.md`.

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
