# Build Execution API

Specification for build command execution in domain extensions. This document covers the **execution contract** (input/output fields, lifecycle, format specs). For subcommand documentation and error categories, see `build-api-reference.md`. For timeouts and log handling standards, see `build-systems-common.md`.

## Purpose

Domain bundles that provide build capabilities expose a **unified execution API** that:
- Captures all output to a log file (not stdout/stderr)
- Provides adaptive timeout learning
- Returns structured results for caller interpretation

Build commands return structured results that callers interpret uniformly. This spec defines the **core fields** all implementations must provide and **optional fields** for build-system-specific context.

## Execution Contract

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--command-args` | string | Yes | Complete build arguments with all routing embedded |
| `--format` | string | No | Output format: `toon` (default) or `json` |
| `--mode` | string | No | Content mode: `actionable` (default), `structured`, or `errors` |
| `--timeout` | int | No | Timeout in seconds (default: 300) |

**Key principle**: The `--command-args` string is **complete and self-contained**. All build-specific options (modules, profiles, workspaces) are embedded in this string. No external composition needed at execution time.

**Build-system routing examples**:

| Build System | Example `--command-args` | Routing Mechanism |
|--------------|-------------------------|-------------------|
| Maven | `"verify -Ppre-commit -pl oauth-sheriff-core"` | `-pl module` flag |
| Gradle | `":api-genshin-impact:build"` | `:module:task` prefix |
| npm (workspace) | `"test --workspace=packages/app"` | `--workspace=path` flag |
| npm (prefix) | `"--prefix nifi-cuioss-ui test"` | `--prefix path` flag |

**Mode values**:
- `actionable` - Filter out accepted warnings, show only actionable items (default)
- `structured` - Keep all warnings, mark accepted ones with `[accepted]` flag
- `errors` - Only show errors, no warnings

### Output

Both formats return the same fields; only the serialization differs.

#### Core Fields (Required)

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

#### Error Context (Conditional)

Present when `status` is `error` or `timeout`.

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error type identifier (e.g., `build_failed`, `timeout`, `execution_failed`) |

#### Parsed Issues (On Build Failure)

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

#### Output Modes

The `--mode` parameter controls what issues are included in the output.

| Mode | Default | Description |
|------|---------|-------------|
| `actionable` | Yes | Filter out accepted warnings, show only actionable items |
| `structured` | No | Keep all warnings, mark accepted ones with `[accepted]` flag |
| `errors` | No | Only show errors, no warnings |

**Accepted warnings**: Warnings matching patterns in `.plan/run-configuration.json` under `maven.acceptable_warnings` or equivalent.

#### Execution Metadata (Optional)

Build systems may include additional context for diagnostics.

| Field | Type | Scope | Description |
|-------|------|-------|-------------|
| `timeout_used_seconds` | int | All | Timeout that was applied |
| `wrapper` | string | Maven, Python | Wrapper path used (e.g., `./mvnw`, `./pw`) |
| `command_type` | string | npm | Execution type: `npm` or `npx` |

#### Dynamic Result Fields (Implementation Detail)

Build systems using the factory API can inject additional fields into results. See `_build_execute_factory.py::ExecuteConfig` for `extra_result_fields` and `extra_result_fn` parameters.

## Requirements

### R1: Log File Output

All build output **must** go to a log file, not stdout/stderr.

**Rationale**: Build tools produce verbose output that clutters conversation context. Log files allow:
- Full output available for error analysis
- Compact result returned to caller
- Persistent record for debugging

**Log file location**: `.plan/temp/build-output/{scope}/{build-system}-{timestamp}.log`

| Component | Values | Example |
|-----------|--------|---------|
| `{scope}` | `default` (root) or module name | `default`, `core-api` |
| `{build-system}` | `maven`, `gradle`, `npm` | `maven` |
| `{timestamp}` | `YYYY-MM-DD-HHMMSS` | `2026-01-03-141523` |

**Examples**:
- `.plan/temp/build-output/default/maven-2026-01-03-141523.log` - root Maven build
- `.plan/temp/build-output/core-api/maven-2026-01-03-141530.log` - module build
- `.plan/temp/build-output/default/npm-2026-01-03-141545.log` - npm build

Using `.plan/temp/` ensures:
- Already gitignored
- Part of temp cleanup maintenance
- Module-scoped logs easy to find
- Build system clearly identified

### R2: Wrapper Preference

Extensions **must** prefer project-local wrappers over system installations.

| Build System | Wrapper Priority |
|--------------|------------------|
| Maven | `./mvnw` → `mvn` |
| Gradle | `./gradlew` → `gradle` |
| npm | `npx` → `npm` |

**Rationale**: Project wrappers ensure consistent versions across environments.

### R3: Timeout Learning

Extensions **must** integrate with `run_config` for adaptive timeouts.

**Storage**: `.plan/run-configuration.json`
```json
{
  "commands": {
    "maven:clean_verify": { "timeout_seconds": 180 },
    "npm:test": { "timeout_seconds": 45 }
  }
}
```

**Python API** (import from `plan-marshall:manage-run-config`):

```python
from run_config import timeout_get, timeout_set

