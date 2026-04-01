# Gradle Implementation Standards

Standards for Gradle build command construction, module targeting, and timeout management.

---

## Build Command Construction

### Base Command

Always use the Gradle wrapper for reproducible builds:

```bash
./gradlew [tasks] [options]
```

### Log File Handling

Gradle outputs to console by default. The `gradle run` command captures logs automatically:

**Log file location**: `.plan/temp/build-output/{scope}/gradle-{timestamp}.log`

- `{scope}` = module name or `default` for root builds
- `{timestamp}` = `YYYY-MM-DD-HHMMSS`

**Example**: `.plan/temp/build-output/default/gradle-2026-01-04-143022.log`

**Important**: Use `--console=plain` to disable rich console output for parseable logs.

### Common Tasks

| Task | Purpose |
|------|---------|
| `build` | Compile, test, and assemble |
| `clean` | Remove build directory |
| `test` | Run unit tests |
| `check` | Run all verification tasks |
| `assemble` | Assemble all archives |
| `jar` | Assemble JAR archive |
| `javadoc` | Generate Javadoc |
| `dependencies` | Show dependency tree |

### Common Options

| Option | Purpose |
|--------|---------|
| `--console=plain` | Plain console output |
| `-x test` | Skip test task |
| `--continue` | Continue on failure |
| `-p <path>` | Build specific project |
| `--parallel` | Parallel execution |
| `--no-daemon` | Disable daemon |
| `--stacktrace` | Print stacktrace |
| `--info` | Set log level to info |
| `--debug` | Set log level to debug |

---

## Module/Project Builds

### Single Project Build

```bash
./gradlew build
```

### Multi-Project Build

#### Build Specific Subproject

```bash
# By project path
./gradlew :services:auth-service:build

# By directory
./gradlew -p services/auth-service build
```

Gradle automatically builds dependencies.

#### Parallel Execution

```bash
./gradlew build --parallel
```

### Project Path Detection

1. Search `settings.gradle(.kts)` for `include` statements
2. Extract included project paths
3. Match requested project name against paths
4. Return full project path notation (`:services:auth`)

---

## Timeout Management

### Timeout Calculation

```
timeout = last_successful_duration * 1.25
```

Minimum timeout: 60s (1 minute)
Maximum timeout: 600s (10 minutes)

**Note**: All timeouts use seconds. The build script API accepts `--timeout` in seconds.

### Timeout Handling

On timeout:
1. Kill Gradle process
2. Report partial results if available
3. Suggest increasing timeout or investigating slow tasks

---

## Build Status Determination

### Success Indicators

- Exit code 0
- Output contains "BUILD SUCCESSFUL"

### Failure Indicators

- Non-zero exit code
- Output contains "BUILD FAILED"
- Output contains "FAILURE:"

### Parsing Priority

1. Check exit code first
2. Verify with log content
3. Extract specific failure reasons

---

## Quality Profiles

Gradle doesn't have Maven-like profiles, but similar functionality via:

### Build Types

```kotlin
// build.gradle.kts
tasks.named<Test>("test") {
    if (project.hasProperty("quick")) {
        exclude("**/IntegrationTest*")
    }
}
```

```bash
./gradlew test -Pquick
```

### Task Groups

```kotlin
tasks.register("preCommit") {
    group = "verification"
    dependsOn("spotlessCheck", "test")
}
```

```bash
./gradlew preCommit
```

---

## Acceptable Warnings

### Configuration

Acceptable warning patterns are stored in `run-configuration.json` under the `gradle` section:

```json
{
    "gradle": {
        "acceptable_warnings": [
            "uses unchecked or unsafe operations",
            "^.*deprecated.*$"
        ]
    }
}
```

Patterns support substring matching and regex (patterns starting with `^`).

### Access

```
Skill: plan-marshall:manage-run-config
Workflow: Read Configuration
Field: gradle.acceptable_warnings
```

### Infrastructure Warnings (Can Be Acceptable)

1. **Transitive Dependency Conflicts** - Version conflicts from dependencies of dependencies
2. **Plugin Compatibility Warnings** - Plugin warnings for locked parent configurations
3. **Platform-Specific Warnings** - Warnings related to OS, JVM version, or hardware

### Fixable Warnings (NEVER Acceptable)

These warnings MUST be fixed and NEVER added to acceptable list:

1. **JavaDoc Warnings** - ALWAYS FIX
2. **Compilation Warnings** - ALWAYS FIX
3. **Deprecation Warnings** - ALWAYS FIX (unless external)
4. **Code Quality Warnings** - ALWAYS FIX

---

## CI/CD Standards

### Environment Variables

```bash
export GRADLE_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"
export CI=true
```

### Non-Interactive Mode

```bash
./gradlew build --no-daemon --console=plain
```

### Build Cache

```bash
./gradlew build --build-cache
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Daemon issues | Add `--no-daemon` |
| Memory issues | Adjust `GRADLE_OPTS` |
| Dependency resolution | Check repositories in settings |
| Version conflicts | Use `dependencyInsight` task |
| Slow builds | Enable parallel execution |

### Diagnostic Commands

```bash
# Show Gradle version
./gradlew --version

# Show project structure
./gradlew projects

# Show task dependencies
./gradlew :taskname --dry-run

# Show dependency tree
./gradlew dependencies

# Investigate specific dependency
./gradlew dependencyInsight --dependency log4j
```

---

## Script Reference

| Subcommand | Description |
|------------|-------------|
| `run` | Execute Gradle build with automatic log file handling and parsed output (primary API) |
| `parse` | Parse Gradle build output and categorize issues |
| `find-project` | Find Gradle project path from project name |
| `search-markers` | Search for OpenRewrite TODO markers |
| `check-warnings` | Categorize build warnings against acceptable patterns |

**Notation**: `plan-marshall:build-gradle:gradle`

### run Command

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run \
    --command-args "<tasks>" \
    [--project-dir <path>] \
    [--format toon|json] \
    [--mode actionable|structured|errors] \
    [--timeout <seconds>]
```

**Output format**: Tab-separated TOON (default) or JSON with `--format json`

**Fields**: `status`, `exit_code`, `duration_seconds`, `log_file`, `command`

---

## Coverage Report Paths

The coverage report parser (`_gradle_cmd_coverage_report.py`) searches these JaCoCo XML report paths in order:

| Path | Description |
|------|-------------|
| `build/reports/jacoco/test/jacocoTestReport.xml` | Standard Gradle JaCoCo report |
| `build/reports/jacoco/jacocoTestReport.xml` | Alternative report location |

For multi-project builds, pass `--module-path {module-dir}` to scope the search to a specific subproject's `build/` directory.
