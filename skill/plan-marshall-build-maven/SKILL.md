---
name: plan-marshall-build-maven
description: Maven build operations — compile, test, verify with JaCoCo coverage, OpenRewrite markers, and multi-module profile management
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Build Maven

Maven build execution with output parsing, module discovery, and wrapper detection. Wrapper resolution prefers the project wrapper (`mvnw`) and falls back to the system `mvn` when no checked-in wrapper is present. See [`build-api-reference.md`](../extension-api/standards/build-api-reference.md) § Wrapper Detection for the detection table.

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

### Discover as the canonical source for integration-tests / e2e

`discover` is the authoritative source for the `integration-tests` and `e2e` test targets consumed at **end-of-phase-5 whole-tree verification**. These canonicals are not separate plugins or hard-coded goals — they are Maven profiles that `discover` surfaces from each `pom.xml`'s declared profile ids (and, lazily, the inherited profiles `enrich_maven_module` resolves via `help:all-profiles`). The Profile Processing Pipeline above maps those discovered profiles to canonical command names (`build.maven.profiles.map.canonical`), so a project's `integration-tests` / `e2e` canonical resolves iff `discover` found the backing Maven profile. On a project that declares no such profile, the canonical does not resolve and the end-of-phase-5 step records `skipped` rather than failing.

Whole-tree gates such as `integration-tests` and `e2e` live only in the `verification_steps` end-of-phase-5 sweep, never in the module-scoped per-deliverable build. The phase-5-execute canonical-verify step reads the canonical from its `default:verify:{canonical}` step ID and resolves it through `architecture resolve --command {canonical}`, which consults this discover-derived profile-to-canonical mapping. For the exact step-invocation shape — how the parameterized canonical-verify step invokes the resolved `integration-tests` target, honours its `execution_tier` / `bash_timeout_seconds`, and reports pass/skip/fail — see the central standard at [`../phase-5-execute/standards/canonical_verify.md`](../phase-5-execute/standards/canonical_verify.md) (do NOT inline-copy the invocation shape here).

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
