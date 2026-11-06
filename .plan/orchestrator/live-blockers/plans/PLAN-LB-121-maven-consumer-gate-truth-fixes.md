# PLAN-LB-121: A Maven reactor root is granted a test run only for the tests it builds, and a selector miss never hides a real failure

epic: live-blockers
workstream: WS-02

> Plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-121-maven-consumer-gate-truth-fixes.md`. This spec is NOT queued: the operator asked for it to be specced and
> not staged, so no row file exists. The orchestrator EMITS the command below; it never launches the plan inline, and a row is added
> when the operator launches it.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Specced on the operator's word ("do not stage but spec the plan", decision 17). It is the Maven half of the fix plan for the
> PLAN-LB-110 findings (PR 1921, merge `9c8eb94c2`; report `landings/PLAN-LB-110.md`). Every finding id below (L1-n, L2-n, L3-n) is that
> report's. The other half, the shared routed-result mapping (L1-4, L3-6), sits on the surface of the running PLAN-LB-108 and the held
> PLAN-LB-115 and is carried by PLAN-LB-115 D4, not here. This plan touches no shared build file. The points the orchestrator re-read at
> their lines are OBSERVED; the points the analysis leaf read and the orchestrator did not re-read, and every claim about reach, are
> HYPOTHESIS and are settled first.
>
> Ruling check. D1 is a possible false green in a Maven consumer's pre-push gate (graded blocking as gate integrity, effect a lead until
> the verify-first clause settles it); D2 is a misreport of what a build did (high). D3 is minor and separable. No token or
> measurement work. No Sonar.

## Objective

PLAN-LB-110 gave a Maven reactor root the whole-reactor test canonicals and made a Surefire selector that matched nothing a named
reason. Two of its rules go further than the evidence supports. The root is granted a test run when ANY discovered POM has tests, not
when the root builds one, so a root that does not list a tested subproject resolves its default-scope `module-tests` to a run that
executes zero tests and succeeds. The selector-miss relabel backs off only for two issue categories, so a real failure in another
category is dropped from the result when another module reports a miss.

After this plan the root canonical is granted for the tests the root builds, a selector-miss result keeps every real failure the log
carries and says what the run did, and the guide texts and tests state what holds.

## Deliverables

1. **The reactor root's test canonicals follow what the root builds.** *(L3-1; blocking lead)*
   - Pass 3 grants `module-tests` and `test-compile` to a root `pom` aggregator when any discovered module has test files
     (`_maven_cmd_discover.py:269-307`). "Reactor" there means every `pom.xml` the filesystem walk found, not the modules the root
     declares. The grant follows the root's own reactor: the modules it lists, directly and through nested aggregators, resolved to
     discovered modules; a POM the root does not build does not count.
   - A root that declares no modules and has none of its own tests gets neither key, as a reactor with no test module does today.
     A profile-only `<modules>` list is decided at outline from what a default `mvn test` builds, and the decision is recorded.
   - A discovered run that executed zero tests is not a success the gate can credit. The outline reads whether the pre-push gate or the
     shared result already refuses a green run with no executed test; if it does not, the Maven side reports a successful run whose parse
     shows zero collected tests as `indeterminate` with a named reason, in `_maven_execute.py` (no shared file), and the choice is
     recorded.

   *Done when:* a discovery fixture with a root `pom` that lists no module and a standalone `examples/` POM that has tests gives the
   root neither key (red at `9c8eb94c2`); a root that lists a tested module still gets both (control, the existing fixture); a root that
   lists a nested aggregator whose child has tests still gets both; a no-test reactor still gets neither; a Maven fixture run that
   executed zero tests is not `success`.

2. **A selector miss keeps every real failure and says what the run did.** *(L3-2, L3-3, L3-4, L3-5; major)*
   - The relabel backs off whenever the log carries any real failure issue, not for two categories: any issue whose category is not
     informational (`compilation_error`, `test_failure`, `dependency_error` and `other` build errors alike), decided against the
     category list at outline (`_maven_execute.py`, the guard near its failure-leg branch; `_build_parse.py` categories). The comment
     that states the rule matches the code.
   - The reason names the pattern Surefire printed when the command line carries none: a selector set through `.mvn/maven.config`,
     `MAVEN_OPTS` or a profile, or a Failsafe `-Dit.test` miss, is named from the log's "No tests matching pattern" text
     (`_maven_cmd_parse.py:404,450-453`).
   - In a reactor where the selector matched and ran in one module and missed in another, the reason does not say "the run executed
     nothing".
   - A `-Dtest` run that exited 0 and whose log cannot be read is not `success`: it is `indeterminate` with a reason that says the
     log could not be read, since no evidence cannot be a green for a run whose truth depends on the log. The failure leg's second
     `parse_log` call is guarded the same way.

   *Done when:* a two-module `-fae` fixture, module a failing on `';' expected` and module b printing "No tests matching pattern",
   keeps module a's error and rows (red at `9c8eb94c2`); a `maven.config`-set selector miss names the pattern from the log (red); a
   fixture where the selector ran in module a and missed in module b says so and not "executed nothing" (red); an unreadable log on an
   exit-0 `-Dtest` run is `indeterminate` (red); controls stay green: a lone miss is `indeterminate` with the named reason, a failing
   test keeps its finding, and a `-Dtest` run with an executed test stays `success`.

3. **The guide texts and tests state what holds.** *(separable; L1-2, L1-3, L2-1 to L2-3, L3-7, L3-10)*
   - `build-maven/SKILL.md:42`: the grammar sentence is right for the class position and not for the method form; it states that a
     `+` between classes joins them into one pattern and that `Class#a+b` is Surefire's method list, so the sentence cannot be read to
     forbid valid syntax. The grammar guard pins the corrected sentence.
   - `pre-push-quality-gate.md:419` no longer says a root fix needs an `architecture discover` refresh (the resolver crawls the live
     worktree); branches 3, 4, 5 and 6 (`:479,491,495,500`) name the project's test run neutrally where they say "pytest" and
     "non-Python project".
   - The gate test calls `resolve-test-scope` over the fixture reactor and asserts its response, instead of only checking that the
     help lists the verb (`test_finalize_maven_reactor_root_test_canonical.py:207-224`).
   - `test_discover_reactor_aggregator_has_no_test_ladder` says in its docstring why it lost its `module-tests` assertion, or the
     assertion returns (`test_discover_modules.py:729-734`); the docstring that states the `-am` malformation as fact states what was
     shown (`test_finalize_maven_reactor_root_test_canonical.py:170-177`); the test docstrings drop "shipped before this plan" and
     "at the branch base".
   - The comment that says the relabel claims the run "only when it is the ONLY failure" matches the code D2 leaves.

   *Done when:* the guard test fails against the old grammar sentence; a read of each cited line shows the wording corrected; the gate
   test fails when `resolve-test-scope` is removed from the Maven skill.

