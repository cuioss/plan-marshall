# Script Standards

Comprehensive standards for marketplace scripts including location, documentation requirements, testing, help output, stdlib-only dependencies, JSON output format, and error handling.

## Overview

Scripts are executable files (shell scripts, Python scripts) providing deterministic validation logic. They complement AI-powered agents by handling pattern matching, parsing, and calculation tasks.

**Key Characteristics**:
- Located in `{skill-dir}/scripts/` directory
- Invoked via `python3 .plan/execute-script.py {bundle}:{skill} {subcommand} {args}`
- Stdlib-only (no external dependencies)
- TOON/JSON output format (for machine parsing)
- Executable permissions required
- Must support `--help` flag

## Script Location

**Standard Location**: `{skill-dir}/scripts/`

**Example**:
```
marketplace/bundles/pm-plugin-development/skills/plugin-diagnose/
└── scripts/
    ├── analyze-markdown-file.sh
    ├── analyze-tool-coverage.sh
    ├── analyze-skill-structure.sh
    └── validate-references.py
```

**Invocation from SKILL.md**:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze markdown --file {file_path} --type agent
```

## Documentation Requirements in SKILL.md

**CRITICAL**: All scripts MUST be documented in SKILL.md.

### Required Documentation

**For Each Script**:

1. **Purpose**: One-sentence description of what script does
2. **Input**: Parameters, types, formats
3. **Output**: Return format (typically JSON with schema)
4. **Usage**: Example invocation from workflow

**Template**:
```markdown
## External Resources

### Scripts (in scripts/)

**1. {script-name}.py**: Brief purpose statement
- **Input**: parameter1 (type), parameter2 (type)
- **Output**: TOON/JSON with {field_names}
- **Usage**:
  ```bash
  python3 .plan/execute-script.py {bundle}:{skill} {subcommand} --param1 {value1} --param2 {value2}
  ```
- **Example Output**:
  ```toon
  status: success
  field1: value
  field2: 123
  ```
```

### Example Documentation

**Real Example** (from plugin-doctor SKILL.md):
```markdown
### Scripts (in scripts/)

**1. analyze.py**: Analyzes file structure, frontmatter, bloat, Rule 6/7/Pattern 22 violations
- **Input**: file path, component type (agent|command|skill)
- **Output**: JSON with structural analysis
- **Usage**:
  ```bash
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze markdown --file {file_path} --type agent
  ```

**2. analyze.py coverage**: Analyzes tool coverage and fit for agents/commands
- **Input**: file path
- **Output**: JSON with tool analysis (score, missing, unused, critical violations)
- **Usage**:
  ```bash
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze coverage --file {file_path}
  ```

**3. analyze.py structure**: Analyzes skill directory structure and file references
- **Input**: skill directory path
- **Output**: JSON with structure analysis (score, missing files, unreferenced files)
- **Usage**:
  ```bash
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze structure --directory {skill_dir}
  ```

**4. validate.py references**: Python script for reference pre-filtering and extraction
- **Input**: file path
- **Output**: JSON with detected references and pre-filter statistics
- **Usage**:
  ```bash
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate references --file {file_path}
  ```
```

## Test File Requirements

**CRITICAL**: All scripts MUST have test files.

### Test File Naming Convention

**Pattern**: `test/pm-plugin-development/{skill-name}/test-{script-name}.sh`

**Example**:
```
test/pm-plugin-development/plugin-diagnose/
├── test-analyze-markdown-file.sh
├── test-analyze-tool-coverage.sh
├── test-analyze-skill-structure.sh
└── test-validate-references.sh
```

### Test File Structure

**Standard Structure**:
```bash
#!/bin/bash
# Test suite for script-name.sh
#
# Usage: ./test-script-name.sh

set -euo pipefail

# Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCRIPT_UNDER_TEST="$PROJECT_ROOT/marketplace/bundles/.../scripts/script-name.sh"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/script-name"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test functions
run_test() {
    local test_name="$1"
    # ... test logic
}

