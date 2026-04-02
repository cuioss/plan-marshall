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

- Plan ID validation (kebab-case format)
- Relative path validation (rejects absolute paths and traversal)
- Enum membership validation
- Skill notation validation (bundle:skill format)
- Both raising (ValueError) and bool return styles

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
