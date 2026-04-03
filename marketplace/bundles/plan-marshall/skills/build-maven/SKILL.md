---
name: build-maven
description: Maven build operations with execution, output parsing, module discovery, and coverage analysis
user-invocable: false
---

# Build Maven

Maven build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

See `plan-marshall:extension-api/standards/build-api-reference.md` § Enforcement for shared rules.

**Tool-specific constraint:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-maven:maven {command} {args}`

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `maven.py` | CLI | Maven operations dispatcher (includes coverage + warning config) |
| `_maven_execute.py` | Library | Execution config via factory pattern |
| `_maven_cmd_discover.py` | Library | Module discovery via pom.xml |
| `_maven_cmd_parse.py` | Library | Log parsing, issue extraction (uses shared categorizer) |

Shared infrastructure from `extension-api`: `_build_execute_factory.py`, `_build_shared.py`, `_build_parse.py`, `_build_coverage_report.py`, `_build_check_warnings.py`.

## Subcommands

Maven supports all shared subcommands documented in `build-api-reference.md`:
**run**, **parse**, **coverage-report**, **check-warnings**, **discover**, **search-markers**.

### Maven-Specific Notes

**run**: The `--command-args` value contains Maven goals and options, e.g., `"verify -Ppre-commit -pl my-module"`.

**parse**: Supports the `no-openrewrite` mode in addition to shared modes.

**coverage-report**: Auto-detects JaCoCo XML reports in these locations:
- `target/site/jacoco/jacoco.xml`
- `target/jacoco/report.xml`
- `target/site/jacoco-aggregate/jacoco.xml`

**discover**: Shells out to Maven for metadata (`dependency:tree`, `help:all-profiles`) in addition to parsing `pom.xml`. This makes discovery slower than static-file-only approaches (Gradle, npm, Python) but provides richer metadata including profiles and dependency scopes.

## Error Categories

Uses the shared JVM error categories (see `build-api-reference.md` § Shared categories).

Maven-specific: uses **substring matching** (case-insensitive) for all patterns. Key patterns:
- `compilation_error`: "cannot find symbol", "incompatible types", "illegal start", etc.
- `test_failure`: "tests run:", "failure!", "assertionfailed", "expected:", etc.
- `dependency_error`: "could not resolve dependencies", "could not find artifact", etc.

## Module Discovery

Reads `pom.xml` `<modules>` declarations. Modules are identified from the parent POM.

### Profile Processing Pipeline

1. Filter to command-line activated profiles (`Active: false`)
2. Apply skip list from configuration (`build.maven.profiles.skip`)
3. Map to canonical command names (`build.maven.profiles.map.canonical`)

### Command Generation

| Canonical | Maven Command |
|-----------|---------------|
| `verify` | `verify -pl {module}` |
| `quality-gate` | `-Ppre-commit verify -pl {module}` |
| `compile` | `compile -pl {module}` |
| `module-tests` | `test -pl {module}` |
| `coverage` | `-Pcoverage verify -pl {module}` |
| `clean` | `clean` |

Profile-to-canonical mappings are configurable via extension defaults.

### Issue Routing

Maven errors route to `pm-dev-java` bundle skills:

| Category | Target Skill |
|----------|-------------|
| `compilation_error` | `pm-dev-java:java-core` |
| `test_failure` | `pm-dev-java:junit-core` |
| `javadoc_warning` | `pm-dev-java:javadoc` |

## Wrapper Detection

```
Maven: ./mvnw > mvnw.cmd > mvn (system PATH)
```

Detection order: `./mvnw` (Unix), `mvnw.cmd` (Windows), `mvn` (system fallback). Falls back to system `mvn` if no wrapper is found.

## References

- `plan-marshall:extension-api/standards/build-api-reference.md` — Shared subcommand documentation
- `plan-marshall:extension-api/standards/build-execution.md` — Execution contract and lifecycle
- `standards/maven-impl.md` — Maven-specific execution details
- `standards/pom-maintenance.md` — POM structure and dependency management standards