# Before execution: get timeout to use
timeout = timeout_get(
    command_key="maven:clean_verify",  # Identifier for this command
    default=300,                        # Default if no learned value
    project_dir="."                     # Project root
)
# Returns: default (first run) or learned * 1.25 (subsequent runs)

# After execution: record actual duration
timeout_set(
    command_key="maven:clean_verify",
    duration=165,                       # Actual execution time
    project_dir="."
)
# Updates learned value with weighted average (80% higher, 20% lower)
```

**Algorithm**:
- `timeout_get`: Returns `persisted * 1.25` (safety margin) or default if none
- `timeout_set`: Computes `0.80 * max(existing, new) + 0.20 * min(existing, new)`

**CLI** (via execute-script):
```bash
# Get timeout
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  timeout get --command "maven:verify" --default 300

# Set timeout
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  timeout set --command "maven:verify" --duration 165
```

## CLI Interface

Extensions expose a single `run` subcommand with format and mode selection:

```bash
python3 .plan/execute-script.py {bundle}:build-{tool}:{script} run \
  --command-args "verify -pl core-api" \
  --format toon \             # or --format json
  --mode actionable           # or --mode structured, --mode errors
```

### R4: Dual Format Support

Implementations **must** support both output formats via `--format` parameter:

| Format | Default | Use Case |
|--------|---------|----------|
| `toon` | Yes | Interactive agent builds, human-readable |
| `json` | No | Script integration, programmatic parsing |

**Testing requirement**: Each implementation must have tests verifying both formats produce equivalent data.

### R5: Content Mode Support

Implementations **must** support content filtering via `--mode` parameter:

| Mode | Default | Use Case |
|------|---------|----------|
| `actionable` | Yes | Focus on issues requiring action, filter accepted warnings |
| `structured` | No | Full diagnostics with acceptance status for analysis |
| `errors` | No | Errors only, minimal output for CI pipelines |

**Accepted warnings**: Patterns configured in `.plan/run-configuration.json` under `{build_system}.acceptable_warnings`.

## Invocation Patterns

### From Aggregated Output

The orchestrator resolves commands per module in `.plan/project-architecture/derived-data.json`. Each command is **complete** with all routing embedded:

```json
{
  "modules": {
    "oauth-sheriff-core": {
      "commands": {
        "module-tests": "python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args \"test -pl oauth-sheriff-core\"",
        "verify": "python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args \"verify -pl oauth-sheriff-core\"",
        "quality-gate": "python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args \"verify -Ppre-commit -pl oauth-sheriff-core\""
      }
    }
  }
}
```

### From discover_modules()

Extensions generate complete commands per module during discovery:

```python
def _build_commands(module_name: str, profiles: list) -> dict:
    base = "python3 .plan/execute-script.py plan-marshall:build-maven:maven run"
    pl_arg = f" -pl {module_name}" if module_name != "." else ""

    commands = {
        "clean": f'{base} --command-args "clean{pl_arg}"',
        "verify": f'{base} --command-args "verify{pl_arg}"',
        "module-tests": f'{base} --command-args "test{pl_arg}"',
    }

    # Add profile-based commands
    for profile in profiles:
        if profile["canonical"] == "quality-gate":
            commands["quality-gate"] = f'{base} --command-args "verify -P{profile["id"]}{pl_arg}"'

    return commands
```

**Key principle**: Commands are generated **once** during discovery with all routing embedded. No placeholders, no runtime composition.

### Interactive (agents)

```bash
# Default TOON output for interactive use (actionable mode)
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "verify -Ppre-commit -pl core-api"

# JSON output for script integration
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "verify" --format json

# Structured mode for full diagnostics (shows all warnings with acceptance status)
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "verify" --mode structured

# Errors-only mode for CI pipelines
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "verify" --mode errors --format json

# Gradle example with module routing
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run \
  --command-args ":api-genshin-impact:build"

# npm example with workspace routing
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
  --command-args "test --workspace=packages/app"
```

## Direct Execution API

For module discovery and other non-interactive build operations, extensions use `execute_direct()` from their `{build_system}_execute.py` module.

### Python API

```python
from maven_execute import execute_direct  # or gradle_execute, npm_execute
from build_result import DirectCommandResult

result: DirectCommandResult = execute_direct(
    args="help:all-profiles dependency:tree -DoutputType=text",
    command_key="maven:discover-modules",
    default_timeout=120,
    project_dir="."
)

