---
name: build-maven
description: Maven build operations with execution, parsing, and module discovery
user-invocable: false
---

# Build Maven

Maven build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke Maven directly; all builds go through the script API
- Do not invent script arguments not listed in the operations table
- Do not bypass wrapper detection logic

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-maven:maven {command} {args}`
- Output format defaults to TOON; use `--format json` only when explicitly required
- Always analyze the result TOON: check `status` for success/error/timeout, review `errors` for failures

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `maven.py` | CLI | Maven operations dispatcher (includes coverage + warning config) |
| `_maven_execute.py` | Library | Execution config via factory pattern |
| `_maven_cmd_discover.py` | Library | Module discovery via pom.xml |
| `_maven_cmd_parse.py` | Library | Log parsing, issue extraction (uses shared categorizer) |

## Unified API

All build skills share the same subcommand structure. Maven supports all subcommands:

| Subcommand | Purpose |
|------------|---------|
| `run` | Execute build and auto-parse on failure (primary API) |
| `parse` | Parse build output from log file |
| `coverage-report` | Parse JaCoCo coverage report |
| `check-warnings` | Categorize build warnings against acceptable patterns |
| `search-markers` | Search OpenRewrite TODO markers in source files |

### run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
    --command-args "<goals>" \
    [--timeout <seconds>] \
    [--mode <mode>] \
    [--format <toon|json>]
```

**Parameters**:
- `--command-args` - Complete Maven command arguments, e.g. `"verify -Ppre-commit -pl my-module"` (required)
- `--timeout` - Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)
- `--mode` - Output mode: actionable (default), structured, errors
- `--format` - Output format: toon (default), json

**Output Format (TOON)**:

Success:
```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/default/maven-2026-01-04-143022.log
command	./mvnw -l .plan/temp/build-output/... clean test -pl core
```

Build Failed:
```
status	error
exit_code	1
duration_seconds	23
log_file	.plan/temp/build-output/default/maven-2026-01-04-143022.log
command	./mvnw -l .plan/temp/build-output/... clean test
error	build_failed

errors[2]{file,line,message,category}:
src/main/java/Foo.java    42    cannot find symbol       compile
src/main/java/Bar.java    15    null pointer             test

tests:
  passed: 40
  failed: 2
  skipped: 1
```

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven parse \
    --log <path> [--mode <mode>]
```

**Parameters**:
- `--log` - Path to Maven build log file (required)
- `--mode` - Output mode: default, errors, structured (default), no-openrewrite

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven coverage-report \
    [--project-path <path>] \
    [--report-path <path>] \
    [--threshold <percent>]
```

**Parameters**:
- `--project-path` - Module directory path (for multi-module projects)
- `--report-path` - Override JaCoCo XML report path (default: auto-detect in target/)
- `--threshold` - Coverage threshold percent (default: 80)

**Output Format (TOON)**:

```
status	success
passed	true
threshold	80
message	"Coverage meets threshold: 82.4% line, 75.0% branch"

overall:
  line	82.35
  branch	75.0
  instruction	79.69
  method	83.33

low_coverage[1]{class,line_pct,missed_methods}:
  de.cuioss.portal.sample.UserService,66.67,deleteUser
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven check-warnings \
    --warnings <json> [--acceptable-warnings <json>]
```

**Parameters**:
- `--warnings` - JSON array of warning objects
- `--acceptable-warnings` - JSON object with acceptable patterns

### search-markers

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven search-markers \
    --source-dir <dir> [--extensions <ext>]
```

**Parameters**:
- `--source-dir` - Directory to search (default: src)
- `--extensions` - Comma-separated file extensions (default: .java)

**Note**: This subcommand is specific to Maven and Gradle (OpenRewrite integration). Not available in npm or Python builds.

## Wrapper Detection

```
Maven:  ./mvnw > mvn (on PATH)
```

## Error Categories

Categories use **substring matching** (case-insensitive). The shared `categorize_issue()` function auto-detects regex metacharacters, but Maven patterns are plain substrings for simplicity.

| Category | Description |
|----------|-------------|
| `compilation_error` | Compile-time Java errors |
| `test_failure` | Test assertion failures |
| `dependency_error` | Dependency resolution issues |
| `javadoc_warning` | JavaDoc documentation issues |
| `deprecation_warning` | Deprecated API usage |
| `unchecked_warning` | Unchecked type conversions |
| `openrewrite_info` | OpenRewrite plugin output |

## Module Discovery

Maven module discovery reads `pom.xml` to detect multi-module projects. Modules are identified from `<modules>` declarations in the parent POM.

### Command Generation

Discovery generates canonical commands per module:

| Canonical | Maven Command |
|-----------|---------------|
| `verify` | `verify -pl {module}` |
| `quality-gate` | `-Ppre-commit verify -pl {module}` |
| `compile` | `compile -pl {module}` |
| `module-tests` | `test -pl {module}` |
| `coverage` | `-Pcoverage verify -pl {module}` |
| `clean` | `clean` |

Profile-to-canonical mappings are configurable via extension defaults.

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/maven-impl.md` - Maven execution details
- `standards/pom-maintenance.md` - POM structure and dependency management standards
