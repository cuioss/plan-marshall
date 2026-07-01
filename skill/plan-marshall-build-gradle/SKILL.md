---
name: plan-marshall-build-gradle
description: Gradle build operations — Java/Kotlin builds with JaCoCo coverage, quality task detection, multi-project discovery, and OpenRewrite markers
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Build Gradle

Gradle build execution with output parsing, module discovery, and wrapper detection. Wrapper resolution prefers the project wrapper (`gradlew`) and falls back to the system `gradle` when no checked-in wrapper is present. See [`build-api-reference.md`](../extension-api/standards/build-api-reference.md) § Wrapper Detection for the detection table.

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

### Producer-Side Finding Storage (`run --plan-id`)

When `run` is invoked with `--plan-id <P>`, every parsed issue from a failed build is auto-stored via the producer path (always-on). Without `--plan-id`, the build parses and formats only (no finding storage). The gradle-specific issue→finding-type routing is:

| Parsed `category` (Issue) | Finding type |
|---------------------------|--------------|
| `test_failure`, `test_*` | `test-failure` |
| categories containing `lint` or `style` (spotless, checkstyle, ktlint, detekt) | `lint-issue` |
| everything else (compilation, dependency, plugin, Kotlin Unresolved/Type mismatch) | `build-error` |

The finding's `module` carries `gradle`, `rule` carries the parser category.

> For the producer→store→consumer→gate flow including the producer-mismatch fidelity contract, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md). This SKILL.md owns the per-tool issue→finding-type routing only.

## Module Discovery

Reads `settings.gradle(.kts)` for `include()` declarations. Supports both Groovy and Kotlin DSL. Shells out to Gradle for properties, dependencies, and quality task detection.

## Canonical invocations

The canonical argparse surface for `gradle.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### run

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run \
  --command-args COMMAND_ARGS \
  [--timeout SECONDS] [--mode {actionable,structured,errors}] [--format {toon,json}] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--project-dir` and `--plan-id` are mutually exclusive.

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle parse \
  --log LOG \
  [--mode {default,errors,structured,no-openrewrite}] [--format {toon,json}] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### find-project

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle find-project \
  (--project-name PROJECT_NAME | --project-path PROJECT_PATH) [--root ROOT]
```

`--project-name` and `--project-path` are mutually exclusive; exactly one must be supplied.

### search-markers

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle search-markers \
  [--source-dir SOURCE_DIR] [--extensions EXTENSIONS] [--format {toon,json}]
```

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle coverage-report \
  [--project-path PROJECT_PATH] [--report-path REPORT_PATH] [--threshold PERCENT] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle check-warnings \
  [--warnings WARNINGS] [--acceptable-warnings ACCEPTABLE_WARNINGS] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### discover

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle discover \
  [--root ROOT] [--format {toon,json}]
```

### run-config-key

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run-config-key \
  --command-args COMMAND_ARGS [--format {toon,json}]
```

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/gradle-impl.md` — Gradle-specific execution and configuration details
