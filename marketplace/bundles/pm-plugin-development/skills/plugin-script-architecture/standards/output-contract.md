# Output Contract Standards

Standards for script output format, exit codes, and error handling.

## Default Output Format: TOON

**TOON** (Token-Oriented Object Notation) is the default output format for marketplace scripts.

See `plan-marshall:toon-usage` skill for complete TOON specification.

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

| Code | Meaning | Output Stream |
|------|---------|---------------|
| `0` | Success | stdout |
| `1` | Error | stderr |

### Success Output (exit 0)

```python
import sys

# Success - output to stdout
print("status: success")
print("items_processed: 42")
sys.exit(0)
```

### Error Output (exit 1)

```python
import json
import sys

# Error - output to stderr
print(json.dumps({"error": "File not found: config.toon"}), file=sys.stderr)
sys.exit(1)
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
- [ ] Exit code 0 for success
- [ ] Exit code 1 for error
- [ ] Success output to stdout
- [ ] Error output to stderr
- [ ] Error messages are clear and actionable
- [ ] Includes relevant context in errors
- [ ] Status field present (`status: success|error`)
