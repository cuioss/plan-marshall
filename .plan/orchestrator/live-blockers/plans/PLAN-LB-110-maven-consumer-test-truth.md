# PLAN-LB-110: A Maven consumer's test results read true — the parser files only diagnostics, the reactor root resolves its tests, and a selector that matched nothing is never green

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-110-maven-consumer-test-truth.md` and is queued as one row file, `queue/PLAN-LB-110.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's instruction of 2026-11-02 ("stage the corresponding plans, aggregate where sensible"). Sources:
> - inbox `lessons-routing-061` (high, operator ruling), together with the related medium lesson `2026-10-12-07-006`;
> - `lessons-routing-058` item 3 (high, inherited), a recurrence of `-031`, which PLAN-LB-58 D3 (#1866) last owned;
> - `lessons-routing-070` item 4, the Surefire `-Dtest` grammar, used only where plan-marshall itself decides how a selector's
>   result is read.
>
> The plan also absorbs the "epilogue header lines still filed" gap in the Open Defect "PLAN-LB-28's test ladder needs discovery
> re-run", and the medium Open Defect "a Maven consumer's task-time gate cannot reach the new Maven scope verb" (D4, which is
> droppable). Every source rests on runs in API-Sheriff, a Maven project, and each claim below was re-read at HEAD of `main`.

## Objective

In a Maven consumer, three build signals report something other than what the build did:

- **The log parser files non-diagnostics.** It files Maven's own failure-epilogue header lines (`Failures:`,
  `COMPILATION ERROR :`) and the compiler's `symbol:` / `location:` continuation lines as separate issues. Each one becomes a
  finding to triage.
- **The pre-push gate records `module-tests` as DEGRADED although every test ran.** The whole-tree `verify` on a Maven reactor
  runs every test. But the reactor root (a `pom` aggregator) has no `module-tests` or `test-compile` canonical, so the gate's
  default-scope resolve finds no target.
- **A Surefire `-Dtest` selector that matches nothing is misreported.** It either fails like a test failure or, with
  `failIfNoSpecifiedTests=false`, passes with zero tests.

This plan makes the parser file only diagnostics, and gives a Maven reactor root its test canonicals so the gate's module-tests
arm runs. A selector that matched nothing becomes a named error and never a green. The originally reported false positive, a
passing Surefire class summary with `Skipped` above zero, is already fixed at HEAD; this plan only pins it with the consumer's
exact line.

## Deliverables