# Test cases
test_case_1() {
    run_test "Test case 1" ...
}

test_case_2() {
    run_test "Test case 2" ...
}

# Main
main() {
    echo "Test Suite: script-name.sh"

    test_case_1
    test_case_2
    # ... more tests

    # Summary
    echo "Tests: $TESTS_RUN, Passed: $TESTS_PASSED, Failed: $TESTS_FAILED"

    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

main
```

### Test Fixtures

**Location**: `test/{bundle}/{skill}/fixtures/{script-name}/`

**Purpose**: Test input files and expected outputs

**Example**:
```
test/pm-plugin-development/plugin-diagnose/fixtures/
└── analyze-markdown-file/
    ├── valid-agent.md
    ├── bloated-command.md
    ├── missing-frontmatter.md
    └── invalid-yaml.md
```

### Running Tests

**Manual Execution**:
```bash
cd test/pm-plugin-development/plugin-diagnose/
./test-analyze-markdown-file.sh
```

**Expected Output**:
```
========================================
Test Suite: analyze-markdown-file.sh
========================================

Test: Valid agent ... PASS
Test: Bloated command ... PASS
Test: Missing frontmatter ... PASS
Test: Invalid YAML ... PASS

========================================
Test Summary
========================================
Total tests:   4
Passed:        4
Failed:        0

✓ All tests passed!
```

## Help Output Requirements

**CRITICAL**: All scripts MUST support `--help` flag.

### Help Output Format

**Required Sections**:
1. **Usage**: Command syntax
2. **Description**: What the script does
3. **Parameters**: Input parameters with descriptions
4. **Output**: Output format
5. **Examples**: Usage examples

**Template**:
```bash
# In script:
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<EOF
Usage: $(basename "$0") <file_path> [component_type]

Description:
  Analyzes markdown file structure, frontmatter, and compliance.

Parameters:
  file_path       Path to markdown file to analyze
  component_type  Optional: agent|command|skill (default: auto-detect)

Output:
  JSON with structural analysis including:
  - file_path: Input file path
  - metrics: Line count, section count
  - frontmatter: Presence, validity, required fields
  - bloat: Classification (NORMAL, LARGE, BLOATED, CRITICAL)

Examples:
  # Analyze agent file:
  $(basename "$0") agents/my-agent.md agent

  # Auto-detect component type:
  $(basename "$0") commands/my-command.md

EOF
    exit 0
fi
```

### Help Output Validation

**Test**:
```bash
python3 .plan/execute-script.py {bundle}:{skill} --help
python3 .plan/execute-script.py {bundle}:{skill} {subcommand} --help
```

**Verify**:
- ✅ Prints usage information
- ✅ Exit code 0
- ✅ Output includes all required sections
- ✅ Examples are accurate

## Stdlib-Only Requirement

**CRITICAL**: Scripts MUST use only standard library (no external dependencies).

### Shell Scripts (bash)

**Allowed**:
- ✅ Standard Unix utilities (grep, sed, awk, find, cat, etc.)
- ✅ jq (widely available JSON processor) - documented exception
- ✅ Bash built-ins (if, for, while, functions, etc.)

**Prohibited**:
- ❌ External tools requiring installation (yq, xmllint, etc.)
- ❌ Language-specific tools (npm, pip, cargo) unless wrapper scripts

**Example** (stdlib-only):
```bash
#!/bin/bash
set -euo pipefail

FILE_PATH="${1:-}"

# ✅ Standard Unix utilities
LINE_COUNT=$(wc -l < "$FILE_PATH")
CONTENT=$(cat "$FILE_PATH")

# ✅ Bash built-ins and standard tools
if echo "$CONTENT" | grep -q "^---$"; then
    FRONTMATTER=$(awk '/^---$/{if(++count==2) exit; if(count==1) next} count==1' "$FILE_PATH")
fi

# ✅ jq for JSON output (documented exception)
echo "{\"line_count\": $LINE_COUNT}" | jq .
```

### Python Scripts

**Allowed**:
- ✅ Standard library modules (json, re, sys, os, pathlib, etc.)
- ✅ Built-in types and functions

**Prohibited**:
- ❌ pip packages (requests, pandas, numpy, etc.)
- ❌ Third-party libraries requiring installation

**Example** (stdlib-only):
```python
#!/usr/bin/env python3
"""Validates references in markdown files."""

import json
import re
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "File path required"}), file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    # ✅ Standard library only
    if not Path(file_path).is_file():
        print(json.dumps({"error": f"File not found: {file_path}"}), file=sys.stderr)
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # ✅ Standard library regex
    references = re.findall(r'Skill:\s*([a-z0-9:-]+)', content)

    # ✅ Standard library JSON
    result = {"file_path": file_path, "references": references}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
