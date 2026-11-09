---
name: build-maven
description: Maven build operations — compile, test, verify with JaCoCo coverage and multi-module profile management
user-invocable: false
mode: script-executor
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build Maven

Maven build execution with output parsing, module discovery, and wrapper detection. Wrapper resolution prefers the project wrapper (`mvnw`) and falls back to the system `mvn` when no checked-in wrapper is present. See [`build-api-reference.md`](../extension-api/standards/build-api-reference.md) § Wrapper Detection for the detection table.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-maven:maven {command} {args}`.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Scripts

| Script | Purpose |
|--------|---------|
| `maven.py` | CLI dispatcher |
| `_maven_execute.py` | Execution config via factory (uses shared `default_command_key_fn`); carries the run-path `-Dtest` selector-miss guard |
| `_maven_cmd_discover.py` | Module discovery via pom.xml + Maven metadata commands |
| `_maven_cmd_parse.py` | Log parsing with JVM base patterns + Maven-specific extensions |
| `_maven_cmd_rewrite_log.py` | Additive OpenRewrite #118 log-parse consumption (Signal B) via the `rewrite-log-parse` domain verb, fail-closed |
| `_maven_cmd_resolve_scope.py` | `resolve-test-scope` — the scoped module set and divergence risk, owned by Maven module directories |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**, **rewrite-log**, **resolve-test-scope**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### Maven-Specific Behavior

- **run**: `--command-args` takes Maven goals/options, e.g., `"verify -Ppre-commit -pl my-module"`. Two truth checks run on the in-process result: a selector that matched nothing — a `-Dtest` on the command line, or one set through `.mvn/maven.config`, `MAVEN_OPTS` or a profile that only the log names — is `indeterminate` with `test_selector_matched_nothing`, and a leading `test` or `package` run that executed no test — a zero summary, a measured summary whose whole population was skipped, or no summary at all for a leading `test` whose reports show no executed test — is `indeterminate` with `test_run_executed_nothing`. A test run whose log cannot be read is `test_log_unreadable`. A green exit code credits no gate when no test ran or no evidence establishes that one did.
- **parse**: Additional `no-openrewrite` mode filters OpenRewrite markers
- **coverage-report**: Searches `target/site/jacoco/jacoco.xml`, `target/jacoco/report.xml`, `target/site/jacoco-aggregate/jacoco.xml`
- **discover**: Subprocess-free — parses each `pom.xml` with stdlib XML for coordinates, packaging, the reactor's `<modules>` (plus a profile's, when the profile is `activeByDefault`), declared profile ids, and the dependencies declared in the module's own POM, and walks the filesystem for sources/tests. A module whose own POM depends on another module of the same reactor with `<type>test-jar</type>` or a non-empty `<classifier>` records the artifact in `metadata.reactor_test_artifacts` and gets the `package`-phase test ladder (`module-tests` = `package -pl {module} -am`, `test-compile` = the same with `-DskipTests`); see [`standards/maven-impl.md`](standards/maven-impl.md) § "Test ladder for reactor test artifacts". A root `pom` aggregator gets the whole-reactor `module-tests` = `test` and `test-compile` = `test-compile` when the reactor IT builds — its own `<modules>`, followed through nested aggregators — holds a module with tests, because the architecture's default scope resolves that module and `mvn test` there runs those modules' tests; a tested POM the root does not list is not built there and grants nothing. See [`standards/maven-impl.md`](standards/maven-impl.md) § "Test canonicals of a reactor root". Resolved coordinates, inherited profiles, and the resolved dependency tree are filled lazily, one module at a time, by `enrich_maven_module` (which runs `dependency:tree`, `help:all-profiles`) only when a consumer — the dependency graph or the resolver's profile-canonical path — needs them.

### Producer-Side Finding Storage (`run --plan-id`)

When `run` is invoked with `--plan-id <P>`, every parsed issue from a failed build is auto-stored via the producer path (always-on). Without `--plan-id`, the build parses and formats only (no finding storage). The maven-specific issue→finding-type routing is:

| Parsed `category` (Issue) | Finding type |
|---------------------------|--------------|
| `test_failure`, `test_*` | `test-failure` |
| categories containing `lint` or `style` | `lint-issue` |
| everything else (compilation, dependency, plugin, surefire/failsafe) | `build-error` |

Severity is mapped from `Issue.severity` (`error` → `error`, `warning` → `warning`). The finding's `module` carries `maven`, `rule` carries the parser category.

Three kinds of `[ERROR]` / `[WARNING]` line are not issues, so they never become findings:

- **Maven's failure epilogue** — the fixed advice printed after a failed build (the `-e` / `-X` re-run advice, the "For more information" and `[Help N]` link lines, the resume advice and its `mvn … -rf :module` / `mvn [args] -r` command), Surefire's report pointers (both the `Please refer to …` and the `See …` wording, for test results and for dump files), Maven 4's `[ERROR]`-level reactor-summary rows and `BUILD FAILURE` banner, and the section banners that head a block whose rows carry the diagnostics — Surefire's `Failures:` / `Errors:` and the compiler plugin's `COMPILATION ERROR :`. Each line is matched in full, so a reworded line is filed again rather than a genuine diagnostic being dropped; `Failed to execute goal …` and compiler `file:[line,col]` messages stay issues on every Maven version.
- **Javac's continuation fields** — the `symbol:` and `location:` lines under a compiler error are attached to that error as its `detail` rather than filed as issues of their own: they carry the name the error refers to, so dropping them would lose the diagnostic. A continuation field with no compiler error before it is filed like any other line (fail-visible).
- **Passing test-count lines** — a `Tests run:` line (summary or per-class) whose `Failures` and `Errors` are both 0, such as `[WARNING] Tests run: 27, Failures: 0, Errors: 0, Skipped: 1`. A count line with failures or errors is still filed.

> For the producer→store→consumer→gate flow including the producer-mismatch fidelity contract, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md). This SKILL.md owns the per-tool issue→finding-type routing only.

### Additive OpenRewrite log-parse consumption (`rewrite-log`)

The `rewrite-log` subcommand consumes **Signal B** of the two-signal OpenRewrite model — the `cui-open-rewrite` #118 structured WARN lines in the captured Maven build log — additively, alongside (never replacing) the existing `openrewrite_info` categorization and issue routing. build-maven does NOT parse the WARN format itself: the format is owned by the domain bundle, and core reaches it only through the `rewrite-log-parse` **domain verb**, resolved null-on-absent. See [`../extension-api/standards/ext-point-domain-verb.md`](../extension-api/standards/ext-point-domain-verb.md) § Declaration for the resolution/dispatch contract (not re-copied here).

The consumption is **fail-closed** (ADR-009) — it never reports a vacuous "clean". Four distinct verdicts:

| Verdict | Condition | Meaning |
|---------|-----------|---------|
| `observed` | The build reached `rewrite:run` AND an active domain provides the verb AND the dispatched parser succeeded | The domain parser was dispatched against the log; structured findings (`path`, `line`, `column`, `recipe`, `message`, newly-detected vs pre-existing) are surfaced. |
| `not_observed` | The build never reached `rewrite:run` (e.g. a compile failure before the OpenRewrite goal) | Absence-of-evidence is a distinct third state, **never** a false `clean` — the findings were simply not produced this run. |
| `domain_inactive` | The build reached `rewrite:run` but no active domain provides the `rewrite-log-parse` verb (e.g. a non-java-cui project) | A first-class skip via null-on-absent resolution, **not** a false clean. |
| `parse_error` | The build reached `rewrite:run` and the verb resolves, but the dispatched parser returned an error payload (executor not found, output unparseable / not an object) or a non-dict | Findings could **not** be observed this run — fail closed rather than report a false `observed` with zero findings. |

The existing Maven parse pipeline, the `openrewrite_info` categorization, and the tree-scan marker signal (`marker-detect`) are unchanged by this additive consumer.

### Test selectors (`-Dtest`)

The selector grammar, stated once here for the whole corpus: **Classes are separated by commas, and a method goes after `#`** — `-Dtest=AwaitsTest,CoreTest#runs`. A `+` between classes joins them into one pattern, and one pattern matches nothing, so `-Dtest=Awaits+Core` selects no test at all. `Class#a+b` is Surefire's method list: it runs methods `a` and `b` of `Class`, and it is valid syntax — the `+` separator means "method" only after the `#`.

