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
    [--format <toon|json>] \
    [--timeout <seconds>] \
    [--mode <mode>]
```

**Parameters**:
- `--command-args` - Complete Gradle command arguments, e.g. `":module:build"` or `"build"` (required)
- `--format` - Output format: toon (default), json
- `--timeout` - Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)
- `--mode` - Output mode: actionable (default), structured, errors

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
- `--mode` - Output mode: default, errors, structured (default)

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

**Note**: This subcommand is specific to Maven and Gradle (OpenRewrite integration). Not available in npm or Python builds.

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

## Wrapper Detection

```
Gradle: ./gradlew > gradle (on PATH)
```

## Error Categories

Categories use **regex patterns** for Gradle's task-specific markers (e.g., `Execution failed for task ':.*:compileJava'`). The shared `categorize_issue()` function auto-detects regex metacharacters and switches matching mode accordingly.

| Category | Description |
|----------|-------------|
| `compilation_error` | Compile-time Java/Kotlin errors |
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
| `clean` | `clean` |

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/gradle-impl.md` - Gradle execution details
