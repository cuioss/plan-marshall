envelope_version=1
sender_type=plan
sender_id=rb-lb-121-maven-consumer-gate-truth-fixes
epic=live-blockers
kind=landing
created=2026-11-07T11:59:35Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-121-maven-consumer-gate-truth-fixes
epic=live-blockers
pr=#1929
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2062
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# PLAN-LB-121 landing — a reactor root runs only the tests it builds, and a selector miss keeps every real failure

PR #1929 merged as `74ddc39a8918a846cd32b57ffeb6dd36d1490e16`. Base at merge time:
`47d4a5b70` (main moved during the run, so origin/main was merged into the branch
as `0ae252455` and the gate re-run on that head).

## Deliverables

### D1 — the reactor root's test canonicals follow what the root builds

| Done-when | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| Root that lists no module + a standalone tested `examples/` POM → root gets neither key | met | mutation-after | `test_discover_reactor_root_ignores_a_tested_pom_it_does_not_build` | `82d3439b8` + mutation, `b76d3c0f82f949acb062bd403212636b` |
| Root that lists a tested module → both (control) | met | none | `test_discover_reactor_aggregator_carries_the_whole_reactor_test_canonicals` | — |
| Root that lists a nested aggregator whose child has tests → both | met | none | `test_discover_root_reactor_follows_modules_through_a_nested_aggregator` | — |
| No-test reactor → neither | met | mutation-after | `test_discover_reactor_root_stays_false_canonical_free_without_test_modules` | `82d3439b8` + mutation, `b76d3c0f82f949acb062bd403212636b` |
| A Maven fixture run that executed zero tests is not `success` | met | mutation-after | `test_zero_test_run_is_not_success`, `test_test_run_with_no_summary_at_all_is_not_success`, `test_execute_direct_is_wired_to_the_zero_test_guard` | `82d3439b8` + mutation, `b76d3c0f82f949acb062bd403212636b` |
| Profile-only `<modules>` decided from what a default `mvn test` builds, decision recorded | met | none | `test_discover_root_reactor_follows_a_modules_block_only_when_the_profile_is_default_active`, `test_parse_pom_xml_reads_the_modules_a_default_build_includes` | — |

Decisions recorded: the root's reactor is its top-level `<modules>` plus any
profile's `<modules>` whose `activation/activeByDefault` is true, followed through
nested aggregators; a `-P`-only, property-, JDK-, OS- or file-activated profile is
not followed (under-grants → the gate records DEGRADED), and a counted-but-
deactivated `activeByDefault` profile may over-grant (→ the zero-test check). The
zero-test backstop applies to a leading `test` or `package` goal only, read from
Maven's phase/plugin-goal vocabulary, and honours a log that states it skipped.

### D2 — a selector miss keeps every real failure and says what the run did

| Done-when | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| Two-module `-fae` fixture keeps module a's `';' expected` error and rows | met | mutation-after | `test_fae_reactor_keeps_a_real_failure_beside_a_selector_miss` | `82d3439b8` + mutation, `8a5bf691d3664be3a978141cd59be504` |
| `maven.config`-set selector miss names the pattern from the log | met | mutation-after | `test_selector_miss_without_a_command_selector_names_the_pattern_from_the_log` (failure path), `test_exit_zero_config_selector_miss_is_detected_by_the_zero_test_guard` (exit-0 path) | `82d3439b8` + mutation, `8a5bf691d3664be3a978141cd59be504` |
| Selector ran in module a, missed in b → says so, not "executed nothing" | met | mutation-after | `test_reactor_selector_miss_beside_an_executed_module_says_what_the_run_did` | `82d3439b8` + mutation, `8a5bf691d3664be3a978141cd59be504` |
| Unreadable log on an exit-0 `-Dtest` run → `indeterminate` | met | mutation-after | `test_unreadable_log_on_a_zero_exit_dtest_run_is_indeterminate` | `82d3439b8` + mutation, `8a5bf691d3664be3a978141cd59be504` |
| Controls: lone miss named; failing test keeps its finding; `-Dtest` with an executed test stays `success` | met | none | `test_control_a_selector_miss_that_ran_nothing_still_says_so`, `test_control_a_mixed_reactor_keeps_the_other_modules_failure`, `test_control_dtest_run_with_an_executed_test_stays_success`, `test_control_a_suppressed_partial_reactor_miss_is_the_documented_limit` | — |

