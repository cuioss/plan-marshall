# PLAN-LB-28: Java consumer repositories: Maven build results are right

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-28-java-consumer-repos.md` and is queued as one row file, `queue/PLAN-LB-28.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-13, PLAN-LB-03, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

> SPLIT on 2026-10-09 by operator instruction. This spec was a weak merge of two halves, licensed to split. Its self-review half — deliverables 5 to 8, carried from PLAN-LB-03 — MOVED to PLAN-LB-34, which builds the full surfacing foundation those four deliverables were the first third of. **This plan is deliverables 1 to 4 only: the Maven build path.** The moved deliverables, their claim labels and the carried PLAN-LB-03 notes stay below as the record and are not part of this plan; their surface entries were removed from § Expected Surface and are declared by PLAN-LB-34.

## Objective

(Since the split of 2026-10-09 this plan carries the Maven sentences of this objective only; the self-review sentences describe what moved to PLAN-LB-34.) Two defects stop plans in the Java consumer repositories and neither is visible in this one. The Maven build path generates a test command that cannot resolve a sibling test-jar, reports one summary block out of several as the test count, and files Maven's failure advice as blocking findings. And the pre-submission self-review, which ships default-on, selects a surfacer that covers no Java file, so the verifier refuses a "clean" verdict round after round until the loop-back ceiling stops the push. This plan corrects the Maven command, count and classification, and makes surfacer selection follow declared content classes with a terminal "not covered" outcome.

### Carried from PLAN-LB-13: Maven build results are wrong in consumer repos

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

### Carried from PLAN-LB-03: Self-review ends once on a diff no surfacer covers

`default:pre-submission-self-review` ships default-on to consumer repositories, and its Step 1 runs the first
surfacing implementor whose script notation resolves. The only implementor is
`ext-self-review-plan-marshall`, whose detectors target Python, skill documents and Markdown; in a Java or
other consumer repository it resolves, runs, classifies the changed files as `other`, and surfaces nothing.
The verifier then declines to close a "clean" verdict that the analysis could not have reached, the step
records `loop_back`, and because no fix can change which surfacer exists the same round repeats until the
loop-back ceiling stops the push and an operator overrides it (about 28 minutes on one TokenSheriff PR, where
4 of 4 files were `other`; 19 of 20 on an API-Sheriff diff). Select the implementor by the content classes
it declares it covers instead of by "first that resolves", and give the step a terminal *not covered*
outcome, so a diff no surfacer covers ends the step in one round with a verdict that says exactly that.
Carries forward truthful-signals PLAN-TRUTH-181 deliverables D1–D3.

## Deliverables

1. **[PLAN-LB-13 D1]** **The Maven test ladder reaches `package` when the module consumes a reactor sibling's test-jar.**
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

2. **[PLAN-LB-13 D2]** **`tests_run` counts every summary block of the run, and names the plugin each count came from.**
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

3. **[PLAN-LB-13 D3]** **Bracketed javac tags are matched as literal text.** `'[deprecation]'` and `'[unchecked]'` in
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

4. **[PLAN-LB-13 D4]** **Maven's failure epilogue and passing test-summary lines are not filed as findings.** After a
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

> ⛔ Deliverables 5 to 8 below MOVED to PLAN-LB-34 on 2026-10-09. They are kept as the record and are NOT part of this plan.

5. **[PLAN-LB-03 D1]** **Implementors declare the content classes they cover, and selection uses the declaration.** A
   surfacing implementor states the content classes its detectors cover in a machine-readable declaration
   that `extension_discovery implementors` returns. `ext-self-review-plan-marshall` declares every class it
   has detectors for and does NOT declare the catch-all `other`. Step 1 classifies the live footprint into
   content classes, and an implementor is *applicable* only when its declared classes intersect the
   footprint's classes. A resolvable but inapplicable implementor is not run. Two implementors that declare
   the same class is a registration error reported by discovery, not a silent first-wins.
   Done when: the discovery verb's output for the surfacing ext-point carries the declared classes of
   `ext-self-review-plan-marshall`; a test with a footprint of only `.java` files shows the implementor
   resolved and not selected; a test with a footprint of `.py` and `SKILL.md` files shows it selected and
   its envelope identical to today's for the same fixture; a fixture with two implementors claiming one
   class makes discovery return an error naming both.