Split guard: three deliverables on one Maven surface. D1 and D2 are independent of each other (discovery, execute guard); D3 is the
text and test pass over both and is the first to split off.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **Maven-only, no shared build file.** Do not edit `_build_execute_factory.py`, `_build_server_protocol.py`, `_build_shared.py`,
  `_build_parse.py` or `_build_jvm_patterns.py`; a change that needs one is recorded as owed to PLAN-LB-115 D4. Gradle and pyproject
  behaviour is unchanged.
- **The gate gets more precise, never more permissive.** Every narrowing of the root canonical ships with a control showing that a
  tested reactor still resolves its run, and every relaxation of the relabel with a control showing a lone selector miss is still named.
- **Fail closed.** An unreadable log or an unreadable POM is a named stop, never a pass.
- **No real Maven invocation.** Every new test is a log or POM fixture and states which Maven or Surefire version it reproduces.
- **Test ordering labels.** `order: test-first` where red at the base, `order: none` for a pin or control, and a rewritten existing
  assertion is disclosed as a correction.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: pass 3 sets `reactor_has_tests = any(module.get('stats', {}).get('test_files', 0) > 0 for module in modules)` over every
  discovered module and gives a root `pom` at `.` both canonicals when it is true — `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` L269-307; the docstring calls a canonical that would run nothing "a false green, worse than an
  absent one" — L290-293; the modules come from `discover_descriptors(project_root, 'pom.xml')` — L251.
- OBSERVED: the selector-miss guard returns the result unchanged when the log is unreadable, relabels a miss to `indeterminate`
  unless an issue of category `test_failure` or `compilation_error` is present, and names the selector from the command only —
  `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py` (190 lines at `9c8eb94c2`; the guard is at about L56-150, the log read at about L88-92, the category check at about L100-107, the selector at about L109-110).
- OBSERVED: `_maven_cmd_parse.py` holds the selector-miss reason and the `dtest_selector` reader (about L393-460); the leaf's citations
  for this file are not exact.
