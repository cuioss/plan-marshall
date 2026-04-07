---
name: build-gradle
description: Gradle build operations — Java/Kotlin builds with JaCoCo coverage, quality task detection, multi-project discovery, and OpenRewrite markers
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build Gradle

Gradle build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-gradle:gradle {command} {args}`.

## Scripts

| Script | Purpose |
|--------|---------|
| `gradle.py` | CLI dispatcher |
| `_gradle_execute.py` | Execution config via factory (custom command_key_fn for `:module:` notation) |
| `_gradle_cmd_discover.py` | Module discovery via settings.gradle(.kts) + Gradle metadata commands |
| `_gradle_cmd_parse.py` | Log parsing with JVM base patterns + Kotlin error patterns |
| `_gradle_cmd_find_project.py` | Subproject name-to-notation resolution |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**, **search-markers**, **find-project**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### Gradle-Specific Behavior

- **run**: `--command-args` takes Gradle tasks, e.g., `":module:build"` or `"build"`
- **parse**: Additional `no-openrewrite` mode; includes Kotlin-specific error patterns (Unresolved reference, Type mismatch, etc.)
- **coverage-report**: Searches `build/reports/jacoco/test/jacocoTestReport.xml`, `build/reports/jacoco/jacocoTestReport.xml`, `build/jacoco/test.xml`
- **discover**: Reads `settings.gradle(.kts)` `include()` declarations (Groovy + Kotlin DSL); detects quality tasks (`spotlessCheck`, `checkstyleMain`, `pmdMain`, `detekt`, `ktlintCheck`)
- **find-project**: Resolves module names to Gradle notation (e.g., `auth` → `:services:auth`)
- **search-markers**: Default extensions: `.java,.kt`

## Module Discovery

Reads `settings.gradle(.kts)` for `include()` declarations. Supports both Groovy and Kotlin DSL. Shells out to Gradle for properties, dependencies, and quality task detection.

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/gradle-impl.md` — Gradle-specific execution and configuration details