A selector that matches nothing is a wrong command, not a test result. `run` reports it as `test_selector_matched_nothing` — an `indeterminate` result naming the selector — whether the runner fails the build with `No tests matching pattern … were executed` or `-Dsurefire.failIfNoSpecifiedTests=false` turns the same miss into an exit-0 summary of zero executed tests.

**Recorded limit — a suppressed miss inside a reactor is not detectable.** With `-Dsurefire.failIfNoSpecifiedTests=false`, a module whose scan is empty returns through the runner's own no-tests path: it prints no `No tests matching pattern` line, and when another module collected tests the aggregate count is non-zero. Such a run reports `success`, and no signal in the log distinguishes it from one whose selector matched everywhere. The same limit applies to Failsafe's `-Dit.test` under a `verify` run: `-Dtest` and `-Dit.test` are both recognised as selectors, so a miss the runner NAMES is caught, but a miss it suppresses to exit 0 inside a reactor that collected unit tests stays invisible. Detection therefore needs the default setting (a failing build, where the runner names the pattern) or a single-module run (where the aggregate is zero and the zero-test check reports `test_run_executed_nothing`). Stating the limit is deliberate: the alternative would be to guess a miss from a run that says nothing about one.

## Module Discovery

Reads `pom.xml` `<modules>` declarations from the parent POM, and Maven 4.1's `<subprojects>` spelling of the same list. A module entry naming a POM file (`child/pom.xml`, `child/pom-alt.xml`) resolves to the directory holding it.