- OBSERVED: `pre-push-quality-gate.md` L419 says the unblocking condition is "an `architecture discover` refresh so the persisted
  inventory picks it up"; the architecture core's module docstring says `derived.json` is computed by crawling the live worktree on every
  read and is not persisted — `manage-architecture/scripts/_architecture_core.py` module docstring.
- OBSERVED: the grammar sentence at `build-maven/SKILL.md` L42 was taken from the spec of PLAN-LB-110 D3.
- HYPOTHESIS: `_parse_pom_xml` exposes the POM's `<modules>` list (and a profile's), so the root's own reactor can be resolved without
  a second POM parser — confirm/refute at `_maven_cmd_discover.py` § `_parse_pom_xml` and `_build_module` (verify-at-outline). It
  decides how D1 resolves the root's reactor.
- HYPOTHESIS: a root that declares no `<modules>` still receives `module-tests = test` in the shipped fixture (the lane's own
  `_AGGREGATOR_POM`) — confirm/refute at `test/plan-marshall/build-maven/test_discover_modules.py` § `_AGGREGATOR_POM` and the test at
  L737-751 (verify-at-outline). If it is refuted, D1's first fixture is rebuilt from a real standalone POM.
- HYPOTHESIS: the pre-push gate or `cmd_run_common` does not refuse a green run that executed zero tests — confirm/refute at
  `phase-6-finalize/standards/pre-push-quality-gate.md` § step 0 and branch 4 and at `_build_shared.cmd_run_common` (verify-at-outline).
  It decides whether D1's third bullet is a code change or a documentation line.
- HYPOTHESIS: the `compilation_error` category matches nine phrases only, so `Failed to execute goal … Compilation failure`,
  `';' expected`, enforcer and checkstyle failures categorise as `other` — confirm/refute at `_build_jvm_patterns.py` and
  `_maven_cmd_parse.py` § `MAVEN_PATTERNS` (verify-at-outline; read, not edit).
- HYPOTHESIS: Surefire's documented method list `Class#a+b` is valid and the SKILL sentence reads as forbidding it — confirm/refute
  against the Surefire documentation the corpus cites (verify-at-outline).
- HYPOTHESIS: `-Dtest` set in `.mvn/maven.config` or a profile leaves the command line without the selector, so the exit-0 miss
  (`failIfNoSpecifiedTests=false`) is not detected at all — confirm/refute at `_maven_cmd_parse.py` § `dtest_selector`
  (verify-at-outline). If it is not detectable from the log, the limit is stated in `SKILL.md` and not worked around.
- Verify-first clause (D1): reproduce the stray-POM shape as a discovery fixture at `9c8eb94c2` before editing. A shape that does not
  reproduce is reported and its Done-when narrowed in the PR.
- Verify-first clause (D2): reproduce the dropped-failure shape as a log fixture at `9c8eb94c2` before editing.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` — pass 3 and the root canonical rule (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py` — the selector-miss guard, the unreadable log, the zero-test run (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py` — the pattern capture, the reason text (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — the grammar sentence, the root canonicals (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — L419 and the "pytest" branches (D3)
- OBSERVED: `test/plan-marshall/build-maven/test_discover_modules.py` — root canonical fixtures (D1, D3)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_cmd_parse.py` — pattern capture and grammar guard (D2, D3)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_execute.py` — the guard fixtures (D1, D2)
- OBSERVED: `test/plan-marshall/build-maven/fixtures/log-test-data/` — new log fixtures (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_finalize_maven_reactor_root_test_canonical.py` — the gate test (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md` — the command-map table, if it lists the root entries (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_resolve_scope.py` — only if the zero-test run needs a scope-verb answer (D1; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the merge of PLAN-LB-110 (`9c8eb94c2`), which is on the base branch.
- **Overlaps with PLAN-LB-115 (held) and PLAN-LB-108 (running)** on no file: this spec edits no shared build file. The shared
  routed-result hunks of PLAN-LB-110 are carried by PLAN-LB-115 D4.
- **Overlaps with parked PLAN-LB-75** on the directory `test/plan-marshall/phase-6-finalize/` through the gate test file only: re-ground
  PLAN-LB-75 against this plan's line moves before it is un-parked. The disjointness gate decides the pairing at emit.
- **Adjacent to** (left untouched): the freshness coverage vocabulary (`_build_examined.py`, `_freshness_crosscheck.py`): the Maven `test`
  goal is outside it, so a root `test` row earns no test credit; that is PLAN-LB-120 D2's ground and is not changed here.
- **Owed outside this plan, operator-run:** a harness sync after merge. No consumer needs to re-run `architecture discover`.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-121-maven-consumer-gate-truth-fixes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