6. **[PLAN-LB-03 D2]** **A footprint no implementor covers closes the step once, as *not covered*.** When at least one
   implementor resolves and none is applicable, Step 1 skips the surface call, the author dispatch and the
   verifier dispatch, and Step 4 records `--outcome done` under a new non-finding verdict that is distinct
   from every existing one (for example `"self-review not covered: no surfacer covers this diff's
   content"` — at most 80 ASCII characters, no trailing period, not a prefix of another verdict, and
   without the substring `found`), with `work_performed=false` and facts carrying the uncovered file count
   and the footprint's class names. It is not the *not-run* verdict (no implementor resolved at all) and
   not the *zero-observation* verdict (a surfacer ran and observed nothing); the three stay separate
   records. A WARNING decision-log line names the uncovered classes. No `loop_back` is recorded and no
   iteration is spent.
   Done when: a test of the documented branch table shows the not-covered path reaching `done` with the
   new verdict and without a verifier answer; the verdict-vocabulary test accepts the new verdict beside
   the existing five and still proves no verdict is a prefix of another; `ext-point-self-review-surfacing.md` defines the outcome beside the not-run
   fallback.

7. **[PLAN-LB-03 D3]** **Uncovered files inside a covered diff are reported, and a refusal that no round can change does not
   loop.** When an applicable implementor runs over a footprint that also holds files of classes nobody
   declared, those files are reported as `not_covered` with their count in the round's published
   boundaries and are passed to the verifier as a stated boundary, so they are neither folded into a clean
   zero nor a ground for `may_close: no`. In addition, a round that would record `loop_back` with EMPTY
   author findings at the same HEAD as the previous round's `head_at_completion` (no fix landed in
   between, same non-closing verifier state) does not record a further `loop_back`: nothing a next round
   reads has changed, so the step records the gap once and ends, as Deliverable 2 does, with a verdict
   naming the unresolved verifier state. `verifier_unavailable` is excluded — a failed dispatch can
   succeed on retry.
   Done when: a test of a mixed footprint (Python plus Java) shows the Python slice surfaced, the Java
   files counted as `not_covered`, and the verifier prompt carrying that count; a test replays two
   consecutive empty-findings refused rounds at one HEAD and shows the second ending the step without
   incrementing the loop-back count; a round with findings, or with a moved HEAD, still records
   `loop_back`.

8. **[PLAN-LB-03 D4]** **Controls.** (a) A plan-marshall-only diff produces today's envelope and today's verdicts unchanged.
   (b) A project where no implementor resolves still records the not-run verdict, not the new one.
   (c) Fixtures shaped like the two observed consumer diffs — 4 of 4 files `other`, and 19 of 20 `other`
   with one covered file — end in one round: the first as not covered, the second with the one file
   reviewed and 19 reported `not_covered`. (d) `test_self_review_unclassified_surface.py`, which today
   pins the "wrong-domain implementor resolves, runs, and observes nothing" route as contract, is rewritten
   to pin the new routes with its matched negative control kept.

## Claim Labels

Carried in source order: bullets 1 to 22 from PLAN-LB-13; bullets 23 to 39 from PLAN-LB-03; bullets 40 to 40 added at the regrouping.