Two under-grants are recorded rather than guessed at: an entry using a property (`${module.dir}/pom.xml`) cannot be resolved without Maven, and a `pom.xml` under `build/` or `target/` is not crawled at all (the shared descriptor walk prunes those trees). In both cases the root keeps no test canonical for that module and the gate records DEGRADED instead of running it — the fail-closed direction.

**A daemon not reconciled to the current code does not run these guards.** The run-path truth checks (the zero-test guard, the selector-miss guard) live in the build skill the daemon child re-runs, so a daemon whose checkout predates a guard keeps running the older code: the reason is recorded here so a stale daemon is diagnosed rather than mistaken for a guard that did not fire.

### Profile Processing Pipeline

1. Filter to command-line activated profiles (`Active: false`)
2. Apply skip list from configuration (`build.maven.profiles.skip`)
3. Map to canonical command names (`build.maven.profiles.map.canonical`)

### Discover as the canonical source for integration-tests / e2e

`discover` is the authoritative source for the `integration-tests` and `e2e` test targets consumed at **end-of-phase-5 whole-tree verification**. These canonicals are not separate plugins or hard-coded goals — they are Maven profiles that `discover` surfaces from each `pom.xml`'s declared profile ids (and, lazily, the inherited profiles `enrich_maven_module` resolves via `help:all-profiles`). The Profile Processing Pipeline above maps those discovered profiles to canonical command names (`build.maven.profiles.map.canonical`), so a project's `integration-tests` / `e2e` canonical resolves iff `discover` found the backing Maven profile. On a project that declares no such profile, the canonical does not resolve and the end-of-phase-5 step records `skipped` rather than failing.

