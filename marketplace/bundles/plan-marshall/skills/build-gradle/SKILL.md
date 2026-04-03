---
name: build-gradle
description: Gradle build operations with execution, parsing, and module discovery
user-invocable: false
---

# Build Gradle

Gradle build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

See `plan-marshall:extension-api/standards/build-api-reference.md` § Enforcement for shared rules.

**Tool-specific constraint:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-gradle:gradle {command} {args}`

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `gradle.py` | CLI | Gradle operations dispatcher (includes coverage + warning config) |
| `_gradle_execute.py` | Library | Execution config via factory pattern |
| `_gradle_cmd_discover.py` | Library | Module discovery via build.gradle |
| `_gradle_cmd_parse.py` | Library | Log parsing, issue extraction (uses shared categorizer) |
| `_gradle_cmd_find_project.py` | Library | Gradle subproject location |

Shared infrastructure from `extension-api`: `_build_execute_factory.py`, `_build_shared.py`, `_build_parse.py`, `_build_coverage_report.py`, `_build_check_warnings.py`.

## Subcommands

Gradle supports all shared subcommands documented in `build-api-reference.md`:
**run**, **parse**, **coverage-report**, **check-warnings**, **discover**, **search-markers**, **find-project**.

### Gradle-Specific Notes

**run**: The `--command-args` value contains Gradle tasks, e.g., `":module:build"` or `"build"`.

**parse**: Supports the `no-openrewrite` mode in addition to shared modes.

**coverage-report**: Auto-detects JaCoCo XML reports in these locations:
- `build/reports/jacoco/test/jacocoTestReport.xml`
- `build/reports/jacoco/jacocoTestReport.xml`
- `build/jacoco/test.xml`

**discover**: Reads `settings.gradle(.kts)` `include()` declarations (Groovy and Kotlin DSL). Also detects quality tasks: `spotlessCheck`, `checkstyleMain`, `pmdMain`, `detekt`, `ktlintCheck`.

**find-project**: Gradle-specific utility for resolving module names to Gradle notation (`:services:auth`). Useful when error output contains a module name but you need the Gradle notation to construct a build command. Not available in other build systems — Maven uses `-pl {module}` directly.

**search-markers**: Default extensions include `.java,.kt` (Kotlin support).

## Error Categories

Uses the shared JVM error categories (see `build-api-reference.md` § Shared categories).

Gradle-specific additions:
- Uses **regex patterns** for task-specific markers (e.g., `Execution failed for task ':.*:compileJava'`)
- `compilation_error` additionally detects Kotlin patterns: `Unresolved reference`, `Type mismatch`, `Smart cast` failures
- Supports Kotlin (`.kt`), Groovy (`.groovy`), and Scala (`.scala`) file location parsing

## Module Discovery

Reads `settings.gradle(.kts)` to detect multi-project builds. Subprojects are identified from `include()` declarations. Supports both Groovy and Kotlin DSL.

### Command Generation

| Canonical | Gradle Command |
|-----------|----------------|
| `verify` | `:{module}:build` |
| `quality-gate` | `:{module}:check` |
| `compile` | `:{module}:compileJava` |
| `module-tests` | `:{module}:test` |
| `coverage` | `:{module}:test :{module}:jacocoTestReport` |
| `clean` | `clean` |

### Issue Routing

Gradle errors route to `pm-dev-java` bundle skills (same as Maven):

| Category | Target Skill |
|----------|-------------|
| `compilation_error` | `pm-dev-java:java-core` |
| `test_failure` | `pm-dev-java:junit-core` |
| `javadoc_warning` | `pm-dev-java:javadoc` |

## References

- `plan-marshall:extension-api/standards/build-api-reference.md` — Shared subcommand documentation
- `plan-marshall:extension-api/standards/build-execution.md` — Execution contract and lifecycle
- `standards/gradle-impl.md` — Gradle-specific execution details
