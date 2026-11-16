# PLAN-LB-156: The Maven root aggregator `module-tests` canonical satisfies a member's sibling test artifact

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

A root `pom` aggregator gets `module-tests: test` and `test-compile: test-compile` unconditionally once the reactor holds a test file, while the per-module ladder switches to `package` for a module that consumes a reactor test artifact and excludes the root. At the `test` phase a sibling's classified artifact is not attached, so a reactor-root `mvn test` fails to compile a consumer even though the whole-tree `verify` is green. Make the root canonical apply the same rule the per-module ladder already knows.

## Deliverables

1. `_add_reactor_test_canonicals` emits `package` and `package -DskipTests` for `module-tests` and `test-compile` when any member of the reactor consumes a reactor test artifact, and keeps `test` / `test-compile` otherwise. The decision reuses the same reactor-test-artifact detection the per-module ladder uses, so the two cannot disagree.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
2. Tests cover a reactor with no consuming member (still `test`), one member consuming a classified sibling artifact (`package`), one consuming a `test-jar`-type dependency, a nested aggregator (unchanged) and a single-module root (unchanged); the outline settles from the fixtures whether the `test-jar`-type form also needs `package`.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- A root canonical that would run nothing stays absent (the existing no-test-file rule).
- No Maven run against a real consumer is required; fixtures assert the emitted canonical.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.

## Claim Labels

- OBSERVED: a root `pom` aggregator at the project root gets `{'module-tests': 'test', 'test-compile': 'test-compile'}` with no test-artifact check — read at `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` lines 454-482 (re-read at HEAD).
- OBSERVED: the per-module ladder uses `package` when `has_tests and consumes_reactor_test_artifact and not is_root_module` — same file, lines 1248-1259 (re-read at HEAD).
- OBSERVED (leaf reading, not re-read): `_reactor_test_artifacts` is applied per module only; PLAN-LB-121 and #1921 cover the per-module ladder and the root's test population, not the root aggregator's consumers.
- HYPOTHESIS: a dependency declared with `<type>test-jar</type>` resolves at the `test` phase via `target/test-classes` and only the classifier form needs `package` — confirm/refute at `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` lines 1222-1231 and the fixtures (verify-at-outline).
- Verify-first clause: the outline settles the test-jar versus classifier trigger before choosing whether the root switches on any consuming member or only on the classifier form.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py`
- HYPOTHESIS: `test/plan-marshall/build-maven/` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none staged.
- Adjacent to: `PLAN-LB-110`, `-121` and `-124` (shipped) touched the Maven canonicals; their behaviour stays untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-156-maven-root-aggregator-test-artifact-ladder.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