Recorded limit (CodeRabbit's finding, verified against the Surefire 3.5.2 source):
with `-Dsurefire.failIfNoSpecifiedTests=false` a module whose scan is empty prints
no pattern line, so a suppressed miss inside a reactor whose other module collected
tests leaves no trace. `build-maven/SKILL.md` § "Test selectors" states the limit;
no real Maven invocation was allowed by the spec's Standing Constraints, so the
shape is verified from the runner's code path, not a recording.

### D3 — the guide texts and tests state what holds

| Done-when | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| The guard test fails against the old grammar sentence | met | mutation-after | `test_build_maven_skill_states_the_selector_grammar` | `bb3d4ea02` + old sentence, `491f196b3d4f49e5ae8a4d1a4a08b58f` |
| A read of each cited line shows the wording corrected | met | none | `pre-push-quality-gate.md` L419 and branches 3–6; `SKILL.md` grammar + run sections; `maven-impl.md` § reactor root | — |
| The gate test fails when `resolve-test-scope` is removed from the Maven skill | met | mutation-after | `test_the_resolved_notation_publishes_the_scope_verb_the_arm_calls_next` | `bb3d4ea02` + verb mutated to an error envelope, `40f7ee6075c6415c81ebf389919a65eb`; removing the registration outright also breaks collection, `ad3acd795a074a68b6f51a834189fb2c` |

Per-head test runs (`verify` on every pushed head): `bb3d4ea02` 32980, `1ff320b11`
32984, `45e0cc347` 32986, `a510844fd` 32989, `2059eb260` 32991, `dd935dc08` 32995,
`12415d8ae` 32996, `2d478fa0a` 32996, merge `0ae252455` 33115 — all exit 0.
Bundle-scoped `module-tests` ran alongside (439 at the last pre-merge head).

## Personas and skills

- Personas applied: `persona-implementer` (production code in `_maven_cmd_discover.py`,
  `_maven_execute.py`, `_maven_cmd_parse.py`), `persona-module-tester` (the fixture and
  unit tests), `persona-documenter` (SKILL/standard text), `persona-code-reviewer` (all
  four self-review rounds and every PR-comment triage).
- Domain skills: none named by the spec for any deliverable (`skills: none named`).
- No surface drift: every changed file maps to the spec's Expected Surface, except
  `test/plan-marshall/build-maven/test_maven_pom_parse.py`, which is the mechanical
  consequence of the new `modules` key on `_parse_pom_xml` (the governing hypothesis is
  in the spec).

## Hypotheses

- `_parse_pom_xml` exposes the POM's `<modules>` list — **refuted**: it parsed only
  packaging/coordinates/profiles/dependencies (`_maven_cmd_discover.py` L512-586 at
  base). The parser was extended; the root's reactor is resolved from it.
- A root that declares no `<modules>` still receives `module-tests = test` in the
  shipped fixture — **confirmed** (`test_discover_modules.py` L736-751 at `9c8eb94c2`).
- The pre-push gate or `cmd_run_common` does not refuse a green run that executed zero
  tests — **confirmed**: `cmd_run_common` only refuses to CLEAR findings
  (`_build_examined.refusal_reason`), and the gate branches on `status: success`; hence
  D1's third bullet is a code change.
- `compilation_error` matches nine phrases only, so `';' expected`, enforcer and
  checkstyle failures categorise as `other` — **confirmed**
  (`_build_jvm_patterns.py` L24-49, `categorize_issue` default `other`).
- Surefire's `Class#a+b` is valid and the SKILL sentence reads as forbidding it —
  **confirmed** against the Surefire documentation the corpus cites
  (`maven.apache.org/surefire/maven-surefire-plugin`), and the sentence was corrected.
- A `-Dtest` set in `.mvn/maven.config` or a profile leaves the command line without
  the selector — **confirmed** (`dtest_selector` reads only the command). The failing
  shape is detected from the log's pattern text; the exit-0 shape is not detectable and
  is documented rather than worked around.
- Verify-first clauses: the stray-POM shape and the dropped-failure shape both
  reproduced as fixtures, so no Done-when had to be narrowed.

## Findings

Self-review rounds 1–4 (round 4 on the operator's selection after the three-round
limit) raised 31 findings. Fixed in `1ff320b11`, `45e0cc347`, `a510844fd`, `2059eb260`:
an unrelated warning blocking the relabel, the unreadable-log and skip-marker scopes,
`-DskipTests=false`, goal detection past option values, stale docstrings, a vacuous
test, an internally inconsistent fixture, a dead assertion, and two drift gaps (now
drift-tested). Answered rather than changed: the collected-vs-executed reading (LB-110's
recorded choice), the `verify`/`install` narrowing, the guard's in-process-only reach
(version-pinned daemon), and the Expected-Surface addition.

CodeRabbit (2 actionable + 5 nitpicks, then two follow-ups): everything dispositioned.
Actionable fixed in `dd935dc08`; the suppressed-partial-miss follow-up is the documented
limit in `12415d8ae`; the profile-activation docstring was corrected in `2d478fa0a`;
refusing to capture a real Maven log is the spec's Standing Constraint. Its final review
on `0ae252455` reports `kind=reviewed`, risk Low, "no actionable comments".
Sourcery refused on its own review quota and is optional.

## Reviewers

| Reviewer | Kind | Result |
|---|---|---|
| CodeRabbit | required, quota-limited | reviewed `2059eb260` (2 actionable + 5 nitpicks), `12415d8ae` (follow-ups), and the merge head `0ae252455` (`final_review_risk_coverage` kind=reviewed, risk Low, no actionable comments). Re-triggered after every push; two triggers were rate-limited (`next review in ~5-8 min`), recorded. |
| Sourcery | optional, quota-limited | refused: "used your own review budget of 250,000 diff characters for the last 7 days" (4 days 17 hours to reset). Not a gate. |

## Operator questions

1. "The self-review round limit (3 rounds) is reached … How should the run continue?" —
   options {run one more review round; proceed as budget-exhausted} → **"Run one more
   review round"**.
2. "Cleanup after the merge … the worktree is dirty only by `uv.lock` … How should I
   proceed?" (first asked as a two-option form, the operator answered "re-ask") —
   options {drop the lockfile change then clean up; force-remove the worktree; leave
   everything} → **"Drop the lockfile change, then clean up"**.

No free-text operator messages beyond those selections.

## Rule check

- Guard: present on this harness. Two refusals, both from this run's own session
  (`ses_e4dad1b2cffeW43qz9h3mO524s`): R1 rejected a `git commit` whose message carried a
  parenthesised shell-looking construct (re-issued without it); R2 rejected a `cp` of a
  ci-body file (the body was written with the write tool instead). No workaround was
  attempted after either refusal.
- Shell: one command per call throughout; files read/edited with the file tools. One
  `grep` of the build log tail and one `git show origin/main:uv.lock` are outside the
  "use file tools" guidance — recorded here as self-counted, and neither is a `.plan/`
  write.
- `.plan/` writes: only `.plan/temp/` (progress + landing) and the `ci` bodies under
  `.plan/local/plans/NO_PLAN/work/ci-bodies/`.
- Builds: every build used the resolved canonicals with the default routing; the count
  and mechanisms are in the Build server section below.
- `git restore` was used once, on `uv.lock` only, after the operator explicitly selected
  dropping that regenerated lockfile (the lane forbids it by default precisely so this
  decision is the operator's).
- Spec read: `spec_source: ledger_worktree`; no `spec_differ` marker.
- `executor-skew`: `not_applicable` (source checkout) — answered, recorded, never asked.
- Restart: the session was restarted once by the server during the review cycle; the
  progress file carried the state, and the lane text in context was re-applied. No
  sub-agent was killed; the four self-review dispatches each re-ran their own round only.

## Build server

Preflight at setup: `ready`. Eleven routed builds (`daemon_longpoll`), zero
`in_process_fallback`, zero launch-fault retries, zero `killed` jobs. One `running`
hand-back was re-attached with a bounded wait each time the queue held the job. The
per-`mechanism` counts are: `daemon_longpoll: 11`, `in_process_fallback: 0`.
No fallbacks were used. `runtime_stamp_reason`: none.

## Residue

- The documented limit above: a suppressed selector miss inside a multi-module reactor
  where another module collected tests is invisible in the log.
- `pre-push-quality-gate.md` still says "pytest" at L574/607/622, outside the four
  branch lines D3 named; left untouched to keep the plan's surface.
- A harness sync after merge is owed (operator-run); no consumer needs to re-run
  `architecture discover`.
- `uv.lock` in this repository is stale relative to `pyproject.toml` (main pins
  types-pyyaml 20260906 while `pyproject.toml` requires >=6.0.12.20261103); noticed
  during cleanup, not touched.
