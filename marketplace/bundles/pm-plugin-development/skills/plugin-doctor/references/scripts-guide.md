# Script Validation Guide

Validation rules for plugin-doctor Workflow 5 (doctor-scripts) to ensure script compliance against plugin-script-architecture standards.

For detailed script development standards (Python implementation, testing, output contracts, cross-skill integration), load the `pm-plugin-development:plugin-script-architecture` skill. This document defines only the **doctor-specific validation checks** applied against those standards.

## Validation Categories

Each category references a standard from `plugin-script-architecture`. The check criteria and fix strategies below are specific to the doctor's automated validation.

### 1. Subcommand Pattern Validation

**Standard reference**: `plugin-script-architecture:standards/python-implementation.md` (Subcommand Pattern section)

**Check Criteria**:
1. Script name is `{noun}.py` (not `{verb}-{noun}.py`)
2. Script uses argparse subcommands (search for `subparsers = parser.add_subparsers`)
3. Help output shows available subcommands

**Categorization**: Risky fix (requires script restructuring)

**Fix Strategy**: Flag for migration - script needs refactoring to subcommand pattern

### 2. Executor Pattern Validation

**Standard reference**: `plugin-script-architecture:standards/cross-skill-integration.md`

**Check Criteria**:
1. Script usage examples use `python3 .plan/execute-script.py {notation} ...`
2. No direct script path usage (`python3 {path}/*.py ...`)
3. No path variable placeholders (`python3 {script_path} ...`)

**Categorization**: Safe fix (pattern replacement)

**Fix Strategy**: Auto-correct to executor pattern using notation

### 3. Stdlib-Only Validation

**Standard reference**: `plugin-script-architecture:standards/python-implementation.md` (Stdlib-Only Requirement) and `plugin-script-architecture:references/stdlib-modules.md` for the allowed module list

**Check Criteria**:
1. Script imports only allowed stdlib modules
2. No `import yaml`, `import requests`, etc.
3. No pip dependencies in any form

**Categorization**: Risky fix (requires code refactoring)

**Fix Strategy**: Flag for manual review - suggest stdlib alternatives

### 4. TOON Output Validation

**Standard reference**: `plugin-script-architecture:standards/output-contract.md`

**Check Criteria**:
1. Script outputs TOON format (default) or JSON (complex nested only)
2. Errors go to stderr
3. Exit codes: 0 for success, 1 for error

**Categorization**: Risky fix (output format change)

**Fix Strategy**: Flag for migration - document TOON conversion needed

### 5. Test Coverage Validation

**Standard reference**: `plugin-script-architecture:standards/testing-standards.md`

**Check Criteria**:
1. Test file exists: `test/{bundle}/{skill}/test_{script}.py`
2. Test file contains at least one `assert` statement
3. Tests cover: happy path, missing input, invalid input, edge cases

**Categorization**: Safe fix (flag for test creation)

**Fix Strategy**: Report missing tests, suggest test template

### 6. Script Size Validation (Modularization)

**Standard reference**: `plugin-script-architecture:standards/python-implementation.md` (Modularization section)

**Check Criteria**:
1. Count lines in main script file
2. If >400 lines, check for modular structure (cmd_*.py files in same directory)
3. Main script should be <250 lines (parser + dispatch only)

**Categorization**: Risky fix (requires script restructuring)

**Fix Strategy**: Flag for refactoring - split into modules

### 7. Help Output Validation

**Standard reference**: `plugin-script-architecture:standards/python-implementation.md` (argparse requirements)

**Check Criteria**:
1. Running `python3 .plan/execute-script.py {notation} --help` exits with code 0
2. Help output includes: usage, description, parameters, examples
3. Subcommand help also available

**Categorization**: Safe fix (add argparse help)

**Fix Strategy**: Flag missing help - argparse provides automatic help

### 8. Test Size Validation (Modularization)

**Standard reference**: `plugin-script-architecture:standards/testing-standards.md` (Modularization section)

