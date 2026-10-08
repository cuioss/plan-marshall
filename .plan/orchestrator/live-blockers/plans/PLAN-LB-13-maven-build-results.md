# PLAN-LB-13: Maven build results are wrong in consumer repos

epic: live-blockers
workstream: WS-02

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-28 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-13-maven-build-results.md` and is queued as one row file, `queue/PLAN-LB-13.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Fix three defects in the Maven build path that every Java consumer repository hits. The generated
`module-tests` (and `test-compile`) command stops before the `package` phase, so a module whose tests
use a sibling module's test-jar fails although its code is fine. The result parser reports only the
last `Tests run:` line of the log, so a green `verify` over 724 unit tests reads as 7 (or as 0) while
being stamped `tests_population: measured`. The category pattern `'[deprecation]'` is compiled as a
regex character class, so nearly every unclassified `[ERROR]` line — including Maven's failure
epilogue — is filed as a blocking `deprecation_warning` finding. All three produce a signal an agent
cannot tell from a real regression, and each has cost repeated triage rounds in TokenSheriff, API-Sheriff
and cui-http. Carries forward truthful-signals PLAN-TRUTH-122 D1 and D3 with its "new root cause" fold,
and truthful-signals PLAN-TRUTH-150 D3 and D5 with its "trailer advice filed as blocking errors" fold.

## Deliverables

1. **The Maven test ladder reaches `package` when the module consumes a reactor sibling's test-jar.**
   `_build_commands` emits `test-compile -pl X -am` and `test -pl X -am` for every non-pom module with
   tests. `-am` builds upstream modules only as far as the requested phase, and a test-jar is attached
   at `package`, so the sibling's test-jar is never produced. Discovery must read, from the module's
   POM and without running Maven, whether the module declares a dependency of `<type>test-jar</type>`
   (or a classified test artifact) on another module of the same reactor, and for such a module emit
   test-ladder commands whose phase reaches `package` (for example `verify -pl X -am`, or a `package`
   prerequisite). Modules without such a dependency keep today's commands unchanged. Because
   `architecture derive-verification` and the phase-4 task stamp resolve through the same command map,
   the fix must be visible there too. Done when: a new multi-module fixture in which module B depends on
   module A's test-jar yields a `module-tests` and `test-compile` command for B that no longer stops at
   the `test` / `test-compile` phase, the same fixture's module A (no test-jar dependency) still yields
   `test -pl A -am`, and a `derive-verification` test over a test file in B returns the corrected
   executables. The first assertion fails at HEAD.

