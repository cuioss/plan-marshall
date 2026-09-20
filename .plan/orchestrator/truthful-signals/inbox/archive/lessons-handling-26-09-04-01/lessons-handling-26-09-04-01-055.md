envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:54Z

component=plan-marshall:build-maven
category=bug

# Green build reports analyses_examined='compile, lint, test' when tests_run=0

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report, and the SECOND such batch.**
Filed as lesson `2026-09-09-16-001` in **Token-Sheriff's** store, whose repo does not own the `plan-marshall`
bundle. Written here first and removed there second (integrate-then-remove).

⚠ **The pattern RECURRED.** Nine such lessons were relocated on 2026-09-09 and the mechanism was
reported as `-032`; PLAN-08 then routed its lessons correctly to the epic inbox, but PLAN-09 filed
these two into the local store again. So the `wrong_store` override is **not** reliably avoided —
it depends on which path a plan happens to take. That recurrence is itself the signal.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`, original id `2026-09-09-16-001`, created 2026-09-09.
Body verbatim below.

---

## Observation

The maven build wrapper's green-build summary line reports which analyses it
examined, and reports `tests_run` separately. When a build executes ZERO tests, the
summary still reads:

```
[EXEC] green build: analyses examined: compile, lint, test; 0 test(s) executed
status: success
tests_run: 0
tests_population: measured
analyses_examined: \"compile, lint, test\"
```

`analyses_examined` claims `test` was examined while `tests_run: 0` says nothing ran.
The two fields are adjacent and contradict each other. A reader — human or agent —
who takes `status: success` plus `analyses_examined` at face value records the build
as test-verified when no test executed.

Measured on plan `mtls-alpha-reclassification` (2026-09-09), three orchestrator-tier
builds via the marshalld daemon:

| Command | Duration | tests_run | Real test verification? |
|---|---|---|---|
| `verify -Ppre-commit` (whole tree) | 615s | **0** | NO — compile + lint only |
| `verify -pl token-sheriff-quarkus-parent/token-sheriff-client-quarkus -am` | 419s | 18 | yes |
| `verify -pl token-sheriff-quarkus-parent/token-sheriff-quarkus-integration-tests -am` | 519s | **0** | NO — Keycloak container fixture unavailable, ITs never ran |

Two of three \"green\" gates executed no tests, and nothing in the green line said so
except the `tests_run` field a reader has to notice independently.

`tests_population: measured` is the load-bearing detail: the wrapper did NOT fail to
count. It counted, and the count was zero. So the information needed to refuse the
false green is already present in the payload — it is the SUMMARY LINE that
misrepresents it.

## Why this matters here specifically

This is the false-green class the `lessons-handling-26-09-04-01` epic exists to
close — the same shape as its PLAN-01 (pre-commit gate truthfulness) and PLAN-12
(pre-commit gate cannot fail by construction). Those two plans addressed the gate's
construction; this is the reporting surface in front of it.

Two distinct causes produced the two zero-test rows, and the summary line is
identical for both, so the line cannot distinguish them:

1. **`-Ppre-commit` runs no tests.** There is no `skipTests` / `maven.test.skip` /
   `skipITs` in the root `pom.xml`, so this is not a local opt-out — the cause was
   not established and is worth establishing. Whatever the cause, a whole-tree
   \"quality gate\" that executes zero tests is compile-and-lint only, and calling it
   a quality gate oversells it.
2. **The integration-tests module needs a container fixture that was absent**, so
   Failsafe ran nothing. A missing fixture is an environmental gap, not a pass —
   but the build is green and the summary says `test` was examined.

## Directive

Make the green-build summary line and the structured payload agree:

- When `tests_run == 0` AND `tests_population == measured`, do NOT list `test` in
  `analyses_examined`. A test analysis that examined nothing was not performed.
- Emit an explicit discriminator for the zero-test case rather than leaving the
  reader to cross-check `tests_run` against `analyses_examined` — e.g. a
  `test_verification: none | partial | full` field, so a consumer can refuse a
  vacuous green on one field rather than on an inference across two.
- Distinguish \"the command runs no tests by construction\" from \"tests were
  configured but the fixture/environment prevented them running\". These are
  different verdicts with different remedies, and today they render identically.

⚠ Do NOT fix this by making a zero-test build fail. Some commands legitimately run
no tests (`compile`, a docs-only lane). The defect is the summary CLAIMING a test
analysis it did not perform, not the absence of tests.

## Consumer-side rule until fixed

Never record a build as test-verified on `status: success` alone. Read `tests_run`,
and treat `tests_run: 0` with `tests_population: measured` as \"no test evidence\" —
regardless of what `analyses_examined` claims.
