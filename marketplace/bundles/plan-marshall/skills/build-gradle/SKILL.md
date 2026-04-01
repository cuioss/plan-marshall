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
| `_gradle_cmd_parse.py` | Library | Log parsing, issue extraction |
| `_gradle_cmd_find_project.py` | Library | Gradle subproject location |

## Gradle run (Primary API)

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

### Coverage Report

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle coverage-report \
    [--module-path <path>] \
    [--report-path <path>] \
    [--threshold <percent>]
```

**Parameters**:
- `--module-path` - Module directory path (for multi-project builds)
- `--report-path` - Override JaCoCo XML report path (default: auto-detect in build/)
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

### Low-level Operations

| Command | Purpose |
|---------|---------|
| `gradle parse` | Parse Gradle build output |
| `gradle find-project` | Find Gradle subproject |
| `gradle search-markers` | Search markers in Gradle project |
| `gradle check-warnings` | Check Gradle warnings |
| `gradle coverage-report` | Parse JaCoCo coverage report |

## Wrapper Detection

```
Gradle: ./gradlew > gradle (on PATH)
```

## Error Categories

| Category | Description |
|----------|-------------|
| `compilation_error` | Compile-time Java/Kotlin errors |
| `test_failure` | Test assertion failures |
| `dependency_error` | Dependency resolution issues |
| `javadoc_warning` | JavaDoc documentation issues |
| `deprecation_warning` | Deprecated API usage |
| `unchecked_warning` | Unchecked type conversions |
| `openrewrite_info` | OpenRewrite plugin output |

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/gradle-impl.md` - Gradle execution details
