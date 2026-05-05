---
name: build-maven
description: Maven build operations — compile, test, verify with JaCoCo coverage, OpenRewrite markers, and multi-module profile management
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build Maven

Maven build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-maven:maven {command} {args}`.

## Scripts

| Script | Purpose |
|--------|---------|
| `maven.py` | CLI dispatcher |
| `_maven_execute.py` | Execution config via factory (uses shared `default_command_key_fn`) |
| `_maven_cmd_discover.py` | Module discovery via pom.xml + Maven metadata commands |
| `_maven_cmd_parse.py` | Log parsing with JVM base patterns + Maven-specific extensions |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**, **search-markers**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### Maven-Specific Behavior

- **run**: `--command-args` takes Maven goals/options, e.g., `"verify -Ppre-commit -pl my-module"`
- **parse**: Additional `no-openrewrite` mode filters OpenRewrite markers
- **coverage-report**: Searches `target/site/jacoco/jacoco.xml`, `target/jacoco/report.xml`, `target/site/jacoco-aggregate/jacoco.xml`
- **discover**: Shells out to Maven (`dependency:tree`, `help:all-profiles`) for richer metadata including profiles and dependency scopes — slower than static-file approaches
- **search-markers**: Default extensions: `.java`

### Producer-Side Finding Storage (`run --plan-id`)

When `run` is invoked with `--plan-id <P>`, every parsed issue from a failed build is auto-stored as a finding via `manage-findings add` (always-on). Without `--plan-id`, the historical silent behaviour is preserved.

| Parsed `category` (Issue) | Finding type |
|---------------------------|--------------|
| `test_failure`, `test_*` | `test-failure` |
| categories containing `lint` or `style` | `lint-issue` |
| everything else (compilation, dependency, plugin, surefire/failsafe) | `build-error` |

Severity is mapped from `Issue.severity` (`error` → `error`, `warning` → `warning`). The finding's `module` carries `maven`, `rule` carries the parser category. Producer-side mismatches (parsed ≠ stored) are surfaced as a Q-Gate finding under phase `5-execute` with title prefix `(producer-mismatch)`.

## Module Discovery

Reads `pom.xml` `<modules>` declarations from the parent POM.

### Profile Processing Pipeline

1. Filter to command-line activated profiles (`Active: false`)
2. Apply skip list from configuration (`build.maven.profiles.skip`)
3. Map to canonical command names (`build.maven.profiles.map.canonical`)

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/maven-impl.md` — Maven-specific execution and configuration details
- `pm-dev-java:java-maintenance/standards/pom-maintenance.md` — POM structure standards
