# Maven Implementation Standards

Standards for Maven build execution, output parsing, and issue handling.

---

## Build Command Construction

### Base Command

All Maven builds use the Maven Wrapper from the project root:

```bash
./mvnw {goals} {options}
```

**Output Capture**: Use Maven's `-l` (log file) flag for output capture with timestamped filenames:

```bash
./mvnw -l target/build-output-2025-11-25-143022.log clean install
```

### Common Goals

**Note**: `clean` is a separate command. Run it explicitly before other goals when needed, or use `clean install` combination for fresh builds.

| Goal | Purpose |
|------|---------|
| `clean` | Remove build artifacts and generated files |
| `install` | Build and install artifact to local repository |
| `clean install` | Fresh build with artifact installation |
| `verify` | Full build without installation |
| `test` | Compile and run tests only |
| `package` | Build without integration tests |
| `package -Dnative` | Native image build |
| `-Ppre-commit verify` | Pre-commit quality checks |
| `-Pcoverage verify` | Coverage analysis build |

### Log File Handling (CRITICAL)

**Problem**: When using `-l target/build.log` with `clean`, the `clean` phase deletes `target/` before Maven can create the log file.

**Solution**: ALWAYS pre-create the log file before executing Maven:

1. Generate timestamped filename: `target/build-output-{YYYY-MM-DD-HHmmss}.log`
2. Pre-create the log file (use Write tool)
3. Execute: `./mvnw -l target/build-output-{timestamp}.log {goals}`

---

## Module Builds

### Single Module Build

Use `-pl` (project list) to build specific modules:

```bash
./mvnw -l target/module-build.log clean install -pl module-name
```

For nested modules: `-pl parent/child-module`

### Building with Dependencies

| Flag | Purpose | Example |
|------|---------|---------|
| `-pl` | Build specific modules | `-pl module-a,module-b` |
| `-am` | Build required dependencies | `-pl module-a -am` |
| `-amd` | Build dependent modules | `-pl module-a -amd` |

### Resume From Module

Use `-rf` (resume from) to restart a failed build:

```bash
./mvnw -l target/resume-build.log clean install -rf :module-name
```

---

## Timeout Management

### Timeout Calculation

```
timeout = last_successful_duration * 1.25
```

### Default Timeouts

| Build Type | Default Timeout |
|------------|-----------------|
| Unit tests only | 60,000ms (1 min) |
| Full build | 120,000ms (2 min) |
| Integration tests | 300,000ms (5 min) |
| Native image | 600,000ms (10 min) |

---

## Build Status Determination

| Exit Code | Output Content | Status |
|-----------|---------------|--------|
| 0 | Contains "BUILD SUCCESS" | SUCCESS |
| 0 | Contains "BUILD FAILURE" | FAILURE |
| != 0 | Any | FAILURE |
| 0 | Contains [ERROR] lines | FAILURE |

**Never assume success from exit code alone.**

---

## Quality Profiles

**Note**: Profile commands do NOT include clean goal. Run `clean` separately if needed.

### Pre-Commit Profile

```bash
./mvnw -l target/pre-commit.log -Ppre-commit verify
```

Includes: Compilation with warnings, unit tests, code quality checks, JavaDoc validation.

### Coverage Profile

```bash
./mvnw -l target/coverage.log -Pcoverage verify
```

Includes: All pre-commit checks, JaCoCo coverage, threshold verification.

### Integration Tests Profile

```bash
./mvnw -l target/integration.log -Pintegration-tests verify
```

Runs integration tests (*IT.java, *ITCase.java).

---

## Acceptable Warnings

### Infrastructure Warnings (Can Be Acceptable)

1. **Transitive Dependency Conflicts** - Version conflicts from dependencies of dependencies
2. **Plugin Compatibility Warnings** - Plugin warnings for configurations locked by parent POM
3. **Platform-Specific Warnings** - Warnings related to OS, JVM version, or hardware

### Fixable Warnings (NEVER Acceptable)

These warnings MUST be fixed and NEVER added to acceptable list:

1. **JavaDoc Warnings** - ALWAYS FIX
2. **Compilation Warnings** - ALWAYS FIX
3. **Deprecation Warnings** - ALWAYS FIX (unless external)
4. **Code Quality Warnings** - ALWAYS FIX

### Configuration Access

```
Skill: plan-marshall:manage-run-config
Workflow: Read Configuration
Field: maven.acceptable_warnings
```

---

## OpenRewrite Marker Handling

