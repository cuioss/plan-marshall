# Script Validation Guide

Validation rules for plugin-doctor Workflow 5 (doctor-scripts) to ensure script compliance against plugin-script-architecture standards.

## Validation Categories

### 1. Subcommand Pattern Validation

**Standard**: Scripts MUST follow `{noun}.py {verb}` pattern using argparse subparsers.

**Check Criteria**:
1. Script name is `{noun}.py` (not `{verb}-{noun}.py`)
2. Script uses argparse subcommands (search for `subparsers = parser.add_subparsers`)
3. Help output shows available subcommands

**Detection**:
```python
# COMPLIANT: noun.py with subcommands
manage-files.py add --plan-id my-plan
maven.py run --targets verify
analyze.py markdown --file input.md

# VIOLATION: verb-noun.py pattern
add-file.py --plan-id my-plan
execute-maven-build.py --goals verify
get-config.py --key foo
```

**Categorization**: Risky fix (requires script restructuring)

**Fix Strategy**: Flag for migration - script needs refactoring to subcommand pattern

### 2. Executor Pattern Validation

**Standard**: All script invocations MUST use `python3 .plan/execute-script.py {notation} {subcommand} {args}`.

**Check Criteria**:
1. Script usage examples use `python3 .plan/execute-script.py {notation} ...`
2. No direct script path usage (`python3 {path}/*.py ...`)
3. No path variable placeholders (`python3 {script_path} ...`)

**Detection in SKILL.md files**:
```markdown
# COMPLIANT
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files add --plan-id my-plan
python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets verify

# VIOLATION (direct path)
python3 /path/to/marketplace/.../manage-files.py add --plan-id my-plan
python3 marketplace/bundles/planning/skills/manage-files/scripts/manage-files.py add

# VIOLATION (path variable)
python3 {manage_files_path} add --plan-id my-plan
Bash: scripts/script-name.sh {args}
```

**Categorization**: Safe fix (pattern replacement)

**Fix Strategy**: Auto-correct to executor pattern using notation

### 3. Stdlib-Only Validation

**Standard**: Scripts MUST use only Python standard library (no pip dependencies).

**Check Criteria**:
1. Script imports only allowed stdlib modules
2. No `import yaml`, `import requests`, etc.
3. No pip dependencies in any form

**Allowed Modules** (per `plugin-script-architecture:references/stdlib-modules.md`):
- `json`, `argparse`, `pathlib`, `re`, `sys`, `os`
- `datetime`, `shutil`, `subprocess`, `tempfile`, `textwrap`
- `collections`, `typing`, `dataclasses`, `functools`, `itertools`
- `contextlib`, `io`, `hashlib`, `base64`, `urllib.parse`, `difflib`
- `unittest`, `time`, `copy`, `logging`, `string`, `enum`, `uuid`
- `glob`, `fnmatch`

**Prohibited Imports**:
```python
# VIOLATIONS
import yaml          # Use custom simple YAML parser
import requests      # Use urllib
import numpy         # Not needed for scripts
import pandas        # Not needed for scripts
from toml import *   # External package (Python < 3.11)
```

**Categorization**: Risky fix (requires code refactoring)

**Fix Strategy**: Flag for manual review - suggest stdlib alternatives

### 4. TOON Output Validation

**Standard**: Scripts SHOULD output TOON format (tab-separated, header row pattern).

**Check Criteria**:
1. Script outputs TOON format (default) or JSON (complex nested only)
2. Errors go to stderr
3. Exit codes: 0 for success, 1 for error

**TOON Format**:
```toon
status: success
count: 3

items[3]{id,name,status}:
TASK-001	Implement feature	in_progress
TASK-002	Write tests	pending
TASK-003	Update docs	pending
```

**JSON Acceptable When**:
- Complex nested structures (>3 levels deep)
- Non-uniform object shapes
- API interchange with external tools

**Categorization**: Risky fix (output format change)

**Fix Strategy**: Flag for migration - document TOON conversion needed

### 5. Test Coverage Validation

**Standard**: All scripts MUST have corresponding test files.

**Check Criteria**:
1. Test file exists: `test/{bundle}/{skill}/test_{script}.py`
2. Test file contains at least one `assert` statement
3. Tests cover: happy path, missing input, invalid input, edge cases