if result["status"] == "success":
    log_content = Path(result["log_file"]).read_text()
    # Parse log content...
```

### Parameters

All `execute_direct()` implementations use this **minimal, unified signature**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `args` | string | Yes | - | Complete build arguments (all routing embedded) |
| `command_key` | string | Yes | - | Key for timeout learning (e.g., `"maven:verify"`) |
| `default_timeout` | int | No | 300 | Default timeout in seconds |
| `project_dir` | string | No | `.` | Project root directory |

**Key principle**: The `args` parameter contains **all** build-specific options. No separate parameters for modules, profiles, workspaces, or wrappers. Wrappers are auto-detected internally.

### Return Value: DirectCommandResult

All `execute_direct()` implementations return `DirectCommandResult` (TypedDict from `build_result.py`):

**Required fields** (always present):

| Field | Type | Description |
|-------|------|-------------|
| `status` | `Literal["success", "error", "timeout"]` | Execution outcome |
| `exit_code` | int | Process exit code (-1 for timeout/failure) |
| `duration_seconds` | int | Actual execution time |
| `log_file` | string | Path to captured output (R1 requirement) |
| `command` | string | Full command executed |

**Optional fields** (present when applicable):

| Field | Type | Description |
|-------|------|-------------|
| `timeout_used_seconds` | int | Timeout that was applied |
| `error` | string | Error message (on error/timeout only) |

### Implementation

Each domain bundle provides its own `{build_system}_execute.py` module that:
- Detects and uses project wrappers (R2)
- Creates log files per R1
- Integrates with timeout learning (R3)
- Returns `DirectCommandResult` structure

Location: inside the `build-{tool}` skill directory, under a `scripts` subdirectory, as `_{build_system}_execute.py`.

| Build System | Module |
|--------------|--------|
| Maven | `maven_execute.py` |
| Gradle | `gradle_execute.py` |
| npm | `npm_execute.py` |

Import the TypedDict for type hints:
```python
from build_result import DirectCommandResult

def execute_direct(...) -> DirectCommandResult:
    ...
```

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

## Execution Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUILD EXECUTION LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. COMMAND RESOLUTION                                                       │
│     architecture.py resolve --command verify --name my-module                │
│     → Complete command string with all routing embedded                      │
│                              │                                               │
│                              ▼                                               │
│  2. EXECUTION (execute_direct)                                               │
│     a. create_log_file(build_system, scope, project_dir)                    │
│     b. timeout_get(command_key, default, project_dir)                       │
│     c. detect_wrapper(project_dir)                                          │
│     d. subprocess.run(cmd, timeout=timeout, cwd=project_dir)               │
│     e. timeout_set(command_key, actual_duration, project_dir)               │
│                              │                                               │
│              ┌───────────────┼───────────────┐                               │
│              ▼               ▼               ▼                               │
│        [exit_code=0]    [exit_code>0]    [TimeoutExpired]                   │
│                                                                              │
│  3. RESULT HANDLING                                                          │
│     success_result()    parse_log() →     timeout_result()                  │
│                         partition_issues()                                   │
│                         filter_warnings()                                   │
│                         error_result()                                      │
│                              │                                               │
│  4. OUTPUT FORMATTING                                                        │
│     format_toon(result)  or  format_json(result)                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Persistence Points

| File | Owner | Content |
|------|-------|---------|
| `.plan/project-architecture/derived-data.json` | manage-architecture | Discovered modules with command strings |
| `.plan/run-configuration.json` | run-config | Learned timeouts, acceptable warnings |
| `.plan/temp/build-output/{scope}/{system}-{ts}.log` | build scripts | Raw build output (timestamped) |

## Error Handling

See [Exit Code Semantics](#exit-code-semantics) above for the status/exit-code mapping.

## Compliance

Extensions providing build commands must:

- Capture output to log file (R1)
- Prefer project wrappers over system commands (R2)
- Integrate with timeout learning (R3)
- Support `--format toon` and `--format json` (R4)
- Support `--mode actionable`, `structured`, `errors` (R5)
- Return all 5 core fields on every invocation
- Return `log_file` path in all results
- Use `duration_seconds` (not milliseconds)
- Use `command` (not `command_executed`)
- Include `error` field when status is not `success`
- Use TOON tab-separated format: `key\tvalue` (not colon-separated)
- Parse and return structured `errors`, `warnings`, `tests` on build failure
- Filter warnings based on mode and acceptable patterns
- Have tests for both output formats and all modes

## Related Specifications

- [extension-contract.md](extension-contract.md) - Extension API contract
- [canonical-commands.md](canonical-commands.md) - Command vocabulary
- [module-discovery.md](module-discovery.md) - Project structure discovery