- OBSERVED: `module-tests` is emitted as `test{pl_arg}` and `test-compile` as `test-compile{pl_arg}` with `pl_arg = ' -pl {relative_path} -am'` for every non-pom module that has tests; nothing in `_build_commands` checks whether the phase is sufficient — read at `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py:787,808-810`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _maven_cmd_discover.py _build_commands: pl_arg = f' -pl {relative_path} -am' (:787); test-compile{pl_arg} and test{pl_arg} under packaging != 'pom' and has_tests (:808-810); no phase-sufficiency check. File unchanged since 726ca857a.
- OBSERVED: the code comment above `pl_arg` claims `-am` makes "an intra-reactor test-jar resolve on a clean checkout", which is the false premise the defect rests on — read at `_maven_cmd_discover.py:782-786`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _maven_cmd_discover.py:782-786 comment above pl_arg still reads '-am ... so an intra-reactor test-jar resolves on a clean checkout'.
- OBSERVED: `_maven_cmd_discover.py` contains no handling of `test-jar`, `<type>` or `classifier`; the dependency parser reads `dependency:tree` output and discards the type field (`# type = match.group(3) … not needed`) — read at `_maven_cmd_discover.py:702-737`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _maven_cmd_discover.py _parse_dependencies_from_maven_output (:702-737) keeps '# type = match.group(3) ... not needed' (:731); search of the file for test-jar, classifier, <type> hits only the :783 comment.
- OBSERVED: `_build_commands` has two callers: discovery (`_maven_cmd_discover.py:307`) and the profile enrichment in `manage-architecture/scripts/_cmd_client_query.py:136` § `_enrich_module_commands`, which rebuilds the map and overlays it with `merged.update(...)` at `:146-147`; a fix inside `_build_commands` covers both only if both callers pass the test-jar fact in
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_commands call sites: _maven_cmd_discover.py:307 and _cmd_client_query.py:136 in _enrich_module_commands (:112), which overlays with merged.update(...) at :146-147. Both files unchanged.
- OBSERVED: `derive-verification` builds no command string of its own; for build class `module-tests` it resolves the two verbs `test-compile` and `module-tests` through `resolve_command` and returns their executables, so it emits the same `test-compile -pl X -am` and `test -pl X -am` as the command map — read at `manage-architecture/scripts/_cmd_client_handlers.py:475-492,544-553`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_client_handlers.py lines moved (c9738952a): _resolve_verbs_for_build_class now :553-570 returns ['test-compile','module-tests'] (:567); cmd_derive_verification (:573) resolves each verb via resolve_command (:623-631) and returns executables.
- OBSERVED: the phase-4 task deriver is not a separate emitter; it stamps `verification.commands` from the rows `architecture derive-verification` returns — read at `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:594-602`; a search of `phase-4-plan/`, `manage-tasks/` and `manage-architecture/` for a literal `-am` finds only two documentation examples at `manage-architecture/standards/client-api.md:580,595`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-4-plan/SKILL.md:594-602 stamps verification.commands from derive-verification rows; search of phase-4-plan, manage-tasks, manage-architecture for '-pl X -am' hits only manage-architecture/standards/client-api.md:580 and :595.
- OBSERVED: existing tests pin `-pl … -am` on `module-tests` and `test-compile` as required behaviour and must be updated, not deleted — read at `test/plan-marshall/build-maven/test_discover_modules.py:549-598`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: test_discover_modules.py:548-568 test_nested_module_pl_in_all_commands and :579-599 test_nested_module_pl_includes_also_make assert '-pl ... -am' on module-tests and test-compile. File unchanged.
- OBSERVED: the Maven summary extractor takes `m = matches[-1]` over the pattern `Tests run:\s*(\d+),\s*Failures:…Skipped:\s*(\d+)`, which matches per-class lines as well as summary lines — read at `build-maven/scripts/_maven_cmd_parse.py:151-176`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _maven_cmd_parse.py _extract_test_summary (:151-176): unanchored pattern 'Tests run:..Failures:..Errors:..Skipped:' (:159) via re.finditer, m = matches[-1] (:164); matches per-class lines too.
- OBSERVED: a non-`None` parsed total is stamped `tests_population: measured` — read at `script-shared/scripts/build/_build_shared.py:836-876`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_shared.py lines moved (c9738952a): cmd_run_common :860-864 parsed_total = test_summary.executed (or routed_tests_run) -> resolve_tests_run; :895 'tests_population': 'measured' if tests_run is not None else 'unmeasured'.
- OBSERVED: no test names Failsafe or a second summary block: `failsafe` (any case) has zero matches in `test/plan-marshall/build-maven/test_maven_cmd_parse.py` and `test/plan-marshall/script-shared/test_build_parse.py`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Case-insensitive search for 'failsafe' in test/plan-marshall/build-maven/test_maven_cmd_parse.py and test/plan-marshall/script-shared/test_build_parse.py returns zero matches; both files exist.
- OBSERVED: `JVM_BASE_PATTERNS['deprecation_warning']` carries the literal `'[deprecation]'` and `['unchecked_warning']` carries `'[unchecked]'` — read at `script-shared/scripts/build/_build_jvm_patterns.py:53-60`; `_is_regex_pattern` returns true for any pattern containing `[` or `]` and `categorize_issue` then calls `re.search(pattern, message, re.IGNORECASE)` — read at `script-shared/scripts/build/_build_parse.py:476-490`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_jvm_patterns.py:54 '[deprecation]' and :58 '[unchecked]'; _build_parse.py categorize_issue (:461) calls re.search(pattern, message, re.IGNORECASE) at :479 when _is_regex_pattern (:487-490) sees a bracket.
- OBSERVED: `MAVEN_PATTERNS` overrides only `openrewrite_info`, so Maven inherits both bracket patterns unescaped, while `GRADLE_PATTERNS` overrides them with `r'\[deprecation\]'` and `r'\[unchecked\]'` — read at `build-maven/scripts/_maven_cmd_parse.py:37-47` and `build-gradle/scripts/_gradle_cmd_parse.py:85-94`; the defect is Maven-only in effect
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _maven_cmd_parse.py:37-47 MAVEN_PATTERNS overrides only openrewrite_info; _gradle_cmd_parse.py:85-94 unchanged since 726ca857a (no commit touched build-gradle), still escaping both bracket patterns.
- OBSERVED: the one existing deprecation test asserts only `len(deprecation) >= 1`, which the character-class match satisfies for the wrong reason — read at `test/plan-marshall/build-maven/test_maven_cmd_parse.py:138-140`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: test_maven_cmd_parse.py:138-140 test_parse_log_failure_warning_category ends with 'assert len(deprecation) >= 1' (:140). File unchanged.
- OBSERVED: `_extract_issues` files every line containing `[ERROR]` or `[WARNING]` except empty messages, `->` continuations and stack-trace lines; there is no epilogue filter — read at `build-maven/scripts/_maven_cmd_parse.py:89-135`; the base pattern `'tests run:'` under `test_failure` is a plain substring — read at `_build_jvm_patterns.py:32-38`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _maven_cmd_parse.py _extract_issues (:89-135) skips only 'at '/'Caused by:' lines (:102), empty messages and '->' continuations (:114); no epilogue filter. _build_jvm_patterns.py:33 test_failure carries plain 'tests run:'.
- OBSERVED: a category containing neither `test` nor `lint`/`style` becomes a `build-error` finding, and severity `error` is carried through — read at `script-shared/scripts/build/_build_shared.py:283-309`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_shared.py _classify_issue_finding_type (:283-301) falls through to 'build-error' unless test-failure / lint / style; _classify_finding_severity (:304-309) maps SEVERITY_ERROR to 'error'. Lines unmoved.
- HYPOTHESIS: Maven attaches a test-jar only at `package`, and a reactor run stopped at `test` cannot resolve a sibling's `test-jar` or custom-classifier artifact from `target/test-classes` in the Maven versions the consumer repos use — confirm/refute with a real two-module fixture run under the consumers' Maven wrapper version, and at `build-maven/standards/maven-impl.md` § command options (verify-at-outline)
- HYPOTHESIS: the reported consumer figures (TokenSheriff: `test` 724 against `verify` 7 on one tree; a 15-module reactor with 3,083 tests reported as 0; API-Sheriff: 202 reported for a module that runs 1,886) are other repositories' observations and were not re-run here — confirm/refute by parsing a captured `verify` log from `/Users/oliver/git/TokenSheriff` or `/Users/oliver/git/API-Sheriff` through `_maven_cmd_parse.py` § `parse_log` (verify-at-outline)
- HYPOTHESIS: under `-T1C` parallel reactor builds the per-module summary blocks interleave with other modules' output but each summary line stays intact, so line-based block detection still works — confirm/refute against a captured parallel-build log and at `_maven_cmd_parse.py` § `_extract_test_summary` (verify-at-outline)
- HYPOTHESIS: the daemon-routed path can supply `routed_tests_run`, which wins over the parsed total, so a routed Maven build may report a count this plan's parser fix does not reach — confirm/refute at `script-shared/scripts/build/_build_shared.py` § `cmd_run_common` (the `routed_total` branch) and the daemon's Maven count source (verify-at-outline) — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: refuted. `routed_tests_run` does win over the parsed total (`_build_shared.py:845-863`), but its source is the `tests_run` line of the inner wrapper's own in-process parse (`_build_execute_factory.py:691-692`, `_build_server_protocol.py` § `read_log_verdict`), so a fix to the Maven parser reaches routed builds as well. No routed-path change is needed, and `_build_shared.py` drops out of this plan's conditional surface unless another deliverable needs it
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: _build_shared.py:845-863 routed_tests_run does win, but its source (_build_execute_factory.py:691-692, _build_server_protocol.py read_log_verdict :1059) is the tests_run line of the INNER wrapper's own in-process parse, so a Maven parser fix reaches routed builds.
- Verify-first clause: before scoping deliverable 1, settle which replacement command is emitted. `verify -pl X -am` also runs Failsafe integration tests and any plugin bound after `test`, which changes what `module-tests` costs and means; a two-step `install -DskipTests` then `test -pl X` writes to the local repository. Pick one, state the cost, and record the choice in `build-maven/standards/maven-impl.md`. If the POM cannot tell a reactor-sibling test-jar from an external one without running Maven, loop back and re-scope the detection rule.
- Verify-first clause: before scoping deliverable 2, read the landing of the earlier `tests_run: 0` fix (the `tests_population` discriminator in `_build_shared.py`) so the new summed count and the `measured` / `unmeasured` label keep one meaning.
- Verify-first clause: before scoping deliverable 4, derive the epilogue line set from real failing logs of at least two Maven versions rather than from the list in this spec; the list above is a floor.
- OBSERVED: Step 1 selects exactly one implementor, by resolvability — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:119` ("Select the first implementor whose notation **resolves in the current executor**"); § "Domain-Aware Candidate Surfacing" (:39) states the step ships `default_on: true` to consumer projects.
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md lines moved: :122 'Select the first implementor whose notation **resolves in the current executor**'; Domain-Aware Candidate Surfacing :42 'this step now ships `default_on: true` to consumer projects'.
- OBSERVED: exactly one surfacing implementor exists — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` (frontmatter `implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing`); a listing of `marketplace/bundles/*/skills/ext-self-review-*` finds this skill and one stale directory holding only an untracked `__pycache__` (`marketplace/bundles/plan-marshall/skills/ext-self-review-plan-marshall/`), which is not a skill.
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: git ls-files finds one implementor: pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md (implements: line :6). plan-marshall/skills/ext-self-review-plan-marshall does not exist in this checkout at all, so no stale dir here.
- OBSERVED: the implementor's class vocabulary is private to it and every unanticipated file shape lands in `other` — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` § `CONTENT_CLASSES` (:2463-2470: `python`, `skill_doc`, `standards_doc`, `markdown_other`, `structured_config`, `other`) and § `_classify_content` (:2476-2500, final `return 'other'`).
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: _self_review_detectors.py lines moved (d8b0284ef): CONTENT_CLASSES :2573-2580 (python, skill_doc, standards_doc, markdown_other, structured_config, other); _classify_content :2586-2610 ends 'return other' as catch-all.
- OBSERVED: discovery reads no content-class key from implementor frontmatter — `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` § `_IMPLEMENTOR_FRONTMATTER_KEYS` (:894-902: `name`, `order`, `default_on`, `presets`, `description`, `canonicals`, `verification_profile`).
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: extension_discovery.py _IMPLEMENTOR_FRONTMATTER_KEYS (:894-902) = name, order, default_on, presets, description, canonicals, verification_profile; no content-class key. Read at :1066. File unchanged.
- OBSERVED: every non-closing verifier state records `loop_back` — `pre-submission-self-review.md:505-511` (table) and `:520` ("Every non-closing state above records `loop_back`, never `done` and never `failed`").
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md lines moved: state table :605-609 maps verdict_refused / further_round_owed / verifier_unavailable to loop_back; :623 'Every non-closing state above records `loop_back`, never `done` and never `failed`'.
- OBSERVED: the verifier is told to refuse "a clean verdict that reads as a reviewed diff where the structural limit says this analysis class could not reach the question", and to answer `may_close: no` when anything "suggests a further round would find something this one did not look for" — `pre-submission-self-review.md` § "Step 3b" verifier prompt (the two numbered questions). — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: no longer true. Both passages were removed by `d8b0284ef` (#1726). The verifier prompt (541-561) now refuses only on wrong counts or a wrong scope statement, answers `may_close: yes` when the regraded blocking set is empty and the surface scope is full, and says the structural limit "is not a reason to answer no". A zero-observation clean full-surface round therefore closes by the verifier's own rule, and the refusal no round can change, which drove PLAN-LB-03 D3, should no longer occur. PLAN-LB-03 D3 shrinks to what is still missing: reporting the files no check covered (`not_covered`) and the same-HEAD rule. Confirm on a consumer-repository run before building more
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: Both quoted passages are gone (d8b0284ef). Step 3b prompt :541-561 now refuses ONLY on wrong counts or scope statement, answers may_close yes when the regraded blocking set is empty AND surface_scope is full, and says the structural limit 'is not a reason to answer no'.
- OBSERVED: a round that surfaced nothing over a non-empty scope is routed to a Branch A close under the zero-observation verdict, but Branch A still requires the verifier's `acceptance: accepted` and `may_close: yes` — `pre-submission-self-review.md` § "A clean verdict states what the round observed" (:314) and § "Step 4" stop-path confirmation gate (:540-547). No branch exists for "the verifier will never say yes for a reason no fix changes".
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md :355 routes zero-observation to Branch A; gate :685-693 requires acceptance==accepted and may_close==yes. No automatic never-yes branch; an unexplained no still loops (:597). Only exit is operator 'loop-back close' (:847, 6b00815e0).
- OBSERVED: the only path that closes without a verifier answer is the zero-generator fallback, reached when NO implementor resolves — `pre-submission-self-review.md:181-183` and `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md:24-26`. — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: incomplete. The zero-generator fallback is still there (184-186), but it is no longer the only close without a verifier answer: `6b00815e0` (#1718) added the out-of-budget operator close, `manage-status loop-back close` (847, 859-872), which records `done` with `may_close=operator_override`. The operator exit this spec calls an override therefore exists already; PLAN-LB-03 uses that verb and builds no second one
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: Zero-generator fallback still at :184-186 and ext-point :24-26, but it is no longer the only close without a verifier answer: 6b00815e0 added the out-of-budget operator close 'manage-status loop-back close' (:847, :859-872), recording done with may_close=operator_override.
- OBSERVED: the existing non-finding verdict set is four strings plus the findings verdict, with a stated disjointness rule — `pre-submission-self-review.md` § "Dispatched-envelope output" (:399-407). — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: the count is stale. The section (466-477) now lists six verdicts since `d8b0284ef`: five non-blocking ones (not run, nothing to check, no check matched, zero observation, and a new advisory-only `clean: no blocking finding, {A} advisory`) plus the blocking verdict `found {B} blocking in {C} classes, {A} advisory`. Where a PLAN-LB-03 deliverable says a new verdict stands "beside the existing five", read six, and keep the disjointness rule over all of them
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: Dispatched-envelope output :466-477 now lists SIX verdicts (d8b0284ef): five non-blocking (not-run, nothing-to-check, no-check-matched, zero-observation, new advisory-only 'clean: no blocking finding, {A} advisory') plus the blocking verdict 'found {B} blocking in {C} classes, {A} advisory'.
- OBSERVED: the surfacer already publishes a per-class partition of its file set — `ext-point-self-review-surfacing.md` § `delta_coverage` (`by_class[C]{content_class,files,files_with_candidates,files_without_candidates}` at :95; "the class vocabulary itself is the implementor's" at :224).
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:95 by_class[C]{content_class,files,files_with_candidates,files_without_candidates}; 'The class vocabulary itself is the implementor's' now at :228 (was :224).
- OBSERVED: a test pins the wrong-domain route as contract — `test/plan-marshall/phase-6-finalize/test_self_review_unclassified_surface.py` module docstring ("Route 2 — a wrong-domain implementor resolves, runs, and observes nothing").
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: test_self_review_unclassified_surface.py module docstring :15 'Route 2 - a wrong-domain implementor resolves, runs, and observes nothing'; section headers at :225 and :286. File unchanged.
- OBSERVED: in consumer repositories the plan-marshall implementor's notation resolves, which is why Step 1 selects it instead of taking the zero-generator fallback — the generated executors of the local consumer checkouts `/Users/oliver/git/TokenSheriff/.plan/execute-script.py` and `/Users/oliver/git/API-Sheriff/.plan/execute-script.py` each carry `ext-self-review-plan-marshall` entries (3 matches each).
  - verdict: unverifiable | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: /home/oliver/git/API-Sheriff/.plan/execute-script.py carries 3 ext-self-review-plan-marshall matches, but /home/oliver/git/TokenSheriff/.plan/ holds no execute-script.py on this machine, so the 'each' half cannot be checked.
- HYPOTHESIS: on the observed consumer diffs the loop was driven by the verifier refusing or answering `may_close: no` over a zero-observation clean verdict, round after round at an unchanged HEAD — reported by two runs (TokenSheriff PR #744, API-Sheriff), not reproduced here; confirm from those plans' archived `metadata.phase_steps` and decision logs, or by replaying a 4-of-4 `other` fixture through the documented branches (verify-at-outline).
- HYPOTHESIS: Step 1 can classify the footprint before choosing an implementor without a shared envelope module — either by a cheap applicability subcommand on the implementor script, or by a small path classifier owned by `extension-api`; confirm which at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py` § the `surface` subcommand's footprint derivation (verify-at-outline).
- Verify-first clause: decide where footprint classification lives for this plan (implementor-side applicability call versus an `extension-api` classifier) before scoping Deliverable 1; the shared envelope is out of scope, so the choice must not require moving `CONTENT_CLASSES` out of the implementor.
- Verify-first clause: enumerate the verifier-refusal grounds that cannot change between rounds at an unchanged HEAD (surfacer domain, content class, zero detectors) and confirm the same-HEAD rule in Deliverable 3 catches each; if a ground exists that the rule misses, add it or report it.
- Verify-first clause: the terminal outcome in Deliverables 2 and 3 is `done` with a not-covered verdict and a WARNING. If the operator wants an unattended run to halt and ask instead, that is a one-line change of the recorded outcome; settle it at outline and record the choice.
- Verify-first clause: the carried claims name consumer checkouts as `/Users/oliver/git/TokenSheriff` and `/Users/oliver/git/API-Sheriff`. Resolve the same repository names under the checkout root of the machine the plan runs on before reading a log or an executor from them.

## Expected Surface

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
- Since the split of 2026-10-09 this plan declares Maven build files only. Ten surface entries for the self-review workflow, the extension point, discovery and the plan-marshall surfacer moved to PLAN-LB-34 with deliverables 5 to 8.
- Overlaps with: PLAN-LB-23 (shipped) on `script-shared/scripts/build/_build_shared.py`, only if this plan adds test-count result keys. No overlap with a live plan remains.
- May run together with: every other live plan of the epic.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-13:

- Depends on: none.
- Overlaps with: PLAN-LB-12 (`PLAN-LB-12-build-timeout-and-verify-budget.md`) ranges over `script-shared/scripts/build/*`; this plan touches `_build_jvm_patterns.py` there for certain and `_build_parse.py` / `_build_shared.py` only conditionally. Sequence the two if PLAN-LB-12 edits `_build_shared.py` § `cmd_run_common`.
- Adjacent to: `build-gradle/scripts/_gradle_cmd_parse.py` — already escapes the bracket patterns and calls the shared `extract_test_summary`; untouched. The shared helper's `matches[-1]` at `_build_parse.py:624` and its docstring claim that "the final one is the aggregate" are the same premise for Gradle, npm and pytest; whether it is wrong for those tools is not settled here.
- Adjacent to: `phase-4-plan/SKILL.md` and `manage-architecture/scripts/_cmd_client_handlers.py` § `cmd_derive_verification` — both consume the command map and need no change of their own; only a test is added on the deriver.
- Left out on purpose: a project-side override for a generated canonical (PLAN-TRUTH-122 D2 / PLAN-TRUTH-150 D4), which is unnecessary once the generated command is correct; the population sweep of every parser's last-match premise (PLAN-TRUTH-122 D0); `-Dsurefire.failIfNoSpecifiedTests=false` for a targeted `-Dtest` riding `-am`; the pre-push gate's whole-tree widening that strips `-pl` and `-am` together (`phase-6-finalize/standards/pre-push-quality-gate.md`); one test failure being filed at several granularities; and the CI and `files_exist` items folded into PLAN-TRUTH-150.
- Foreign-repo work: none required. TokenSheriff and API-Sheriff (`/Users/oliver/git/TokenSheriff`, `/Users/oliver/git/API-Sheriff`) are the places to capture real logs for fixtures and to confirm the fix after the harness sync; no change is made in them.

From PLAN-LB-03:

- Depends on: none.
- Overlaps with: PLAN-LB-02 (`PLAN-LB-02-self-review-convergence.md`) — both edit `phase-6-finalize/workflow/pre-submission-self-review.md`. Section ownership: THIS plan owns § "Domain-Aware Candidate Surfacing", § "Step 1" (implementor selection and the zero-generator fallback), the non-finding verdict vocabulary in § "Dispatched-envelope output", the boundary lines of the Step 3b verifier prompt, and the new not-covered branch in § "Step 4". PLAN-LB-02 owns § "Step 3b" from the non-closing state table through the `qgate add` block and the unverified-dispatch paragraph, § "Step 4" Branch B and the paragraph that closes Step 4, and § "Round-loop termination". Neither plan edits the other's sections. Sequence the two, never run them together; the second to start rebases onto the first. This plan is the smaller one and is suggested first.
- Adjacent to: the per-source loop-back budget and the operator close that PLAN-LB-02 adds. Deliverable 3's same-HEAD rule ends a round before it asks for a loop-back, so it does not read or write the loop-back counter in either its current or its per-source form.
- Left out on purpose: truthful-signals PLAN-TRUTH-181 D4–D7 — the shared surfacing envelope module, the machine-readable `not_covered` landing fact for orchestrator epics, the implementor authoring guide, and the multi-implementor merge controls. With one implementor there is nothing to merge; Deliverable 1 selects at most one applicable implementor and reports the duplicate-class case as an error.
- Left out on purpose: surfacers for other domains (Java, consumer Python, JavaScript, documents — truthful-signals PLAN-TRUTH-182 to -185). After this plan a consumer diff is honestly reported as not covered; it is still not reviewed. A consumer diff of `.py` or `.md` files continues to be surfaced by the plan-marshall-domain detectors, because those classes are declared.
- Foreign-repo work: none. The consumer repositories receive the fix through the normal bundle sync.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-28-java-consumer-repos.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