**Detection**:
```bash
# For script: marketplace/bundles/planning/skills/manage-files/scripts/manage-files.py
# Expected test: test/planning/manage-files/test_manage_files.py
```

**Categorization**: Safe fix (flag for test creation)

**Fix Strategy**: Report missing tests, suggest test template

### 6. Script Size Validation (Modularization)

**Standard**: Scripts exceeding 400 lines MUST be modularized by subcommand.

**Check Criteria**:
1. Count lines in main script file
2. If >400 lines, check for modular structure (cmd_*.py files in same directory)
3. Main script should be <250 lines (parser + dispatch only)

**Detection**:
```bash
# Check script line count
wc -l scripts/{script}.py

# Check for modular structure
ls scripts/cmd_*.py scripts/config_*.py
```

**Modular Structure Expected**:
```
scripts/
  {script}.py        # <250 lines: parser + dispatch
  config_core.py     # Shared utilities
  config_defaults.py # Constants
  cmd_{noun1}.py     # Command handlers
  cmd_{noun2}.py     # Command handlers
```

**Categorization**: Risky fix (requires script restructuring)

**Fix Strategy**: Flag for refactoring - split into modules per `plugin-script-architecture:standards/python-implementation.md`

### 7. Help Output Validation

**Standard**: All scripts MUST support `--help` flag via argparse.

**Check Criteria**:
1. Running `python3 .plan/execute-script.py {notation} --help` exits with code 0
2. Help output includes: usage, description, parameters, examples
3. Subcommand help also available

**Detection**:
```bash
python3 .plan/execute-script.py {bundle}:{skill} --help
python3 .plan/execute-script.py {bundle}:{skill} {subcommand} --help
```

**Categorization**: Safe fix (add argparse help)

**Fix Strategy**: Flag missing help - argparse provides automatic help

### 8. Test Size Validation (Modularization)

**Standard**: Test files exceeding 400 lines MUST be modularized by command module.

**Check Criteria**:
1. Count lines in main test file
2. If >400 lines, check for modular structure (test_cmd_*.py files in same directory)
3. Main test file should be <250 lines (integration tests only)

**Detection**:
```bash
# Check test file line count
wc -l test/{bundle}/{skill}/test_{script}.py

# Check for modular structure
ls test/{bundle}/{skill}/test_cmd_*.py test/{bundle}/{skill}/test_helpers.py
```

**Modular Structure Expected**:
```
test/{bundle}/{skill}/
  test_helpers.py              # Shared fixtures (no tests)
  test_cmd_{noun1}.py          # {noun1} command variants/corners
  test_cmd_{noun2}.py          # {noun2} command variants/corners
  test_{script}.py             # <250 lines: happy-path integration only
```

**Categorization**: Risky fix (requires test restructuring)

**Fix Strategy**: Flag for refactoring - split into modules per `plugin-script-architecture:standards/testing-standards.md`

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

### 9. Argument Convention Validation

**Standard**: Scripts MUST follow argument conventions from `plugin-script-architecture:standards/python-implementation.md`.

**Check Criteria**:
1. All `add_argument()` calls use `--` prefix (no positional args)
2. All `--flag` names use kebab-case (no camelCase)
3. All `add_subparsers()` calls include `required=True`

**Detection**:
```python
# COMPLIANT
parser.add_argument('--plan-id', required=True, dest='plan_id')
parser.add_argument('--file-path', required=True, dest='file_path')
subparsers = parser.add_subparsers(dest='command', required=True)

# VIOLATION: positional argument
parser.add_argument('plan_id')

# VIOLATION: camelCase flag
parser.add_argument('--commandArgs')

# VIOLATION: missing required=True on subparsers
subparsers = parser.add_subparsers(dest='command')
```

**Exclusions**: Subcommand dest args (e.g., `dest='command'`) are not positional arguments.

**Categorization**: Safe fix (mechanical transformation)

## Related Standards

- `pm-plugin-development:plugin-script-architecture` - Full script development standards
- `plugin-script-architecture:standards/python-implementation.md` - Python patterns
- `plugin-script-architecture:standards/testing-standards.md` - Test requirements
- `plugin-script-architecture:standards/output-contract.md` - TOON/JSON output
