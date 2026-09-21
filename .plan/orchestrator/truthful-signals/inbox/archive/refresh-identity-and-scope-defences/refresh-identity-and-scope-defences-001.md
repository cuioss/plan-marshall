envelope_version=1
sender_type=plan
sender_id=refresh-identity-and-scope-defences
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T12:45:00Z

component=plan-marshall:build-maven
category=bug
title=The module-tests canonical cannot verify a module that consumes a sibling test-jar, and the maven parser reports only the last Tests-run summary
confidence=high
source_plan=refresh-identity-and-scope-defences

# The module-tests canonical cannot verify a module that consumes a sibling test-jar, and the maven parser reports only the last Tests-run summary

Two defects surfaced by the same build, in the same skill. Both distort the truth of a build signal: the first manufactures a red from working code, the second under-reports a green by two orders of magnitude.

## Defect 1 — `module-tests` emits a `test`-phase reactor request that can never resolve a sibling test-jar

`_maven_cmd_discover.py:810` generates the canonical unconditionally:

```python
cmd_map['module-tests'] = f'test{pl_arg}'   # pl_arg = ' -pl {module} -am'
```

`-am` ("also make") builds the module's upstream reactor dependencies, but only as far as the **requested phase**. A `test`-phase request stops at `test`; a `test-jar` artifact is attached at `package`. So when module B's tests consume module A's test-jar, `test -pl B -am` builds A only to `test`, never attaches A's test-jar, and B fails at **test discovery** — in classes the branch never touched.

Observed in `cuioss/TokenSheriff`: `token-sheriff-client`'s tests consume `token-sheriff-validation`'s test-jar. The resolved canonical

```text
mvn test -pl token-sheriff-client -am
```

fails with `ClassSelector [className = '…IdTokenValidationBridgeTest'] resolution failed`, plus `ClientSecretAuthTest` and `DiscoveryResolverTest` — none of them touched by the branch under test. The identical tree is green under any invocation that reaches `package`:

```text
mvn verify  -pl token-sheriff-client -am     # 660 surefire + 7 failsafe, all green, 154s
mvn install -pl token-sheriff-validation -am -DskipTests && mvn test -pl token-sheriff-client
```

**Why this is a truthful-signals defect, not just a build bug.** The failure is indistinguishable at the gate from a real regression: it is a non-zero exit from the module's own test command, so phase-5-execute routes it to triage unconditionally. Triage then has to spend a full dispatch establishing provenance to discover the code was never broken. In this plan that cost one leaf yield plus one ~176K-token triage dispatch — and it was set to recur on **six** further deliverables, all targeting the same module. The steady state is worse than the cost: an operator who accepts the signature once, to stop the noise, has disabled module-test verification for the rest of the plan, and a genuine regression then arrives wearing the same red.

There is **no project-side override**. The command string is generated live per resolve — it is absent from `marshal.json`, absent from `project-architecture/{module}/enriched.json` (whose `commands` key is null), and `build.map` only routes globs to a `build_class`, never to a command string. A project hitting this has no supported way to correct it; the only in-project workaround is to stop using the `module-tests` canonical entirely.

### Proposed action

Make the phase depend on what the module actually needs rather than emitting `test` unconditionally. Options, roughly in order of preference:

- When any reactor sibling contributes a `test-jar` to this module's test classpath, emit a phase that reaches `package` (`verify{pl_arg}`), or drop `-am` and require the upstream chain to be installed first. The sibling-test-jar dependency is visible in the POM at discovery time, so this is decidable without running a build.
- Failing that, expose a per-module command override that a project can set (`enriched.json.commands`, or a `marshal.json` map), so a project that hits this is not stuck with an uncorrectable canonical.
- Whichever path: the discovery step should not emit a canonical it can determine will fail.

## Defect 2 — the green-build parser reports only the LAST `Tests run:` summary line

The same corrected build reported:

```text
[EXEC] green build: analyses examined: compile, lint, test; 7 test(s) executed
tests_run: 7
tests_population: measured
```

The underlying Maven log for that identical run contains **two** summary lines, because `verify` runs Surefire and then Failsafe:

```text
[INFO] Tests run: 660, Failures: 0, Errors: 0, Skipped: 0     <- surefire (unit)
[INFO] Tests run: 7,   Failures: 0, Errors: 0, Skipped: 0     <- failsafe (IT)
```

667 tests ran; the signal said 7. The parser takes the last summary rather than summing the executions.

**Why this matters here specifically.** `tests_population: measured` asserts the number is a real measurement, not an estimate — so a consumer is entitled to trust it. A reviewer, a retrospective, or a coverage-trend check reading `tests_run: 7` for a module with 660 unit tests would reasonably conclude the suite had collapsed. The failure mode is the mirror of Defect 1: that one turns working code red, this one makes a thorough green look threadbare. Both corrupt the same decision.

It also silently punishes the correct fix. A project that works around Defect 1 by switching to `verify` gets a build that runs *strictly more* tests and reports *far fewer* — which reads as a regression and pushes the operator back toward the broken canonical.

### Proposed action

- Sum every `Tests run:` **summary** block in the log rather than taking the last, and report per-execution detail (surefire vs failsafe) where available.
- If a single figure must be reported, it should be the total; a partial count must not be labelled `tests_population: measured`.

## Evidence

- source: `_maven_cmd_discover.py:810` — `cmd_map['module-tests'] = f'test{pl_arg}'`, unconditional
- repro (red): `architecture resolve --module token-sheriff-client --command module-tests` -> `test -pl token-sheriff-client -am` -> discovery failure in three untouched classes
- repro (green): same tree, `verify -pl token-sheriff-client -am` -> `exit_code: 0`, 660 surefire + 7 failsafe, 154s
- provenance: `git log origin/main..HEAD` confirms the branch touched none of the failing classes
- parser: reported `tests_run: 7` against a log containing `Tests run: 660` and `Tests run: 7`
- override surface checked and absent: `marshal.json` (no command string), `project-architecture/token-sheriff-client/enriched.json` (`commands: null`), `build.map` (glob -> build_class only)
- downstream lesson filed in the consuming project: `2026-08-31-12-001`
- in-plan workaround applied: `plan.phase-5-execute.per_deliverable_build` switched from `default:verify:module-tests` to `default:verify:verify`