```

## JSON Output Format

**CRITICAL**: Scripts MUST output valid JSON (for machine parsing).

### Standard Format

**Success**:
```json
{
  "file_path": "input_file.md",
  "result_field_1": "value",
  "result_field_2": 123,
  "nested_object": {
    "field": "value"
  }
}
```

**Error**:
```json
{
  "error": "Clear error message"
}
```

### Output to stdout (Success) or stderr (Error)

**Success** (exit code 0):
```bash
echo '{
  "status": "success",
  "result": "data"
}' | jq .
exit 0
```

**Error** (exit code 1):
```bash
echo '{"error": "File not found"}' >&2
exit 1
```

## Executable Permissions

**CRITICAL**: Scripts MUST have executable permissions.

**Set Permissions**:
```bash
chmod +x scripts/script-name.sh
chmod +x scripts/script-name.py
```

**Verify**:
```bash
ls -l scripts/
# Should show: -rwxr-xr-x (executable flag set)
```

**Shebang Required**:
```bash
#!/bin/bash              # Shell scripts
#!/usr/bin/env python3   # Python scripts
```

## Error Handling

**CRITICAL**: Scripts MUST handle errors gracefully.

### Input Validation

```bash
#!/bin/bash
set -euo pipefail

FILE_PATH="${1:-}"

# Validate parameter provided
if [ -z "$FILE_PATH" ]; then
    echo '{"error": "File path required"}' >&2
    exit 1
fi

# Validate file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "{\"error\": \"File not found: $FILE_PATH\"}" >&2
    exit 1
fi

# Validate file readable
if [ ! -r "$FILE_PATH" ]; then
    echo "{\"error\": \"File not readable: $FILE_PATH\"}" >&2
    exit 1
fi
```

### Error Messages

**Format**: Clear, actionable error messages

**Good Examples**:
```json
{"error": "File not found: agents/missing.md"}
{"error": "Invalid component type. Expected: agent|command|skill, got: invalid"}
{"error": "JSON parsing failed at line 42: unexpected comma"}
```

**Bad Examples**:
```json
{"error": "Error"}  // Too vague
{"error": "Failed"}  // No context
{"error": "1"}  // Not descriptive
```

## Common Issues and Fixes

### Issue 1: Script Not Documented in SKILL.md

**Symptoms**:
- Script exists but not referenced in SKILL.md
- Users don't know script exists

**Diagnosis**:
```bash
# List scripts
ls {skill_dir}/scripts/

# Check SKILL.md references
Grep: pattern="scripts/", path="{skill_dir}/SKILL.md"
```

**Fix**:
Add script documentation to SKILL.md (see Documentation Requirements section).

### Issue 2: Missing Test File

**Symptoms**:
- No test file for script
- Untested script behavior

**Diagnosis**:
```bash
# Check for test file
ls test/{bundle}/{skill}/test-{script-name}.sh
```

**Fix**:
Create test file following Test File Structure template.

### Issue 3: No --help Support

**Symptoms**:
- Script fails with `--help` flag
- No usage documentation

**Diagnosis**:
```bash
python3 .plan/execute-script.py {bundle}:{skill} --help
# Should print help and exit 0
```

**Fix**:
Add help output handler (see Help Output Requirements section).

### Issue 4: External Dependencies

**Symptoms**:
- Script requires pip packages, npm modules, etc.
- Fails on systems without dependencies installed

**Diagnosis**:
```bash
# Shell scripts: Check for non-standard commands
grep -E "pip|npm|cargo|gem|composer" {script_path}