### Marker Format

```java
/*~~(TODO: message about the issue)>*/
```

### Marker Categories

**Category 1: LogRecord Warnings (AUTO-SUPPRESS)**

Recipe: `CuiLogRecordPatternRecipe`

```java
// cui-rewrite:disable CuiLogRecordPatternRecipe
LOGGER.info("Direct message for debugging");
```

**Category 2: Exception Warnings (AUTO-SUPPRESS)**

Recipe: `InvalidExceptionUsageRecipe`

```java
// cui-rewrite:disable InvalidExceptionUsageRecipe
catch (SomeException e) { ... }
```

**Category 3: Other Markers (ASK USER)**

All other marker types require user confirmation before suppression.

### Suppression Syntax

```java
// Single line
// cui-rewrite:disable RecipeName
<statement>

// Block
// cui-rewrite:disable RecipeName
<statements>
// cui-rewrite:enable RecipeName
```

---

## Script Reference

| Subcommand | Description |
|------------|-------------|
| `execute` | Execute Maven build with automatic log file handling |
| `parse` | Parse Maven build output and categorize issues |
| `find-module` | Find Maven module path from artifactId |
| `search-markers` | Search for OpenRewrite TODO markers |
| `check-warnings` | Categorize build warnings against acceptable patterns |

**Notation**: `pm-dev-java:plan-marshall-plugin:maven`

---

## Issue Routing

| Issue Type | Fix Command |
|------------|-------------|
| `compilation_error` | `/java-implement-code` |
| `test_failure` | `/java-implement-tests` |
| `javadoc_warning` | `/java-fix-javadoc` |
| `dependency_error` | Manual POM fix |

---

## Extension Defaults Configuration

Extensions can configure Maven-specific defaults via `config_defaults()` callback. These values are stored in `run-configuration.json` under `extension_defaults`.

### Configuration Keys

| Key | Format | Description |
|-----|--------|-------------|
| `build.maven.profiles.skip` | Comma-separated | Profile names to ignore during discovery |
| `build.maven.profiles.map.canonical` | Comma-separated pairs | Profile-to-canonical command mappings |

### Profile Skip Configuration

Profiles listed in `build.maven.profiles.skip` are excluded from command generation.

**Key**: `build.maven.profiles.skip`

**Format**: `profile1,profile2,profile3`

**Example**:
```
itest,native,jfr
```

**Effect**: The profiles `itest`, `native`, and `jfr` will not generate canonical commands.

**Use Case**: Skip internal/infrastructure profiles that shouldn't be exposed as build commands.

### Profile Mapping Configuration

Explicit profile-to-canonical mappings override automatic classification.

**Key**: `build.maven.profiles.map.canonical`

**Format**: `profile1:canonical1,profile2:canonical2,...`

**Example**:
```
pre-commit:quality-gate,coverage:coverage,javadoc:javadoc
```

**Effect**: Maps profiles to canonical commands:
- `pre-commit` → `quality-gate`
- `coverage` → `coverage`
- `javadoc` → `javadoc` (CUI-specific canonical command)

**Standard Canonical Commands** (from extension_base.py):
- `quality-gate` - Pre-commit quality checks
- `integration-tests` - Integration test execution
- `coverage` - Code coverage measurement
- `performance` - Benchmark/performance tests

**Note**: Extensions can define additional canonical commands (e.g., `javadoc` for CUI projects).

### Python Constants

Import from `maven_cmd_discover`:

```python
from _maven_cmd_discover import (
    EXT_KEY_PROFILES_SKIP,      # "build.maven.profiles.skip"
    EXT_KEY_PROFILES_MAP,       # "build.maven.profiles.map.canonical"
)
```

### Usage in config_defaults

```python
def config_defaults(self, project_root: str) -> None:
    """Configure CUI-specific Maven defaults."""
    from _config_core import ext_defaults_set_default
    from _maven_cmd_discover import EXT_KEY_PROFILES_SKIP, EXT_KEY_PROFILES_MAP

    # Skip internal profiles
    ext_defaults_set_default(EXT_KEY_PROFILES_SKIP, "itest,native", project_root)

    # Map profiles to canonical commands
    ext_defaults_set_default(
        EXT_KEY_PROFILES_MAP,
        "pre-commit:quality-gate,coverage:coverage,javadoc:javadoc",
        project_root
    )
```

**Contract**: `ext_defaults_set_default` only writes if the key doesn't exist (write-once semantics).