Whole-tree gates such as `integration-tests` and `e2e` live only in the `verification_steps` end-of-phase-5 sweep, never in the module-scoped per-deliverable build. The phase-5-execute canonical-verify step reads the canonical from its `default:verify:{canonical}` step ID and resolves it through `architecture resolve --command {canonical}`, which consults this discover-derived profile-to-canonical mapping. For the exact step-invocation shape — how the parameterized canonical-verify step invokes the resolved `integration-tests` target, honours its `execution_tier` / `bash_timeout_seconds`, and reports pass/skip/fail — see the central standard at [`../phase-5-execute/standards/canonical_verify.md`](../phase-5-execute/standards/canonical_verify.md) (do NOT inline-copy the invocation shape here).

## Module-edge derivation (Axis-C derivation resolver)

`extension.py`'s `BuildExtension` subclasses **both** `BuildExtensionBase` (Axis-B, the file-to-build map above) and `DerivationResolverBase` (Axis-C, module-edge derivation), so this skill also answers *which modules depend on which* for the `graph` / `path` / `neighbors` / `impact` query family and the adjacency surfaces of `overview` and `module` / `info`.

The resolver id is `maven`. Its derivation is the **coordinate join**: each module publishes a `groupId:artifactId` in its `metadata`, each module names its dependencies as `groupId:artifactId:scope` strings, and an edge exists wherever a dependency coordinate matches another module's published coordinate (matched on the first two colon-separated parts, so the scope segment is ignored). This join previously lived inline in `manage-architecture`; it belongs here because the coordinate contract is Maven domain knowledge, and core owns the merge, the provenance, and the traversal rather than the derivation.

**This resolver covers Gradle too.** Gradle discovery publishes the same `metadata.group_id` / `metadata.artifact_id` pair and emits `groupId:artifactId:compile` dependency strings, so a Gradle reactor is joined by this resolver with no Gradle-specific code and no resolver of its own — `build-gradle` registers none. One form is missed: an inter-project dependency (`implementation project(':core')`) is extracted as `project:core:compile`, whose first two segments are the literal `project:core`, matching no published coordinate. Both halves are pinned by `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py`.

Two behaviours are worth naming because they are contract obligations rather than implementation detail:

- **An ambiguous coordinate yields no edge and a reported collision.** When two distinct modules claim the same `groupId:artifactId`, the resolver emits no edge for that coordinate and reports it in `notes[]`. A last-write-wins pick would silently drop one module and every edge pointing at it, with the survivor decided by map iteration order.
- **The enriched overlay is not consulted.** The precedence of a curated or discovered `internal_dependencies` declaration over a derived edge set is core's ruling, applied ahead of the resolver call.

The contract itself — the four faces, the N-resolver union semantics, the anti-vacuity provenance property, and the generic ambiguous-identity-key obligation that binds every resolver — is owned by [`../extension-api/standards/ext-point-derivation-resolver.md`](../extension-api/standards/ext-point-derivation-resolver.md) and is deliberately not restated here.

## Canonical invocations

The canonical argparse surface for `maven.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

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

### rewrite-log

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven rewrite-log \
  --log LOG [--format {toon,json}]
```

Consumes the OpenRewrite #118 log-parse signal from a captured build log, fail-closed. Returns a `rewrite_log.verdict` of `observed` / `not_observed` / `domain_inactive` / `parse_error` (see § "Additive OpenRewrite log-parse consumption").

### resolve-test-scope

```bash
python3 .plan/execute-script.py plan-marshall:build-maven:maven resolve-test-scope \
  [--changed-paths CHANGED_PATHS] (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

The scoped-test answer the `pre-push-quality-gate` module-tests arm asks its resolved build skill: `scoped_modules`, `divergence_possible`, `recommended_target`, `unresolved_paths`, `root_guards_required`, `excluded_population`, `whole_tree_available`. Module ownership is Maven's own — the longest module directory (`paths.module` from `discover`) containing a footprint path — so a reactor's modules, not `marketplace/bundles/<b>` segments, are the population. The reactor root owns no arbitrary file: a root-level `pom.xml` change is reported in `unresolved_paths` and routes the gate to the whole tree. `--changed-paths` is the task-scoped footprint and supersedes the whole-plan footprint from `--plan-id`; a blank value is refused.

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