2. **`tests_run` counts every summary block of the run, and names the plugin each count came from.**
   `_extract_test_summary` takes the last regex match. A `verify` run prints a Surefire summary and
   then a Failsafe summary, and a multi-module reactor prints one summary per module, so the last match
   is one block out of several. The parser must sum the summary blocks across modules and across
   Surefire and Failsafe, must not count the per-class `Tests run: …, Time elapsed: … -- in Class`
   lines (the same regex matches them, so a naive sum over-counts), and must expose the Surefire and
   Failsafe totals separately in the result. When the parser cannot tell summary lines from per-class
   lines in a log, the result must say `tests_population: unmeasured` rather than report a partial
   number as measured. Done when: tests over new log fixtures — (a) one module, Surefire 724 then
   Failsafe 7, (b) a three-module reactor with different per-module totals, (c) Surefire followed by a
   Failsafe block of 0 — assert the summed total and the separate plugin totals, each expected value is
   computed in the test from the summary blocks present in the fixture, and each test asserts the
   fixture contains more than one summary block. All three fail at HEAD (7, last module's total, and 0).

3. **Bracketed javac tags are matched as literal text.** `'[deprecation]'` and `'[unchecked]'` in
   `JVM_BASE_PATTERNS` contain `[` and `]`, so `_is_regex_pattern` sends them to `re.search`, where
   `[deprecation]` matches any single one of the letters d, e, p, r, c, a, t, i, o, n. Since
   `deprecation_warning` is checked before `unchecked_warning` and `openrewrite_info`, almost any
   message that no earlier category claimed is labelled `deprecation_warning`. The Maven pattern set
   must match these two tags literally (the Gradle set already escapes them). Done when: a test asserts
   that `categorize_issue('Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin',
   MAVEN_PATTERNS)` is not `deprecation_warning`, that a real `[deprecation] foo() in Bar has been
   deprecated` line is, that a `[unchecked]` line is `unchecked_warning`, and a population test walks
   every pattern in `MAVEN_PATTERNS` and fails on any that contains an unescaped `[` yet is meant as
   literal text. The first assertion fails at HEAD.

4. **Maven's failure epilogue and passing test-summary lines are not filed as findings.** After a
   failed build Maven prints fixed advice on `[ERROR]` lines (`Re-run Maven using the -X switch`,
   `To see the full stack trace…`, `For more information about the errors…`, `[Help 1] http://…`,
   `After correcting the problems, you can resume the build with the command`,
   `mvn <args> -rf :module`, `See dump files…`, `Please refer to …/surefire-reports`). `_extract_issues`
   turns each into a severity-`error` issue, and each becomes a pending `build-error` finding that
   blocks finalize until someone suppresses it by hand. The `'tests run:'` substring pattern likewise
   files a summary line with `Failures: 0, Errors: 0` as a `test_failure`. `_extract_issues` must drop
   the epilogue advice lines and must not file a test-summary line whose failure and error counts are
   both zero. Done when: a test over a new failing-build log fixture carrying the full epilogue and one
   real compiler error asserts that exactly the real diagnostics are returned and none of the advice
   lines is, and a test over a `[WARNING] Tests run: 27, Failures: 0, Errors: 0, Skipped: 1` line
   asserts no `test_failure` issue. Both fail at HEAD.

## Claim Labels

- OBSERVED: `module-tests` is emitted as `test{pl_arg}` and `test-compile` as `test-compile{pl_arg}` with `pl_arg = ' -pl {relative_path} -am'` for every non-pom module that has tests; nothing in `_build_commands` checks whether the phase is sufficient — read at `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py:787,808-810`
- OBSERVED: the code comment above `pl_arg` claims `-am` makes "an intra-reactor test-jar resolve on a clean checkout", which is the false premise the defect rests on — read at `_maven_cmd_discover.py:782-786`
- OBSERVED: `_maven_cmd_discover.py` contains no handling of `test-jar`, `<type>` or `classifier`; the dependency parser reads `dependency:tree` output and discards the type field (`# type = match.group(3) … not needed`) — read at `_maven_cmd_discover.py:702-737`
- OBSERVED: `_build_commands` has two callers: discovery (`_maven_cmd_discover.py:307`) and the profile enrichment in `manage-architecture/scripts/_cmd_client_query.py:136` § `_enrich_module_commands`, which rebuilds the map and overlays it with `merged.update(...)` at `:146-147`; a fix inside `_build_commands` covers both only if both callers pass the test-jar fact in
- OBSERVED: `derive-verification` builds no command string of its own; for build class `module-tests` it resolves the two verbs `test-compile` and `module-tests` through `resolve_command` and returns their executables, so it emits the same `test-compile -pl X -am` and `test -pl X -am` as the command map — read at `manage-architecture/scripts/_cmd_client_handlers.py:475-492,544-553`
- OBSERVED: the phase-4 task deriver is not a separate emitter; it stamps `verification.commands` from the rows `architecture derive-verification` returns — read at `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:594-602`; a search of `phase-4-plan/`, `manage-tasks/` and `manage-architecture/` for a literal `-am` finds only two documentation examples at `manage-architecture/standards/client-api.md:580,595`
- OBSERVED: existing tests pin `-pl … -am` on `module-tests` and `test-compile` as required behaviour and must be updated, not deleted — read at `test/plan-marshall/build-maven/test_discover_modules.py:549-598`
- OBSERVED: the Maven summary extractor takes `m = matches[-1]` over the pattern `Tests run:\s*(\d+),\s*Failures:…Skipped:\s*(\d+)`, which matches per-class lines as well as summary lines — read at `build-maven/scripts/_maven_cmd_parse.py:151-176`
- OBSERVED: a non-`None` parsed total is stamped `tests_population: measured` — read at `script-shared/scripts/build/_build_shared.py:836-876`
- OBSERVED: no test names Failsafe or a second summary block: `failsafe` (any case) has zero matches in `test/plan-marshall/build-maven/test_maven_cmd_parse.py` and `test/plan-marshall/script-shared/test_build_parse.py`
- OBSERVED: `JVM_BASE_PATTERNS['deprecation_warning']` carries the literal `'[deprecation]'` and `['unchecked_warning']` carries `'[unchecked]'` — read at `script-shared/scripts/build/_build_jvm_patterns.py:53-60`; `_is_regex_pattern` returns true for any pattern containing `[` or `]` and `categorize_issue` then calls `re.search(pattern, message, re.IGNORECASE)` — read at `script-shared/scripts/build/_build_parse.py:476-490`
- OBSERVED: `MAVEN_PATTERNS` overrides only `openrewrite_info`, so Maven inherits both bracket patterns unescaped, while `GRADLE_PATTERNS` overrides them with `r'\[deprecation\]'` and `r'\[unchecked\]'` — read at `build-maven/scripts/_maven_cmd_parse.py:37-47` and `build-gradle/scripts/_gradle_cmd_parse.py:85-94`; the defect is Maven-only in effect
- OBSERVED: the one existing deprecation test asserts only `len(deprecation) >= 1`, which the character-class match satisfies for the wrong reason — read at `test/plan-marshall/build-maven/test_maven_cmd_parse.py:138-140`
- OBSERVED: `_extract_issues` files every line containing `[ERROR]` or `[WARNING]` except empty messages, `->` continuations and stack-trace lines; there is no epilogue filter — read at `build-maven/scripts/_maven_cmd_parse.py:89-135`; the base pattern `'tests run:'` under `test_failure` is a plain substring — read at `_build_jvm_patterns.py:32-38`
- OBSERVED: a category containing neither `test` nor `lint`/`style` becomes a `build-error` finding, and severity `error` is carried through — read at `script-shared/scripts/build/_build_shared.py:283-309`
- HYPOTHESIS: Maven attaches a test-jar only at `package`, and a reactor run stopped at `test` cannot resolve a sibling's `test-jar` or custom-classifier artifact from `target/test-classes` in the Maven versions the consumer repos use — confirm/refute with a real two-module fixture run under the consumers' Maven wrapper version, and at `build-maven/standards/maven-impl.md` § command options (verify-at-outline)
- HYPOTHESIS: the reported consumer figures (TokenSheriff: `test` 724 against `verify` 7 on one tree; a 15-module reactor with 3,083 tests reported as 0; API-Sheriff: 202 reported for a module that runs 1,886) are other repositories' observations and were not re-run here — confirm/refute by parsing a captured `verify` log from `/Users/oliver/git/TokenSheriff` or `/Users/oliver/git/API-Sheriff` through `_maven_cmd_parse.py` § `parse_log` (verify-at-outline)
- HYPOTHESIS: under `-T1C` parallel reactor builds the per-module summary blocks interleave with other modules' output but each summary line stays intact, so line-based block detection still works — confirm/refute against a captured parallel-build log and at `_maven_cmd_parse.py` § `_extract_test_summary` (verify-at-outline)
- HYPOTHESIS: the daemon-routed path can supply `routed_tests_run`, which wins over the parsed total, so a routed Maven build may report a count this plan's parser fix does not reach — confirm/refute at `script-shared/scripts/build/_build_shared.py` § `cmd_run_common` (the `routed_total` branch) and the daemon's Maven count source (verify-at-outline)
- Verify-first clause: before scoping deliverable 1, settle which replacement command is emitted. `verify -pl X -am` also runs Failsafe integration tests and any plugin bound after `test`, which changes what `module-tests` costs and means; a two-step `install -DskipTests` then `test -pl X` writes to the local repository. Pick one, state the cost, and record the choice in `build-maven/standards/maven-impl.md`. If the POM cannot tell a reactor-sibling test-jar from an external one without running Maven, loop back and re-scope the detection rule.
- Verify-first clause: before scoping deliverable 2, read the landing of the earlier `tests_run: 0` fix (the `tests_population` discriminator in `_build_shared.py`) so the new summed count and the `measured` / `unmeasured` label keep one meaning.
- Verify-first clause: before scoping deliverable 4, derive the epilogue line set from real failing logs of at least two Maven versions rather than from the list in this spec; the list above is a floor.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` — `_build_commands` test-ladder emission, the POM parse that must learn the test-jar dependency, and the false comment above `pl_arg`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py` — `_extract_test_summary`, `_extract_issues` and `MAVEN_PATTERNS`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_jvm_patterns.py` — the `'[deprecation]'` and `'[unchecked]'` literals and the `'tests run:'` pattern
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — `_enrich_module_commands`, the second caller of `_build_commands`, which must pass the test-jar fact
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py` — `_is_regex_pattern` / `categorize_issue`, touched only if the literal-bracket fix is made in the matcher instead of in the pattern list; `UnitTestSummary`, touched only if the per-plugin totals are carried on it (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — the green-build result fields, touched only if the Surefire and Failsafe totals are emitted as new result keys (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — the documented canonical commands and the finding-type table
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md` — the `-pl` / `-am` command contract
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` — two examples showing `test -pl <module> -am` as the resolved `module-tests` executable
- OBSERVED: `test/plan-marshall/build-maven/test_discover_modules.py` — existing `-am` pins on the test ladder, plus the new test-jar cases
- OBSERVED: `test/plan-marshall/build-maven/test_maven_cmd_parse.py` — summary-count, category and epilogue tests
- OBSERVED: `test/plan-marshall/build-maven/fixtures/` — new log fixtures and a multi-module project fixture with a sibling test-jar
- OBSERVED: `test/plan-marshall/manage-architecture/test_derive_verification.py` — the downstream assertion that the corrected executables are what `derive-verification` returns
- HYPOTHESIS: `test/plan-marshall/script-shared/test_build_parse.py` — touched only if `_build_parse.py` changes (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-12 (`PLAN-LB-12-build-timeout-and-verify-budget.md`) ranges over `script-shared/scripts/build/*`; this plan touches `_build_jvm_patterns.py` there for certain and `_build_parse.py` / `_build_shared.py` only conditionally. Sequence the two if PLAN-LB-12 edits `_build_shared.py` § `cmd_run_common`.
- Adjacent to: `build-gradle/scripts/_gradle_cmd_parse.py` — already escapes the bracket patterns and calls the shared `extract_test_summary`; untouched. The shared helper's `matches[-1]` at `_build_parse.py:624` and its docstring claim that "the final one is the aggregate" are the same premise for Gradle, npm and pytest; whether it is wrong for those tools is not settled here.
- Adjacent to: `phase-4-plan/SKILL.md` and `manage-architecture/scripts/_cmd_client_handlers.py` § `cmd_derive_verification` — both consume the command map and need no change of their own; only a test is added on the deriver.
- Left out on purpose: a project-side override for a generated canonical (PLAN-TRUTH-122 D2 / PLAN-TRUTH-150 D4), which is unnecessary once the generated command is correct; the population sweep of every parser's last-match premise (PLAN-TRUTH-122 D0); `-Dsurefire.failIfNoSpecifiedTests=false` for a targeted `-Dtest` riding `-am`; the pre-push gate's whole-tree widening that strips `-pl` and `-am` together (`phase-6-finalize/standards/pre-push-quality-gate.md`); one test failure being filed at several granularities; and the CI and `files_exist` items folded into PLAN-TRUTH-150.
- Foreign-repo work: none required. TokenSheriff and API-Sheriff (`/Users/oliver/git/TokenSheriff`, `/Users/oliver/git/API-Sheriff`) are the places to capture real logs for fixtures and to confirm the fix after the harness sync; no change is made in them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-13-maven-build-results.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
