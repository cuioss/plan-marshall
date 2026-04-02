---
name: build-gradle
description: Gradle build operations with execution, parsing, and module discovery
user-invocable: false
---

# Build Gradle

Gradle build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke Gradle directly; all builds go through the script API
- Do not invent script arguments not listed in the operations table
- Do not bypass wrapper detection logic

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-gradle:gradle {command} {args}`
- Output format defaults to TOON; use `--format json` only when explicitly required
- Always analyze the result TOON: check `status` for success/error/timeout, review `errors` for failures

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `gradle.py` | CLI | Gradle operations dispatcher (includes coverage + warning config) |
| `_gradle_execute.py` | Library | Execution config via factory pattern |
| `_gradle_cmd_discover.py` | Library | Module discovery via build.gradle |
| `_gradle_cmd_parse.py` | Library | Log parsing, issue extraction (uses shared categorizer) |
| `_gradle_cmd_find_project.py` | Library | Gradle subproject location |

Shared infrastructure from `extension-api`: `_build_execute_factory.py`, `_build_shared.py`, `_build_parse.py`, `_build_coverage_report.py`, `_build_check_warnings.py`.

## Unified API

All build skills share the same subcommand structure. Gradle supports all subcommands:

| Subcommand | Purpose |
|------------|---------|
| `run` | Execute build and auto-parse on failure (primary API) |
| `parse` | Parse Gradle build output from log file |
| `coverage-report` | Parse JaCoCo coverage report |
| `check-warnings` | Categorize build warnings against acceptable patterns |
| `search-markers` | Search OpenRewrite TODO markers in source files |
| `discover` | Discover Gradle modules with metadata |
| `find-project` | Find Gradle subproject path from name |

### run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run \
    --command-args "<tasks>" \
    [--timeout <seconds>] \
    [--mode <mode>] \
    [--format <toon|json>]
```

**Parameters**:
- `--command-args` - Complete Gradle command arguments, e.g. `":module:build"` or `"build"` (required)
- `--timeout` - Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)
- `--mode` - Output mode: actionable (default), structured, errors
- `--format` - Output format: toon (default), json
- `--project-dir` - Project root directory (default: `.`)

**Output Format (TOON)**:

Success:
```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/default/gradle-2026-01-04-143022.log
command	./gradlew --console=plain build
```

Build Failed:
```
status	error
exit_code	1
duration_seconds	23
log_file	.plan/temp/build-output/default/gradle-2026-01-04-143022.log
command	./gradlew --console=plain :core:build
error	build_failed

errors[2]{file,line,message,category}:
src/main/java/Foo.java    42    cannot find symbol       compilation_error
src/main/java/Bar.java    15    test assertion failed    test_failure

tests:
  passed: 40
  failed: 2
  skipped: 1
```

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle parse \
    --log <path> [--mode <mode>]
```

**Parameters**:
- `--log` - Path to Gradle build log file (required)
- `--mode` - Output mode (default: `structured`):
  - `default` - All issues, unfiltered
  - `errors` - Only error-severity issues
  - `structured` - All issues with structured summary
  - `no-openrewrite` - Exclude OpenRewrite informational messages

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle coverage-report \
    [--project-path <path>] \
    [--report-path <path>] \
    [--threshold <percent>]
```

**Parameters**:
- `--project-path` - Module directory path (for multi-project builds)
- `--report-path` - Override JaCoCo XML report path (default: auto-detect in build/)
- `--threshold` - Coverage threshold percent (default: 80)

**Output Format (TOON)**:

```
status	success
passed	true
threshold	80
message	"Coverage meets threshold: 85.2% line, 78.3% branch"

overall:
  line	85.2
  branch	78.3
  instruction	81.5
  method	87.1

low_coverage[1]{class,line_pct,missed_methods}:
  com.example.service.UserService,68.5,deleteUser
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle check-warnings \
    --warnings <json> [--acceptable-warnings <json>]
```

**Parameters**:
- `--warnings` - JSON array of warnings
- `--acceptable-warnings` - JSON object with acceptable patterns

### search-markers

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle search-markers \
    --source-dir <dir> [--extensions <ext>]
```

**Parameters**:
- `--source-dir` - Directory to search (default: src)
- `--extensions` - Comma-separated file extensions (default: .java,.kt)

**Note**: Available in Maven and Gradle builds only (OpenRewrite integration).

### find-project

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle find-project \
    --project-name <name> | --project-path <path>
```

**Parameters** (mutually exclusive):
- `--project-name` - Project name to search for
- `--project-path` - Explicit project path to validate
- `--root` - Project root directory (default: .)

**Note**: This subcommand is Gradle-specific. Maven uses `-pl {module}` directly.

### discover

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle discover \
    [--root <path>] [--format <toon|json>]
```

**Parameters**:
- `--root` - Project root directory (default: `.`)
- `--format` - Output format: toon (default), json

**Output Format (TOON)**:

```
status	success
count	3

modules[3]{name,build_systems,paths,metadata,packages,stats,commands}:
  auth-service	["gradle"]	{module: "auth-service", descriptor: "services/auth-service/build.gradle", ...}	{group: "com.example", name: "auth-service", ...}	{...}	{source_files: 15, test_files: 8}	{verify: ":auth-service:build", compile: ":auth-service:compileJava", ...}
```

Each module includes: `name`, `build_systems`, `paths` (module/descriptor/sources/tests/readme), `metadata` (group/name/version/description/dependencies), `packages`, `test_packages`, `stats` (source_files/test_files), `commands` (canonical build commands).

## Wrapper Detection

```
Gradle: ./gradlew > gradle (on PATH)
```

## Error Categories

Categories use **regex patterns** for Gradle's task-specific markers (e.g., `Execution failed for task ':.*:compileJava'`). The shared `categorize_issue()` function auto-detects regex metacharacters and switches matching mode accordingly. Deduplication uses the shared `make_dedup_key()` format: `{category}:{file}:{line}:{message[:100]}`.

| Category | Description |
|----------|-------------|
| `compilation_error` | Compile-time Java/Kotlin errors (includes Kotlin-specific: `Unresolved reference`, `Type mismatch`, `Smart cast` failures) |
| `test_failure` | Test assertion failures |
| `dependency_error` | Dependency resolution issues |
| `javadoc_warning` | JavaDoc documentation issues |
| `deprecation_warning` | Deprecated API usage |
| `unchecked_warning` | Unchecked type conversions |
| `openrewrite_info` | OpenRewrite plugin output |

## Module Discovery

Gradle module discovery reads `settings.gradle(.kts)` to detect multi-project builds. Subprojects are identified from `include()` declarations. Discovery uses shared utilities from the extension API for source directories, package scanning, and file counting (at parity with Maven discovery).

### Command Generation

Discovery generates canonical commands per subproject:

| Canonical | Gradle Command |
|-----------|----------------|
| `verify` | `:module:build` |
| `quality-gate` | `:module:check` |
| `compile` | `:module:compileJava` |
| `module-tests` | `:module:test` |
| `coverage` | `:module:test :module:jacocoTestReport` |
| `clean` | `clean` |

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/gradle-impl.md` - Gradle execution details
