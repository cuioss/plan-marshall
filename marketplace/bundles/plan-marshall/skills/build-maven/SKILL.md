---
name: build-maven
description: Maven build operations — compile, test, verify with JaCoCo coverage, OpenRewrite markers, and multi-module profile management
user-invocable: false
mode: script-executor
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
- **discover**: Subprocess-free — parses each `pom.xml` with stdlib XML for coordinates, packaging, and declared profile ids, and walks the filesystem for sources/tests. Resolved coordinates, inherited profiles, and the resolved dependency tree are filled lazily, one module at a time, by `enrich_maven_module` (which runs `dependency:tree`, `help:all-profiles`) only when a consumer — the dependency graph or the resolver's profile-canonical path — needs them.
- **search-markers**: Default extensions: `.java`

### Producer-Side Finding Storage (`run --plan-id`)

When `run` is invoked with `--plan-id <P>`, every parsed issue from a failed build is auto-stored via the producer path (always-on). Without `--plan-id`, the build parses and formats only (no finding storage). The maven-specific issue→finding-type routing is:

| Parsed `category` (Issue) | Finding type |
|---------------------------|--------------|
| `test_failure`, `test_*` | `test-failure` |
| categories containing `lint` or `style` | `lint-issue` |
| everything else (compilation, dependency, plugin, surefire/failsafe) | `build-error` |

Severity is mapped from `Issue.severity` (`error` → `error`, `warning` → `warning`). The finding's `module` carries `maven`, `rule` carries the parser category.

> For the producer→store→consumer→gate flow including the producer-mismatch fidelity contract, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md). This SKILL.md owns the per-tool issue→finding-type routing only.

## Module Discovery

Reads `pom.xml` `<modules>` declarations from the parent POM.

### Profile Processing Pipeline

1. Filter to command-line activated profiles (`Active: false`)
2. Apply skip list from configuration (`build.maven.profiles.skip`)
3. Map to canonical command names (`build.maven.profiles.map.canonical`)

## Canonical invocations

The canonical argparse surface for `maven.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### run

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args COMMAND_ARGS \
  [--timeout SECONDS] [--mode {actionable,structured,errors}] [--format {toon,json}] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--project-dir` and `--plan-id` are mutually exclusive.

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven parse \
  --log LOG \
  [--mode {default,errors,structured,no-openrewrite}] [--format {toon,json}] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### search-markers

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven search-markers \
  [--source-dir SOURCE_DIR] [--extensions EXTENSIONS] [--format {toon,json}]
```

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven coverage-report \
  [--project-path PROJECT_PATH] [--report-path REPORT_PATH] [--threshold PERCENT] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven check-warnings \
  [--warnings WARNINGS] [--acceptable-warnings ACCEPTABLE_WARNINGS] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### discover

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven discover \
  [--root ROOT] [--format {toon,json}]
```

### run-config-key

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven run-config-key \
  --command-args COMMAND_ARGS [--format {toon,json}]
```

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/maven-impl.md` — Maven-specific execution and configuration details
- `pm-dev-java:java-maintenance/standards/pom-maintenance.md` — POM structure standards
