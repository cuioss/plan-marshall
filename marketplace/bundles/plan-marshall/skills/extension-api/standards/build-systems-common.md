# Build Systems — Common Standards

Standards shared across all build systems (Maven, Gradle, npm, Python). Tool-specific details are in each build skill's standards directory.

---

## Timeout Management

See [build-execution.md](build-execution.md) § R3 for the complete timeout learning algorithm and Python API.

**Quick reference**: Default 300s, minimum 60s, maximum 1800s, discovery 120s. All timeouts in seconds. Adaptive learning uses `last_duration × 1.25` with weighted averaging.

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

See [canonical-commands.md](canonical-commands.md) for the complete canonical command specification and resolution logic.

---

## Script API

See [build-api-reference.md](build-api-reference.md) for the complete subcommand documentation including parameters, output formats, and tool-specific variations.

---

## Issue Routing

See [build-api-reference.md](build-api-reference.md) § Error Categories for the complete category list per build system and skill routing table.

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