1. **The Maven parser files diagnostics only.** It files no epilogue header line and no orphaned continuation line, and the
   consumer's passing line gets a pinned regression.
   - `Failures:` and `Errors:` (Surefire's results-section headers) and `COMPILATION ERROR :` (the compiler plugin's banner) are
     not issues. They are matched with `fullmatch` against the message after its prefix is stripped, like the existing
     `_MAVEN_EPILOGUE_PATTERNS`. A reworded line is therefore filed again (fail-visible).
   - The compiler's `symbol:` and `location:` lines that follow a compiler error are attached to that error as its detail, not
     filed as issues of their own. They cannot be dropped, because they carry the missing name. When no compiler error precedes
     them, they stay filed (fail-visible).
   - A fixture line in the consumer's exact shape is not filed: `[WARNING] Tests run: 10, Failures: 0, Errors: 0, Skipped: 1,
     Time elapsed: … s -- in Awaits`. Its simple class name does not end in `Test`. This pins behaviour that #1750 already
     shipped: it is labelled `order: none`, because it passes at the base, and it is not presented as a fix.
   - In `test_maven_cmd_parse.py`, the expected diagnostic lists of the two epilogue fixtures (`_MAVEN3_DIAGNOSTICS`,
     `_MAVEN4_DIAGNOSTICS`) currently pin the defect. They are rewritten to the real diagnostics, and the PR states the change as
     a test correction rather than hiding it inside a fix commit.

   *Done when:* all of the following hold.
   - For both the Maven 3.9 and the Maven 4 fixture, `test_failure_epilogue_is_not_filed_and_real_diagnostics_are` asserts that:
     - `Failures:` and `COMPILATION ERROR :` are not filed;
     - the `cannot find symbol` issue carries `symbol:   class Missing` and `location: class probe.c.Broken` in its detail;
     - neither line is an issue of its own.

     The rewritten assertion is red at the worktree base.
   - A control test shows that a `symbol:` line with no preceding compiler error is still filed.
   - The existing control `test_control_failing_test_count_line_is_still_filed` stays green.
   - The consumer-line pin passes at the base and is labelled as a pin.

2. **A Maven reactor root resolves `module-tests` and `test-compile`, so the pre-push gate's module-tests arm runs instead of
   recording DEGRADED.**
   - `_build_commands` gives a root `pom` aggregator `module-tests` = `test` and `test-compile` = `test-compile` (whole reactor,
     no `-pl`) when at least one reactor module has tests. A reactor with no test module gets neither, so the project still has
     no false canonical. A non-root module and a single-module `jar` root keep today's entries unchanged.
   - The consumer-visible set this changes is below, one check each. The outline confirms the population with a content search
     for the consumers of `module-tests` and `test-compile`.
     - (a) The pre-push step 0 default-scope `resolve --command module-tests` now succeeds and reaches build-maven's
       `resolve-test-scope`.
     - (b) The whole-tree `test-compile` default-scope probe succeeds, so Maven no longer reaches the `-pl`-removal fallback.
     - (c) `derive-verification` for a path the root owns (`pom.xml`) still derives `verify`, unchanged.
     - (d) The scoped branch 6 still re-resolves per module (`test -pl X -am`, or the `package` ladder), unchanged.
   - The DEGRADED warnings in `pre-push-quality-gate.md` § "Whole-tree module-tests divergence gate" step 0 say "NO pytest ran" /
     "no pytest could be run". They are reworded to name the project's test run neutrally, and to state the cause (no canonical,
     or no scope verb) rather than a coverage gap.

   *Done when:* all of the following hold.
   - A discovery test over a fixture reactor (a root `pom` plus one `jar` module with `src/test`) asserts the root's
     `module-tests` and `test-compile` executables. It is red at the worktree base.
   - A second fixture, with no test module, asserts that neither key is present.
   - A third fixture asserts that a single-module `jar` root is unchanged.
   - A test over a Maven-shaped persisted architecture shows step 0 resolving and the arm reaching `resolve-test-scope`, not the
     DEGRADED branch. It is a gate-level test, or a doc-contract test if the arm is prose only.
   - The PR states that a consumer sees the change only after `architecture discover` is re-run there, because the command map
     is persisted at discovery.

3. **A Surefire selector that matched nothing is a named command error, never a test failure and never a green.**
   - A Maven run whose log carries Surefire's goal failure `No tests matching pattern … were executed` returns a named reason
     that names the selector (for example `test_selector_matched_nothing`). It files no `test-failure` finding.
   - A Maven run whose command carries `-Dtest=` and whose parsed summary executed zero tests does not report `success`. This is
     the `-Dsurefire.failIfNoSpecifiedTests=false` case. It reports the same named reason under the five-valued status contract,
     as `error`, or as `indeterminate` if the outline shows that `error` would break a consumer. The choice is recorded.
   - `build-maven/SKILL.md` states the selector grammar once. Classes are separated by commas, and a method goes after `#`. A list
     joined with `+` is one pattern, and it matches nothing. Nothing else in the corpus restates the grammar.

   *Done when:* three log-fixture tests, each red at the worktree base, cover the following, and a guard test pins the SKILL.md
   grammar sentence.
   - The `No tests matching pattern` failure yields the named reason and no test-failure issue.
   - A `-Dtest` run with zero executed tests is not `success`.
   - A control `-Dtest` run with at least one executed test stays `success`.

4. **The per-task gate reaches the resolved build skill's `resolve-test-scope`, not a hard-coded pyproject notation.**
   (Medium Open Defect; drop first.)
   - A content search finds `execute-task/SKILL.md` naming `plan-marshall:build-pyproject:pyproject_build resolve-test-scope`
     literally in two places. The text instead derives the notation from the resolved `module-tests` executable, the way the
     pre-push gate step 0 does, so a Maven task reaches build-maven's verb.

   *Done when:* a doc-contract test asserts two things: that `execute-task/SKILL.md` carries no literal
   `build-pyproject:pyproject_build resolve-test-scope`, and that it names the derivation from the resolved executable. The test
   is red at the worktree base.

Split guard: one theme, Maven test truth. Each deliverable has its own Done-when and must not be merged with another in the
outline. D4 is medium and drops first. D3 drops second, if the outline finds that the zero-test check needs a change to the shared
result contract.

## Standing Constraints

- **Focus rule: high and blocking only.** D4 is carried as droppable.
- **Sonar is not enabled for this project and is ignored.** Collect no Sonar figure and require none.
- **Maven-only change.** Do not alter `JVM_BASE_PATTERNS` in `_build_jvm_patterns.py`, because Gradle shares it. Override or filter
  in `_maven_cmd_parse.py` / `MAVEN_PATTERNS` instead. A change that would also move Gradle needs its own evidence.