# Python scripts: Check for imports
grep -E "^import |^from .* import" {script_path}
# Verify all imports are stdlib
```

**Fix**:
Refactor to use stdlib-only (see Stdlib-Only Requirement section).

### Issue 5: Invalid JSON Output

**Symptoms**:
- JSON parsing fails
- Script output can't be processed

**Diagnosis**:
```bash
# Run script and validate JSON
{script_path} {args} | jq .
# If jq fails, JSON is invalid
```

**Fix**:
- Use `jq` for JSON generation in shell scripts
- Use `json.dumps()` in Python scripts
- Validate output with JSON parser

### Issue 6: Missing Executable Permissions

**Symptoms**:
- Script fails with "Permission denied"
- Cannot execute script

**Diagnosis**:
```bash
ls -l {script_path}
# Check for 'x' flag: -rwxr-xr-x
```

**Fix**:
```bash
chmod +x {script_path}
```

## Script Quality Checklist

**Before marking script as "quality approved"**:
- ✅ Documented in SKILL.md (purpose, input, output, usage)
- ✅ Test file exists and passes (`test-{script-name}.sh`)
- ✅ Supports `--help` flag (prints usage, exits 0)
- ✅ Stdlib-only (no external dependencies)
- ✅ JSON output format (valid, parseable)
- ✅ Executable permissions set (`chmod +x`)
- ✅ Error handling (validates inputs, graceful failures)
- ✅ Clear error messages (actionable, descriptive)
- ✅ Proper shebang (`#!/bin/bash` or `#!/usr/bin/env python3`)
- ✅ Exit codes (0 for success, 1 for error)

## Lessons Learned (Consolidated Best Practices)

Proven insights from developing marketplace scripts across multiple plans.

### Stdlib-Only Implementation Patterns

**PyYAML Replacement**:
Initial scripts often import `yaml` package. Replace with custom parser:

```python
def parse_simple_yaml(content):
    """Parse simple YAML frontmatter (key:value pairs only).

    Handles:
    - key: value pairs
    - Array syntax detection (validates but rejects [])
    - Improper indentation detection
    """
    result = {}
    for line in content.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result
```

**Key Insight**: Simple YAML parsing is sufficient for frontmatter - don't need full YAML library.

### Shell Script Pitfalls

**Counting with `set -euo pipefail`**:

❌ **Wrong** (causes duplicate output or failures):
```bash
set -euo pipefail
COUNT=$(grep -c "pattern" file || echo "0")  # Fallback runs even on success
```

✅ **Correct**:
```bash
set -euo pipefail
if [ -z "$VAR" ]; then
    COUNT=0
else
    COUNT=$(printf "%s" "$VAR" | wc -l)
fi
```

**Variable Construction - Newlines**:

❌ **Wrong** (literal string, not newline):
```bash
ITEMS="item1\nitem2"  # Creates literal "\n"
```

✅ **Correct** (actual newline):
```bash
ITEMS="item1"$'\n'"item2"  # Creates actual newline
```

**JSON Building with Pipes**:

❌ **Wrong** (trailing newline breaks JSON):
```bash
echo "$VAR" | jq -Rs .
```

✅ **Correct** (no trailing newline):
```bash
printf "%s" "$VAR" | jq -Rs .
```

**Frontmatter vs Content Analysis**:

Always separate frontmatter from body content to avoid false matches:

```bash
# Extract body only (skip frontmatter)
BODY=$(awk '/^---$/{if(++count==2) {getline; body=1}} body' "$FILE")
```

