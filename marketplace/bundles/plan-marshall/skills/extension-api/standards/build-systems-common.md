# Build Systems — Common Standards

Standards shared across all build systems (Maven, Gradle, npm, Python). Tool-specific details are in each build skill's standards directory.

---

## Timeout Management

### Timeout Calculation

```
timeout = last_successful_duration * 1.25
```

### Default Timeouts

| Parameter | Value |
|-----------|-------|
| Default timeout | 300 seconds (5 minutes) |
| Minimum timeout | 60 seconds |
| Maximum timeout | 1800 seconds (30 minutes) |
| Discovery timeout | 120 seconds |

**Note**: All timeouts use **seconds** (not milliseconds). The build script API accepts `--timeout` in seconds.

### Adaptive Learning

- On successful completion, actual duration is recorded
- On timeout failure, the cached timeout is doubled for the next run (capped at 1800s)
- Command key format varies per build system (e.g., `maven:verify`, `python:module_tests`)

### Timeout Behavior

On timeout:
1. Kill build process
2. Return exit code -1 (with status `timeout`)
3. Log file contains partial output up to timeout
4. Build marked as FAILURE

---

## Log File Handling

### Log File Pattern

```
.plan/temp/build-output/{scope}/{tool}-{YYYY-MM-DD-HHmmss}.log
```

- `{scope}`: Module name or `default` for root builds
- `{tool}`: Build system name (maven, gradle, npm, python)

### Output Capture

All output goes to log file. Capture strategy varies per build system:

| Build System | Strategy |
|-------------|----------|
| Maven | `-l` log flag (native) |
| Gradle | stdout redirect + `--console=plain` |
| npm | stdout redirect |
| Python | stdout redirect |

---

## Build Status Determination

### General Rules

| Condition | Status |
|-----------|--------|
| Exit code 0 + success markers | SUCCESS |
| Non-zero exit code | FAILURE |
| Exit code 124 | FAILURE (timeout) |

**Never assume success from exit code alone.** Always verify with log content markers.

### Build System Markers

| Build System | Success Marker | Failure Marker |
|-------------|----------------|----------------|
| Maven | `BUILD SUCCESS` | `BUILD FAILURE` |
| Gradle | `BUILD SUCCESSFUL` | `BUILD FAILED` |
| npm | Exit code 0 | Exit code != 0 |
| Python | Exit code 0 | Exit code != 0 |

---

## Acceptable Warnings

### Configuration

Acceptable warning patterns are stored in `run-configuration.json` under the build-system-specific section:

```json
{
    "<build_system>": {
        "acceptable_warnings": [
            "substring pattern",
            "^regex pattern$"
        ]
    }
}
```

Patterns support:
- **Substring matching**: Pattern checked as case-insensitive substring of message
- **Regex matching**: Patterns starting with `^` treated as regex

### Access

```
Skill: plan-marshall:manage-run-config
Workflow: Read Configuration
Field: <build_system>.acceptable_warnings
```

### Warning Categories

**Infrastructure Warnings (Can Be Acceptable)**:
1. Transitive dependency conflicts
2. Plugin compatibility warnings for locked configurations
3. Platform-specific warnings (OS, runtime version, hardware)

**Fixable Warnings (NEVER Acceptable)**:
1. JavaDoc/documentation warnings — ALWAYS FIX
2. Compilation warnings — ALWAYS FIX
3. Deprecation warnings — ALWAYS FIX (unless external dependency)
4. Code quality warnings — ALWAYS FIX

---

## Canonical Commands

All build systems generate commands using the shared executor pattern:

```
python3 .plan/execute-script.py {bundle}:{skill}:{script} run --command-args "{tool_args}"
```

See `canonical-commands.md` for the full canonical command specification.

---

## Script API

All build skills share the same subcommand structure:

| Subcommand | Purpose | Available In |
|------------|---------|--------------|
| `run` | Execute build and auto-parse on failure (primary API) | All |
| `parse` | Parse build output from log file | All |
| `coverage-report` | Parse coverage report | All |
| `check-warnings` | Categorize warnings against acceptable patterns | All |
| `discover` | Discover modules with metadata | All |
| `search-markers` | Search OpenRewrite TODO markers | Maven, Gradle |
| `find-project` | Find subproject path from name | Gradle only |

### Common run Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--command-args` | Yes | — | Tool-specific command arguments |
| `--timeout` | No | 300 | Build timeout in seconds |
| `--mode` | No | actionable | Output mode: actionable, structured, errors |
| `--format` | No | toon | Output format: toon or json |

---

## Issue Routing

Issues are categorized and routed to appropriate fix strategies:

| Category | Description | Build Systems |
|----------|-------------|---------------|
| `compilation_error` | Compile-time errors | Maven, Gradle, npm |
| `test_failure` | Test assertion failures | All |
| `dependency_error` | Dependency resolution issues | Maven, Gradle, npm |
| `lint_error` | Linter violations | npm, Python |
| `type_error` | Type-check errors | Python |
| `javadoc_warning` | Documentation issues | Maven, Gradle |
| `deprecation_warning` | Deprecated API usage | Maven, Gradle |
| `unchecked_warning` | Unchecked type conversions | Maven, Gradle |
| `openrewrite_info` | OpenRewrite plugin output | Maven, Gradle |
| `playwright_error` | Browser automation failures | npm |
| `import_error` | Module import errors | Python |

---

## CI/CD Standards

All build systems support CI mode via environment variables:

| Build System | CI Environment Variables | Additional Flags |
|-------------|--------------------------|------------------|
| Maven | `CI=true`, `MAVEN_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"` | `--batch-mode --no-transfer-progress` |
| Gradle | `CI=true`, `GRADLE_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"` | `--no-daemon --console=plain` |
| npm | `CI=true`, `NODE_ENV=test` | (non-interactive automatically) |
| Python | `CI=true`, `PYTHONDONTWRITEBYTECODE=1` | Cache `.pyprojectx/` between runs |

See each tool's `*-impl.md` for full CI/CD configuration details.

---

## Common Troubleshooting Patterns

| Issue | Applies To | Solution |
|-------|-----------|----------|
| Memory issues | Maven, Gradle | Adjust `*_OPTS` (`-Xmx2g -XX:MaxMetaspaceSize=512m`) |
| Dependency resolution failures | All | Check descriptor file (pom.xml, build.gradle, package.json, pyproject.toml) |
| Version conflicts | Maven, Gradle | Use `dependency:tree` / `dependencyInsight` |
| Slow builds | Maven, Gradle | Enable parallel builds (`-T 1C` / `--parallel`) |
| Build timeout | All | Increase `--timeout` or check for hanging processes |

See each tool's `*-impl.md` for tool-specific diagnostic commands.
