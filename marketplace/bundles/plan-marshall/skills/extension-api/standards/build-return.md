# Build Return Structure

Specification for return values from build command execution.

## Purpose

Build commands return structured results that callers interpret uniformly. This spec defines the **core fields** all implementations must provide and **optional fields** for build-system-specific context.

## Return Structure

### Core Fields (Required)

All build command invocations must return these fields.

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Execution outcome: `success`, `error`, or `timeout` |
| `exit_code` | int | Process exit code (0=success, non-zero=error, -1=timeout/failure) |
| `duration_seconds` | int | Actual execution time in seconds |
| `log_file` | string | Path to captured output file |
| `command` | string | Full command that was executed |

**Status values**:
- `success` - Command completed with exit code 0
- `error` - Command failed (non-zero exit code) or execution failed
- `timeout` - Command exceeded timeout limit

### Error Context (Conditional)

Present when `status` is `error` or `timeout`.

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier (e.g., `build_failed`, `timeout`, `execution_failed`) |

### Parsed Issues (On Build Failure)

When a build fails, implementations **should** parse the log file and include structured issue data. The content varies based on `--mode` parameter.

| Field | Type | Description |
|-------|------|-------------|
| `errors` | list | Compilation/build errors extracted from log |
| `warnings` | list | Build warnings (filtered by mode) |
| `tests` | object | Test execution summary |

**Error entry structure**:
```
{file, line, message, category}
```

**Warning entry structure** (mode-dependent):
```
{file, line, message}           # actionable mode
{file, line, message, accepted} # structured mode
```

**Test summary structure**:
```
{passed, failed, skipped}
```

### Output Modes

The `--mode` parameter controls what issues are included in the output.

| Mode | Default | Description |
|------|---------|-------------|
| `actionable` | Yes | Filter out accepted warnings, show only actionable items |
| `structured` | No | Keep all warnings, mark accepted ones with `[accepted]` flag |
| `errors` | No | Only show errors, no warnings |

**Accepted warnings**: Warnings matching patterns in `.plan/run-configuration.json` under `maven.acceptable_warnings` or equivalent.

### Execution Metadata (Optional)

Build systems may include additional context for diagnostics.

| Field | Type | Scope | Description |
|-------|------|-------|-------------|
| `timeout_used_seconds` | int | All | Timeout that was applied |
| `wrapper` | string | Maven | Wrapper path used (e.g., `./mvnw`) |
| `command_type` | string | npm | Execution type: `npm` or `npx` |

## Format Examples

### TOON Format (Default)

```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/default/maven-2026-01-03-141523.log
command	./mvnw -l .plan/temp/build-output/... clean verify
```

Error case with parsed issues (`--mode actionable`):
```
status	error
exit_code	1
duration_seconds	23
log_file	.plan/temp/build-output/default/maven-2026-01-03-141530.log
command	./mvnw -l .plan/temp/build-output/... clean verify
error	build_failed

errors[2]{file,line,message,category}:
src/Main.java    15    cannot find symbol: class Foo    compilation
src/Test.java    42    test failed    test_failure

warnings[1]{file,line,message}:
pom.xml    -    deprecated dependency version    deprecation

tests:
  passed: 10
  failed: 2
  skipped: 1
```

Error case with `--mode structured` (shows accepted flag):
```
status	error
...
warnings[3]{file,line,message,accepted}:
pom.xml    -    deprecated dependency version
src/Util.java    10    unchecked cast    [accepted]
src/Helper.java    25    raw type usage    [accepted]
```

### JSON Format

```json
{
  "status": "success",
  "exit_code": 0,
  "duration_seconds": 45,
  "log_file": ".plan/temp/build-output/default/maven-2026-01-03-141523.log",
  "command": "./mvnw -l .plan/temp/build-output/... clean verify"
}
```

Error case with parsed issues:
```json
{
  "status": "error",
  "exit_code": 1,
  "duration_seconds": 23,
  "log_file": ".plan/temp/build-output/default/maven-2026-01-03-141530.log",
  "command": "./mvnw -l .plan/temp/build-output/... clean verify",
  "error": "build_failed",
  "errors": [
    {"file": "src/Main.java", "line": 15, "message": "cannot find symbol: class Foo", "category": "compilation"},
    {"file": "src/Test.java", "line": 42, "message": "test failed", "category": "test_failure"}
  ],
  "warnings": [
    {"file": "pom.xml", "line": null, "message": "deprecated dependency version"}
  ],
  "tests": {
    "passed": 10,
    "failed": 2,
    "skipped": 1
  }
}
```

## Exit Code Semantics

| Exit Code | Status | Meaning |
|-----------|--------|---------|
| 0 | `success` | Build completed successfully |
| 1+ | `error` | Build failed (compilation error, test failure, etc.) |
| -1 | `error` | Execution failed (wrapper not found, log creation failed) |
| -1 | `timeout` | Build exceeded timeout |

**Note**: Exit code -1 indicates the build system never ran or was interrupted. Check `status` to distinguish between execution failure and timeout.

## Caller Interpretation

### Basic Success/Failure Check

```python
result = run_build(...)

if result['status'] == 'success':
    # Build passed
    pass
elif result['status'] == 'timeout':
    # Consider increasing timeout
    print(f"Timed out after {result.get('timeout_used_seconds', 'unknown')}s")
else:
    # Build failed - check log file for details
    print(f"See: {result['log_file']}")
```

### Log File Analysis

On failure, callers should read `log_file` for detailed error analysis:

```python
if result['status'] == 'error':
    log_content = Path(result['log_file']).read_text()
    issues = parse_build_output(log_content)
```

## Design Rationale

### Why Seconds Not Milliseconds

Duration uses seconds because:
- Matches timeout parameter units
- Human-readable for interactive output
- Build durations rarely need millisecond precision

### Why Flat Structure Not Nested

Core fields are at the top level (not nested in `data`) because:
- Simpler parsing in both TOON and JSON formats
- Status check doesn't require traversing structure
- TOON format naturally maps to flat key-value pairs

### Why Log File Not stdout/stderr

Output goes to log file (not captured to memory) because:
- Build output can be megabytes (verbose mode, many modules)
- Memory capture would bloat conversation context
- Log files persist for debugging failed builds
- Consistent location pattern enables automation

## Compliance

Implementations must:
- [ ] Return all 5 core fields on every invocation
- [ ] Use `duration_seconds` (not milliseconds)
- [ ] Use `command` (not `command_executed`)
- [ ] Include `error` field when status is not `success`
- [ ] Use TOON tab-separated format: `key\tvalue` (not colon-separated)
- [ ] Support both TOON and JSON via `--format` parameter
- [ ] Support `--mode` parameter with `actionable`, `structured`, `errors` values
- [ ] Parse and include `errors`, `warnings`, `tests` on build failure
- [ ] Filter warnings based on mode and acceptable patterns

## Related Specifications

- [build-execution.md](build-execution.md) - Command execution API
- [build-project-structure.md](build-project-structure.md) - Project structure discovery
- [canonical-commands.md](canonical-commands.md) - Standard command vocabulary