**Check Criteria**:
1. Count lines in main test file
2. If >400 lines, check for modular structure (test_cmd_*.py files in same directory)
3. Main test file should be <250 lines (integration tests only)

**Categorization**: Risky fix (requires test restructuring)

**Fix Strategy**: Flag for refactoring - split into modules

### 9. Argument Convention Validation

**Standard reference**: `plugin-script-architecture:standards/python-implementation.md` (Argument Conventions section)

**Check Criteria**:
1. All `add_argument()` calls use `--` prefix (no positional args)
2. All `--flag` names use kebab-case (no camelCase)
3. All `add_subparsers()` calls include `required=True`

**Exclusions**: Subcommand dest args (e.g., `dest='command'`) are not positional arguments.

**Categorization**: Safe fix (mechanical transformation)

### 10. Argparse Safety (`allow_abbrev=False`)

**Standard reference**: `plugin-script-architecture:standards/python-implementation.md` (Argument Conventions section) and driving lesson 2026-04-17-012.

**Required parameter**: Every `argparse.ArgumentParser(...)` constructor and every `subparsers.add_parser(...)` call in a marketplace Python script with a user-facing CLI MUST pass `allow_abbrev=False`.

**Why it is required**: argparse's default behavior matches unknown long options by unique prefix. When a flag is renamed or removed, callers that still pass the old long form keep working — the new parser silently binds the old name via prefix matching. This turns contract rot into a silent bug class. Passing `allow_abbrev=False` disables prefix matching, so retired or renamed flags fail loudly with "unrecognized arguments" instead of quietly re-binding.

**Check Criteria**:
1. Every `ArgumentParser(...)` call includes `allow_abbrev=False` as a keyword argument.
2. Every `subparsers.add_parser(...)` call includes `allow_abbrev=False`.
3. Scope: files under `marketplace/bundles/*/skills/*/scripts/` and `marketplace/adapters/`.

**Exclusions**: Tests (files under `test/`/`tests/` directories, or named `test_*.py` / `*_test.py`) may intentionally exercise default argparse behavior and are skipped.

**Categorization**: Unfixable (manual edit) — the rule is detection-only; add the flag to each flagged call.

**Fix Strategy**: Audit the flagged `file:line` and add `allow_abbrev=False` to the constructor.

**Rule id**: `argparse_safety` (severity: error). See `rule-catalog.md` "Script Rules" for the full catalog entry.

## Validation Workflow

### Step 1: Discover Scripts

```bash
Glob: pattern="scripts/*.py", path="marketplace/bundles/*/skills/*"
```

### Step 2: For Each Script, Check

1. **Naming**: Is it `{noun}.py` pattern?
2. **Structure**: Does it use argparse subcommands?
3. **Imports**: Are all imports stdlib-only?
4. **Output**: Does it use TOON/JSON format?
5. **Tests**: Does test file exist?
6. **Size**: Is it >400 lines? If so, is it modularized?
7. **Help**: Does `--help` work?
8. **Test Size**: Is test file >400 lines? If so, is it modularized?

### Step 3: For Each SKILL.md, Check

1. **Documentation**: Are scripts documented?
2. **Invocation**: Do examples use executor pattern?

### Step 4: Categorize Issues

| Issue Type | Category | Auto-Fix |
|------------|----------|----------|
| Wrong naming pattern | Risky | No |
| Missing subcommands | Risky | No |
| Direct path invocation | Safe | Yes |
| External imports | Risky | No |
| JSON instead of TOON | Risky | No |
| Missing tests | Safe | No |
| Script >400 lines not modularized | Risky | No |
| Missing help | Safe | No |
| Test >400 lines not modularized | Risky | No |
| Missing `allow_abbrev=False` | Unfixable | No |

### Step 5: Report

```toon
status: {success|issues_found}
scripts_checked: {count}
issues_found: {count}

issues[N]{script,issue_type,severity,auto_fixable}:
manage-files.py	missing_tests	medium	no
execute-build.py	wrong_naming	high	no
...
```

## Related Standards

- `pm-plugin-development:plugin-script-architecture` - Single source of truth for script development standards
