envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-16T07:45:20Z

# The reactor-root `module-tests` canonical is plain `mvn test` and cannot resolve a sibling test-jar

**Severity:** high (operator grade, 2026-11-16 `gather` run; the grading leaf had it BORDERLINE high/medium)
**Bundle:** plan-marshall (`build-maven`)
**Checked at:** `ee019bf1d` (origin/main), re-read by the orchestrator

## What was reported

TokenSheriff lesson `2026-11-13-06-005` (relayed from the API-Sheriff epic `api-sheriff-seams`, message `plan-05-validation-public-seams-001`): in plan `validation-public-seams` (PR #899) the phase-5 module-tests step resolved to plain `mvn test` over the whole reactor. The `test` phase never packages the validation module's test-jar, so `token-sheriff-client` (test) and `benchmark-core` (main) failed to compile. 2577 tests passed before the reactor stopped. All seven failing paths were outside the plan footprint, and the Q-Gate finding was rejected as "not a plan defect" because the whole-tree `verify -Ppre-commit` was green on the same HEAD. The pre-push gate later hit the same failure. The consumer's repair was `<type>test-jar</type>` on the consuming dependencies in four poms (commit 62b7f847, disclosed in PR #899); the build-maven canonical was not fixed.

Lesson's own ask: resolve the reactor `module-tests` canonical to a phase that satisfies test-jar consumers, or have the script report the unsatisfiable consumer instead of a compile failure.

## Ground truth at the checked commit

`marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py`:

- `:1254-1256` the per-module ladder switches `module-tests` to `package` for a module that consumes a reactor test artifact, but the condition is `has_tests and consumes_reactor_test_artifact and not is_root_module`, so the root is excluded.
- `:454-482` `_add_reactor_test_canonicals` gives a root `pom` aggregator `module-tests: test` and `test-compile: test-compile` unconditionally once the reactor holds a test file. It has no test-artifact check. Its docstring says `mvn test` at the reactor root runs the tests of the modules the root builds.
- `:1222-1231` the code's own comment says a sibling's classified or `test-jar` artifact is attached only from `package` on. At an earlier phase Maven 3.9 falls back to the sibling's `target/test-classes` for a `test-jar` / `tests` dependency and to `target/classes` for any other classifier, which lacks the test classes.

So the per-module path knows the rule and the root-aggregator path does not apply it.

## Not verified

- No Maven run. Whether a dependency declared with `<type>test-jar</type>` also fails under a root `mvn test`, or only a classifier-form dependency does, is open. The comment at `:1224-1229` suggests the `test-jar`-type form can resolve at `test`, so the trigger may be the classifier form. The consumer's repair added the type to its dependencies, which fits the classifier-form reading.
- The consumer's POMs were not read.
- The leaf found no existing filing or plan for a root aggregator whose member consumes a sibling test artifact. PLAN-LB-13 D1, PLAN-LB-28, PLAN-LB-110 D2, PLAN-LB-121 D1 and PLAN-LB-124 D3 touch the Maven canonicals (not re-read).

## Source

- TokenSheriff lesson `2026-11-13-06-005`, archived verbatim at `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-16/TokenSheriff/2026-11-13-06-005.md`.