- **Shared build code stays untouched by default.** Do not touch build-pyproject behaviour, `_test_scope_divergence.py`, or the
  shared result contract `cmd_run_common`, unless the D3 outline shows that the zero-test check cannot live in build-maven. In that
  case, record why and keep the shared change to the one reason value.
- **No real Maven invocation.** None is needed or wanted. Every new test is a log fixture or a POM fixture. A new fixture states
  which Maven / Surefire version it reproduces, as the existing epilogue fixtures do.
- **Test ordering labels.**
  - Every test that is red at the base carries `order: test-first`.
  - A pin that passes at the base carries `order: none`.
  - A rewritten existing assertion is disclosed as a test correction.
- **Every new or changed test states what it protects.** A gate-level claim goes through the real resolver over a persisted fixture
  architecture, not a stub that would pass at HEAD.

## Claim Labels

- OBSERVED: the parser already skips a passing count line. `_is_passing_test_count` (`_maven_cmd_parse.py` L80-83) returns true when Failures and Errors are both 0, whatever Skipped is, and `_extract_issues` skips it at L154. The regex `_TESTS_RUN_PATTERN` (L192) matches the consumer's line, including the `Time elapsed … -- in Awaits` form.
- OBSERVED: the fix predates the run the consumer lesson came from. `git log -L80,83` names only `2fd164ec9` (#1750, 2026-10-10), and the lesson's findings e6b5d8 / bab3b4 are stamped 2026-10-07. The headline of `lessons-routing-061` is therefore refuted at HEAD, and survives only as a regression pin.
- OBSERVED: existing coverage of the passing line is a synthetic summary form (`test_passing_test_count_line_is_not_a_test_failure`, `test_maven_cmd_parse.py` L664-673), plus the epilogue fixtures' `Tests run: 2, … Skipped: 1, Time elapsed … -- in probe.a.ATest` in `_MAVEN3_NOT_FILED` / `_MAVEN4_NOT_FILED` (L578, L592). No case has a class name without the `Test` suffix.
- OBSERVED: the test pins the epilogue-header defect. `_MAVEN3_DIAGNOSTICS` and `_MAVEN4_DIAGNOSTICS` (L547-559, L562-574) list `'Failures:'`, `'COMPILATION ERROR :'`, `'symbol:   class Missing'` and `'location: class probe.c.Broken'` as expected issues, and L641 asserts `messages == diagnostics`.
- OBSERVED: the shared JVM `test_failure` patterns include the substring `'tests run:'` (`_build_jvm_patterns.py` L36-42), and Gradle uses the same base. This is why the change is Maven-only.
- OBSERVED: a `pom` module gets no test canonicals. In `_build_commands` (`_maven_cmd_discover.py` L935-943), `module-tests` and `test-compile` are set only when `packaging != 'pom'` and `has_tests`. A root module gets no `-pl` (L906-919).
- OBSERVED: the pre-push gate resolves `module-tests` at default scope first. A `Command not found` shape there takes the "No module-tests canonical resolves" WARNING plus the module-tests DEGRADED detail (`pre-push-quality-gate.md` L427-450). Both WARNING texts say "pytest" (L439, L447).
- OBSERVED: build-maven publishes `resolve-test-scope` (`maven.py` L99-122, registered at L142; `_maven_cmd_resolve_scope.py`, added by `8c08b6126`, #1866). The "argument-parser rejection" half of lesson `2026-10-12-16-008` predates it and is refuted at HEAD. What remains is the missing default-scope canonical.
- OBSERVED: no plan-marshall script composes a `-Dtest` selector. A literal content search for `-Dtest` finds only `manage-tasks/standards/task-contract.md` (L517, a single-class example), `pm-dev-java/.../junit-core/standards/test-fork-policy.md` and one outline test. A selector reaches a task as LLM-authored outline text that phase-4 copies verbatim (`task-contract.md` L88, L467).
- OBSERVED: lesson `2026-10-05-13-001` reports that a selector joined with `+` fails with "No tests matching pattern", and that `-Dsurefire.failIfNoSpecifiedTests=false` turns a wrong selector into a pass with zero tests.
- OBSERVED: a content search finds `execute-task/SKILL.md` carrying the literal `build-pyproject:pyproject_build resolve-test-scope` twice. This matches the epic's medium Open Defect "a Maven consumer's task-time gate cannot reach the new Maven scope verb".
- HYPOTHESIS: the architecture's default-scope `resolve` (no `--module`) answers from the Maven reactor root module — confirm at `manage-architecture/scripts/_cmd_client_handlers.py` § `cmd_resolve` default-module lookup, and against a persisted fixture reactor (verify-at-outline).
- HYPOTHESIS: the `-pl`-removal widening in the `test-compile` fallback (`pre-push-quality-gate.md` L393-402) turns Maven's `test-compile -pl X -am` into a malformed `test-compile -am` — confirm by applying the documented rule to the resolved string (verify-at-outline). If this is true, D2 removes the only Maven path into it.
- HYPOTHESIS: no Maven parse path reads the command, so D3's zero-executed check needs the command handed to the parser (`parser_needs_command`, `_build_shared.cmd_parse_common`), or a check in the run path of `_maven_execute.py` — confirm at `_maven_execute.py` § `cmd_run` and `_build_shared.cmd_run_common` (verify-at-outline).
- HYPOTHESIS: `Failures:` and `COMPILATION ERROR :` fall into no named category and are filed as generic build errors, not as `test_failure` — confirm with `categorize_issue(…, MAVEN_PATTERNS)` (verify-at-outline). This changes only the finding type, not D1.
- HYPOTHESIS: `architecture resolve --narrow-unit` on a Maven module either refuses or composes an invalid `-pl` form. Its tests cover pyproject only (`test_cmd_resolve_narrow_target.py` L44-58) — confirm at `_cmd_client_handlers.py` § narrow-unit branch (verify-at-outline). If it does compose a selector, the outline reports that as a D3 finding and does not fix it here.
- Verify-first clause (D2): before editing, resolve `module-tests` and `test-compile` at default scope over a persisted fixture reactor (a root `pom` plus a module with tests), and record the `Command not found` shape. If either resolves at the base, the DEGRADED premise is refuted at its centre: loop back and re-scope D2 to the warning text only.
- Verify-first clause (D3): run the D3 fixtures at the base. If the zero-executed `-Dtest` run is already not `success`, D3 narrows to the named reason and the SKILL.md sentence.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py` — epilogue headers, continuation attachment (D1), selector-miss reason (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` — `_build_commands` root test canonicals (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py` — command-aware zero-executed check (D3; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — selector grammar sentence (D3), root canonicals (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md` — command-map table if it lists the root entries (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — step 0 DEGRADED wording (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — per-task scope-verb notation (D4)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_cmd_parse.py` — D1 rewrite and pins, D3 tests
- OBSERVED: `test/plan-marshall/build-maven/fixtures/log-test-data/` — new consumer-line and selector fixtures (D1, D3)
- OBSERVED: `test/plan-marshall/build-maven/test_discover_modules.py` — root canonical tests (D2)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_finalize_module_tests_divergence_divergence.py` — gate-level Maven step-0 test (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/execute-task/test_narrow_unit_doc_contract.py` — D4 doc-contract guard, or a new sibling file (verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** none. PLAN-LB-28 (#1750) and PLAN-LB-58 (#1866) are shipped, and this plan builds on both.
- **Overlaps with**, per `corpus surfaces` (none of these are running):
  - Parked PLAN-LB-75 claims the `test/plan-marshall/phase-6-finalize/` directory, which holds the D2 gate test.
  - Parked PLAN-LB-87 claims `test/plan-marshall/script-shared/` and `_build_execute_factory.py`. This plan touches neither
    unless D3 falls back to the shared result, and even then it collides only with a parked row.
  - Of the specs staged on 2026-11-02, PLAN-LB-105 and PLAN-LB-107 also claim the `test/plan-marshall/phase-6-finalize/`
    directory. The gate decides the pairing.
  - Every other declared owner of a Maven surface (PLAN-LB-28, PLAN-LB-58, PLAN-LB-76, PLAN-LB-93) is shipped.
- **Adjacent to:**
  - `_build_jvm_patterns.py` and the Gradle parser: untouched by constraint.
  - The rest of the PLAN-LB-28 Open Defect is not absorbed, because neither part is high:
    - a truncated reactor log that is summed and stamped `measured`;
    - test-artifact detection that reads only a module's own `<dependencies>`.
  - One failing Surefire test files four issues: the per-class line, the method line, the assertion and the summary. Not
    absorbed; the dedup key is the message prefix.
  - The freshness-label defect (`lessons-routing-068`) sits in the same gate family but on a different surface
    (`_freshness_crosscheck.py`); it is PLAN-LB-107 D4.
  - The `architecture discover` re-run in each consumer: an operator step per consumer, as for PLAN-LB-28.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-110-maven-consumer-test-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
