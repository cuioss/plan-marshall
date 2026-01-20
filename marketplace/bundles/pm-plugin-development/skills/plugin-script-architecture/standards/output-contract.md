# Output Contract Standards

Standards for script output format, exit codes, and error handling.

## Default Output Format: TOON

**TOON** (Token-Oriented Object Notation) is the default output format for marketplace scripts.

See `plan-marshall:ref-toon-format` skill for complete TOON specification.

### TOON Structure

**Header Row + Data Rows** (tab-separated):

```toon
issues[3]{file,line,severity}:
Example.java	42	BLOCKER
Service.java	89	MAJOR
Config.java	15	MINOR
```

### When to Use TOON

Use TOON for:
- Uniform arrays (lists of similar items)
- Tabular data (tables, grids)
- Agent handoffs
- Build output summaries

### Multi-Table Output

```toon
status: success
files_processed: 15

issues[2]{file,line,severity}:
Example.java	42	BLOCKER
Service.java	89	MAJOR

recommendations[3]{priority,action}:
HIGH	Fix BLOCKER issues first
MEDIUM	Update deprecated APIs
LOW	Add missing tests
```

### When JSON is Acceptable

Use JSON instead of TOON only for:
- Complex nested structures (>3 levels deep)
- Non-uniform object shapes
- API interchange with external tools
- Configuration output

## Exit Codes

Exit codes indicate whether the **script executed successfully**, not whether the operation succeeded.

| Code | Meaning | When to Use |
|------|---------|-------------|
| `0` | Script completed | Operation success OR failure (check `status` field) |
| `1` | Script error | Crash, missing required file, permission denied |
| `2` | Invalid arguments | argparse validation failure (automatic) |

**Key principle**: If the script ran and produced a meaningful result (even "not found" or "validation failed"), exit 0. Only exit non-zero for actual execution errors.

### Operation Success (exit 0, status: success)

```python
import sys

# Operation succeeded
print("status: success")
print("items_processed: 42")
sys.exit(0)
```

### Operation Failure (exit 0, status: error)

```python
import sys

# Operation failed but script ran successfully
# Example: item not found, validation failed, requires --force
print("status: error")
print("error: Task not found: TASK-999")
print("plan_id: my-plan")
sys.exit(0)  # Exit 0 - status is in output
```

### Script Execution Error (exit 1)

```python
import sys

# Real error - script cannot execute properly
# Example: required file missing, permission denied, crash
try:
    config = load_required_config()
except FileNotFoundError:
    print("error: Required config file not found", file=sys.stderr)
    sys.exit(1)  # Exit 1 - script couldn't run
```

## Error Message Format

### TOON Error Format

```toon
status: error
error: Clear error message here
context: Additional context if helpful
```

### JSON Error Format (Alternative)

```json
{
  "error": "Clear error message describing what went wrong",
  "context": {
    "file": "path/to/file.md",
    "line": 42
  }
}
```

### Error Message Guidelines

**Good Examples**:
```
error: Plan not found: my-plan
error: Invalid key format. Expected: lowercase with underscores, got: MyKey
error: Config file parsing failed at line 42: unexpected character
```

**Bad Examples**:
```
error: Error
error: Failed
error: 1
```

## Standard Output Contract

For scripts returning structured data:

```toon
status: success|error
{operation_specific_fields}

{optional_tables}
```

### Example: List Operation

```toon
status: success
count: 3

items[3]{id,name,status}:
TASK-001	Implement feature	in_progress
TASK-002	Write tests	pending
TASK-003	Update docs	pending
```

### Example: Get Operation

```toon
status: success
id: TASK-001
name: Implement feature
status: in_progress
created: 2025-01-15
```

### Example: Create Operation

```toon
status: success
created: TASK-004
path: .plan/plans/my-plan/tasks/TASK-004.toon
```

### Example: Error Response

```toon
status: error
error: Task not found: TASK-999
plan_id: my-plan
```

## Script Chaining

TOON output enables pipeline processing:

```bash
# Extract → Categorize → Apply → Verify
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix extract --input file.md | \
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix categorize | \
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix apply
```

## Output Quality Checklist

Before marking output as compliant:

- [ ] Uses TOON format (unless complex nesting required)
- [ ] Exit code 0 when script completes (success OR operation failure)
- [ ] Exit code 1 only for script execution errors (crash, missing required file)
- [ ] Status field present (`status: success|error`) in output
- [ ] Operation failures use `status: error` with exit 0, not exit 1
- [ ] Error messages are clear and actionable
- [ ] Includes relevant context in errors