### Test-Driven Development

**Create test fixtures BEFORE implementation**:
1. Define expected inputs and outputs
2. Create fixture files for edge cases
3. Write test script skeleton
4. Implement script to pass tests

**Fixture Coverage**:
- Valid inputs (happy path)
- Invalid inputs (error handling)
- Edge cases (empty, malformed, boundary values)
- Rule violations (Rule 6, Rule 7, Pattern 22)

**Example fixture structure**:
```
test/{bundle}/{skill}/fixtures/{script-name}/
├── valid-input.md           # Happy path
├── invalid-frontmatter.md   # Error case
├── empty-file.md            # Edge case
├── agent-task-tool-prohibited.md  # Architectural rule
└── expected-output.json     # Expected results
```

### Script Architecture Patterns

**Handler Dictionary Pattern** (for multiple operation types):

```python
FIX_HANDLERS = {
    "missing_frontmatter": handle_missing_frontmatter,
    "invalid_yaml": handle_invalid_yaml,
    "unused_tools": handle_unused_tools,
    "rule_6_violation": handle_rule_6_violation,
}

def apply_fix(fix_type, file_path, **kwargs):
    handler = FIX_HANDLERS.get(fix_type)
    if not handler:
        return {"error": f"Unknown fix type: {fix_type}"}
    return handler(file_path, **kwargs)
```

**Backup Before Modify**:

```python
import shutil
from pathlib import Path

def apply_fix_with_backup(file_path, fix_func):
    backup_path = Path(file_path).with_suffix('.bak')
    shutil.copy2(file_path, backup_path)
    try:
        result = fix_func(file_path)
        backup_path.unlink()  # Remove backup on success
        return result
    except Exception as e:
        shutil.copy2(backup_path, file_path)  # Restore on failure
        backup_path.unlink()
        return {"error": str(e)}
```

### JSON Output Consistency

**Standard JSON Contract**:
```json
{
  "status": "success|error",
  "data": {
    "primary_result": "...",
    "secondary_info": []
  },
  "errors": [],
  "metrics": {
    "items_processed": 0,
    "duration_ms": 0
  }
}
```

**Script Chaining** (enabled by consistent JSON):
```bash
# Extract → Categorize → Apply → Verify (via fix.py subcommands)
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix extract --input file.md | \
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix categorize | \
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix apply | \
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix verify
```

### Validation Script Integration

**Architectural Rule Enforcement**:
Scripts should validate architectural rules automatically:

- **Rule 6**: Agents cannot use Task tool
- **Rule 7**: Only maven-builder can use Maven
- **Pattern 22**: Agents must report to caller, not self-invoke

```python
def check_rule_6(content, component_type):
    """Agents CANNOT use Task tool."""
    if component_type != "agent":
        return None
    if "Task" in extract_tools(content):
        return {
            "rule": "Rule 6",
            "severity": "error",
            "message": "Agents cannot use Task tool"
        }
    return None
```

### Proven Pattern Combinations

**Pattern 3 + Pattern 1** (Search-Analyze-Report + Script Automation):
- Scripts handle deterministic validation logic
- SKILL.md orchestrates workflows and interprets results
- JSON output enables structured reporting
- Successfully used across diagnose, fix, and maintain skills

**Key Benefits**:
- Easier testing (standard unit tests for scripts)
- Separation of concerns (logic vs orchestration)
- Portability (scripts work anywhere with Python/Bash)
- Chaining (JSON output enables pipeline processing)

## Summary

**Scripts are**:
- Deterministic validation logic
- Stdlib-only (portable, no dependencies)
- JSON output (machine-readable)
- Documented in SKILL.md
- Tested with test files
- Executable with --help support

**Scripts complement AI agents**:
- Agents: Context interpretation, reasoning, user interaction
- Scripts: Pattern matching, parsing, calculation, validation

**Quality = Documentation + Tests + Standards**
