# Gradle Implementation Standards

Gradle-specific standards for build command construction, module targeting, and quality configuration. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`.

---

## Build Command Construction

### Base Command

Always use the Gradle wrapper for reproducible builds:

```bash
./gradlew [tasks] [options]
```

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

---

## Module/Project Builds

### Multi-Project Build

#### Build Specific Subproject

```bash
# By project path
./gradlew :services:auth-service:build

# By directory
./gradlew -p services/auth-service build
```

Gradle automatically builds dependencies.

### Project Path Detection

1. Search `settings.gradle(.kts)` for `include` statements
2. Extract included project paths
3. Match requested project name against paths
4. Return full project path notation (`:services:auth`)

---

## Quality Profiles

Gradle doesn't have Maven-like profiles, but uses equivalent mechanisms:

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

### Build Types

```kotlin
tasks.named<Test>("test") {
    if (project.hasProperty("quick")) {
        exclude("**/IntegrationTest*")
    }
}
```

```bash
./gradlew test -Pquick
```

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

---

## Kotlin Support

Error parsing includes Kotlin-specific patterns:
- `Unresolved reference` — missing imports/symbols
- `Type mismatch` — type assignment errors
- `Smart cast to ... is impossible` — unsafe cast patterns
- `None of the following candidates is applicable` — overload resolution
- `Val cannot be reassigned` — immutability violations

These are categorized as `compilation_error` alongside Java errors.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Daemon issues | Add `--no-daemon` |
| Memory issues | Adjust `GRADLE_OPTS` |
| Dependency resolution | Check repositories in settings |
| Version conflicts | Use `dependencyInsight` task |
| Slow builds | Enable parallel execution |

### Diagnostic Commands

```bash
./gradlew --version
./gradlew projects
./gradlew :taskname --dry-run
./gradlew dependencies
./gradlew dependencyInsight --dependency log4j
```

---

## Issue Routing

Routes to skills in the `pm-dev-java` bundle:

| Issue Type | Target Skill |
|------------|-------------|
| `compilation_error` | `pm-dev-java:java-core` |
| `test_failure` | `pm-dev-java:junit-core` |
| `javadoc_warning` | `pm-dev-java:javadoc` |
| `dependency_error` | Manual build.gradle fix |

---

## Dependency Management

Gradle uses `platform()` and `enforcedPlatform()` for BOM-style dependency management, analogous to Maven's `<dependencyManagement>`. For multi-project builds:
- Define versions in a version catalog (`gradle/libs.versions.toml`) or platform project
- Child projects should not override platform-managed versions
- Use `dependencies { implementation platform(project(':bom')) }` for internal BOMs

---

## Coverage Report Paths

| Path | Description |
|------|-------------|
| `build/reports/jacoco/test/jacocoTestReport.xml` | Standard Gradle JaCoCo report |
| `build/reports/jacoco/jacocoTestReport.xml` | Alternative report location |

**Notation**: `plan-marshall:build-gradle:gradle`
