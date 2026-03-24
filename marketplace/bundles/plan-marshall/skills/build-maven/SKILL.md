---
name: build-maven
description: Maven build operations with execution, parsing, and module discovery
user-invocable: false
---

# Build Maven

## Enforcement

- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py plan-marshall:build-maven:maven ...`
- Never invoke `mvn` or `./mvnw` directly outside of script internals
- All script output follows TOON format contract

---

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
| `maven.py` | CLI | Maven operations dispatcher |
| `_maven_execute.py` | Library | Foundation execution, wrapper detection |
| `_maven_cmd_discover.py` | Library | Module discovery via pom.xml |
| `_maven_cmd_parse.py` | Library | Log parsing, issue extraction |
| `_maven_cmd_check_warnings.py` | Library | Warning categorization |
| `_maven_cmd_search_markers.py` | Library | OpenRewrite TODO marker detection |

## Maven run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
    --targets "<goals>" \
    [--module <module>] \
    [--profile <profile>] \
    [--timeout <seconds>] \
    [--mode <mode>]
```

**Parameters**:
- `--targets` - Maven goals to execute (required)
- `--module` - Target module for multi-module projects
- `--profile` - Maven profile to activate
- `--timeout` - Timeout in seconds (default from run-config)
- `--mode` - Output mode: actionable (default), structured, errors

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

### Low-level Operations

| Command | Purpose |
|---------|---------|
| `maven parse` | Parse build output from log file |
| `maven search-markers` | Search OpenRewrite TODO markers |
| `maven check-warnings` | Categorize warnings against patterns |

## Wrapper Detection

```
Maven:  ./mvnw > mvn (on PATH)
```

## Error Categories

| Category | Description |
|----------|-------------|
| `compilation_error` | Compile-time Java errors |
| `test_failure` | Test assertion failures |
| `dependency_error` | Dependency resolution issues |
| `javadoc_warning` | JavaDoc documentation issues |
| `deprecation_warning` | Deprecated API usage |
| `unchecked_warning` | Unchecked type conversions |
| `openrewrite_info` | OpenRewrite plugin output |

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/maven-impl.md` - Maven execution details
- `standards/pom-maintenance.md` - POM structure and dependency management standards
