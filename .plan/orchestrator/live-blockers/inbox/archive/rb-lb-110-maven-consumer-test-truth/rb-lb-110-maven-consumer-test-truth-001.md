envelope_version=1
sender_type=plan
sender_id=rb-lb-110-maven-consumer-test-truth
epic=live-blockers
kind=landing
created=2026-11-06T17:32:43Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-110-maven-consumer-test-truth
epic=live-blockers
pr=#1921
merge_state=merged
cleanup_owed=false
deliverables_total=4
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

# PLAN-LB-110 landing — a Maven consumer's test results read true

Merge commit `9c8eb94c26ebfea1e4eb268f262a333735e159a1`, PR #1921, branch
`fix/lb-110-maven-consumer-test-truth` (deleted, local and remote).

## 1. Deliverables

**D1 — the Maven parser files diagnostics only: MET.**

| Done-when | Verdict | Order | Test | Failing run | Commit |
|---|---|---|---|---|---|
| Both fixtures: headers not filed, continuation fields in the compiler error's `detail`, neither its own issue | met | test-first | `test_failure_epilogue_is_not_filed_and_real_diagnostics_are[maven-3.9, maven-4]` | c394a95, `python-2026-11-06-061740.log` | b339055da |
| Control: orphan `symbol:` still filed | met | test-first | `test_control_orphan_compiler_continuation_is_still_filed` | c394a95, same log | b339055da |
| `test_control_failing_test_count_line_is_still_filed` stays green | met | none | same test (severity assertion restored in f029668c4) | — | f029668c4 |
| Consumer-line pin passes at base and is labelled a pin | met | none | `test_consumer_passing_line_without_a_test_suffix_is_not_filed` | — | b339055da |

Added beyond the letter of the criteria: the bare (unprefixed) continuation form a
compile-only log prints (`test_a_compile_only_log_attaches_its_unprefixed_continuation_lines`),
its window-close control, the section-header case, and the Maven finding-store
round trip (55a0dd166).

**D2 — a reactor root resolves `module-tests` / `test-compile`: NOT FULLY MET.**

| Done-when | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| Discovery test, root `pom` + one `jar` module with `src/test` | met | test-first | `test_discover_reactor_aggregator_carries_the_whole_reactor_test_canonicals` | c394a95, `python-2026-11-06-064759.log` |
| Second fixture, no test module: neither key | met | none | `test_discover_reactor_root_stays_false_canonical_free_without_test_modules` | — |
| Third fixture: single-module `jar` root unchanged | met | none | `test_discover_single_module_jar_root_keeps_its_own_test_canonicals` | — |
| Test over a persisted architecture, step 0 resolving and the arm reaching `resolve-test-scope` | met | test-first | `test_a_persisted_maven_architecture_resolves_module_tests_at_default_scope` + `test_the_resolved_notation_publishes_the_scope_verb_the_arm_calls_next` | c394a95, same log (`architecture_error: Command not found`) |
| PR states a consumer must re-run `architecture discover`, because the command map is persisted at discovery | **not met as written — premise refuted** | — | — | — |

The refutation: `architecture resolve` crawls the live worktree on every read
(`iter_modules` / `load_module_derived` → `crawl_all_modules`); a per-module
`derived.json` is never the source of current state when a live crawl finds
modules, and the on-disk read is the synthetic-project fallback. No re-discover is
required — updating the plugin is enough. Commit `a8073b8fa` carries the spec's
wording verbatim; this landing is the correction.

**D3 — a selector that matched nothing is a named reason: MET.**

| Done-when | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| `No tests matching pattern` yields the named reason and no `test-failure` issue | met | test-first | `test_selector_miss_goal_failure_yields_the_named_reason_and_no_test_failure_issue` + run-path twin | c394a95, `python-2026-11-06-064759.log` |
| `-Dtest` run with zero executed tests is not `success` | met | test-first | `test_dtest_run_with_zero_executed_tests_is_not_success` | c394a95, same log |
| Control: `-Dtest` with an executed test stays `success` | met | none | `test_control_dtest_run_with_an_executed_test_stays_success` | — |
| Guard test pins the SKILL.md grammar sentence | met | test-first | `test_build_maven_skill_states_the_selector_grammar` | c394a95, same log |

Recorded deviation: the population test is the COLLECTED total, not "executed", so
a selector that matched an all-`@Disabled` class is not reported as a miss.

**D4 — the per-task gate reaches the resolved skill's verb: MET.**

| Done-when | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| No literal pyproject scope-verb invocation; the derivation from the resolved executable is named; red at base | met | test-first | `test_step_5b_derives_the_scope_verb_from_the_resolved_build_skill` | c394a95, `python-2026-11-06-064759.log` |

Per-head test runs (pushed heads): 7e8879df5 — module-tests 32867 green; e835ec5e2 —
module-tests 32869 green; 2afd917bd — module-tests 32957 green (post-merge of
origin/main); 55a0dd166 — module-tests 32960 green. CI `verify` green on
7e8879df5, e835ec5e2, 2afd917bd, 55a0dd166; the merge-group run 42257769960 green.

## 2. Personas and skills

| Step | Persona applied |
|---|---|
| D1 parser + fixtures (production code) | persona-implementer |
| D1/D3 tests | persona-module-tester |
| D2 discovery + gate doc | persona-implementer |
| D3 run-path guard + shared boundary | persona-implementer |
| D4 workflow doc | persona-documenter |
| Every self-review round, and triaging every PR comment | persona-code-reviewer |

Skills per deliverable: **none named** (the spec's deliverables carry empty
`Skills:` and `Persona:` fields; `resolve` reported `skills_note: none named`).

Skills added for surface drift: none. The shared-surface edits
(`_build_server_protocol.py`, `_build_execute_factory.py`) were not a domain-skill
matter; their justification is in §4.

## 3. Hypotheses

- `Failures:` / `COMPILATION ERROR :` are generic build errors, not `test_failure` — **confirmed**: both categorize as `other` (`_maven_cmd_parse.py` `MAVEN_PATTERNS` applied to `maven-failure-epilogue.log`).
- The default-scope `resolve` answers from the Maven reactor root module — **confirmed**: the gate test resolves module `probe-parent`.
- The `-pl`-removal widening turns `test-compile -pl X -am` into a malformed `test-compile -am` — **refuted for this path**: the default-scope `test-compile` probe now succeeds, so the fallback is unreached (`test_maven_reactor_root_resolves_test_compile_at_default_scope`).
- No Maven parse path reads the command, so the zero-test check needs the run path — **confirmed**: the guard wraps `execute_direct`; no shared `cmd_run_common` change was needed.
- `architecture resolve --narrow-unit` on a Maven module composes an invalid `-pl` form — **confirmed in a narrower sense**: the Maven `resolve-test-scope` response omitted the narrow-unit fields entirely, which D4 made reachable; the fields are now returned empty (`e835ec5e2`).
- The `-Dtest` zero-executed case is already not `success` at base — **refuted**: the guard had to be added (`test-first` red at c394a95).
- Verify-first (D2): the default-scope resolves produced the `Command not found` shape at base — **confirmed**.
- Verify-first (D3): the D3 fixtures were run at base — **confirmed**, and the zero-executed run was green there.

## 4. Findings

**Self-review round 1** (sub-agent, persona-code-reviewer): 1 blocking, 7 should-fix, 7 nit.
- Blocking: D3's named reason did not survive the routed leg. Fixed in `c20d1d909`, then again in `506e3052a` after round 2 showed the first fix covered only `job_status=success`.
- Fixed: D1 control assertion restored; fixture versions + index rows; stale discovery comments; D2 (b)/(c) checks; `@Disabled` false positive; shared `Issue.detail` prose; guard wiring test; wrapper signature; field carry.
- **Disclosed, not fixed**: the D2 consumer-note criterion (premise refuted) — reported as not met as written.

**Self-review round 2**: 2 blocking, 7 should-fix, 6 nit.
- Blocking: the routed fix did not cover the failure leg (fixed in `506e3052a`); the `total == 0` change was uncommitted (committed in `6bfefe772`).
- Fixed: bare javac continuations + detail de-duplication; persisted-architecture and cascade tests; nested-aggregator test; stale test name; D4 wording.

**Self-review round 3**: 0 blocking, 2 should-fix, 7 nit.
- Fixed: the four unpinned branches (detail de-duplication, unknown-vs-zero, non-finish re-render, window reset) in `7e8879df5`.
- **Open, reported as residue**: the gate branch-6 corner (see §9).

**PR review (CodeRabbit)** — 3 inline findings + 1 additional + 3 inline findings + 1 nitpick across two reviewed heads:
- Round A: selector miss relabelling a real failure (`c87cb4e23`); missing `module-tests` canonical in step 5(b) (`e835ec5e2`); Maven scope response missing narrow-unit fields (`e835ec5e2`); string-search notation assertion → CLI `--help` (`e835ec5e2`).
- Round B: mixed-reactor failure loss, field carry, multiline message (`05805c315`); Maven finding-store coverage (`55a0dd166`).
- Every inline thread: fixed, answered, resolved; CodeRabbit confirmed each as addressed.
- Sourcery (optional): refused on quota at both heads; recorded, not gating.

**CI**: green on every pushed head; the merge-group run green.

## 5. Reviewers

| Reviewer | Required | Result | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | yes (quota-limited) | reviewed | 7e8879df5, 2afd917bd | triggered 12:41Z → refused on quota; waited 90 min; re-triggered 14:30Z → reviewed; re-triggered after each push → 14:58Z refused (23 min notice), 15:55Z "already reviewed the last commit", 16:33Z refused (13 min notice). Last head 55a0dd166: review not obtained (quota), standing authorization applied |
| sourcery | no (optional) | refused | — | triggered 12:41Z → own-review budget exhausted (5 days 12 h); recorded, does not gate |

Standing review authorization, per required reviewer: qualifying review on
7e8879df5 and on 2afd917bd (both PR heads, `final_review_risk_coverage` marker
`kind=reviewed`); every finding from those reviews fixed or answered, every thread
resolved; re-triggered once after the last push with the refusal recorded; every
other gate condition green on 55a0dd166 (CI verify, split build gate, Sonar n/a).

## 6. Operator questions

None asked this run — no blocker required a decision. Free-text operator messages: none.

## 7. Rule check

Guard: `present`. The guard log (`.plan/temp/guard.log`) has **two** entries for this run's session `ses_e508be696ffeLd2OxxZsT0VgWt`, both refusals:
- 07:53:12Z — R1, a `git commit` whose `-m` body contained newlines. Refused; retried as single-line `-m` flags.
- 17:00:36Z — R1, a piped `ci pr comments … | grep …`. Refused; re-read the full output instead.

Both were corrected immediately and no rule was knowingly bent. Everything else in
the run's own actions: no shell file operation was used for reading, searching or
listing (Read/Grep/Glob throughout); the only shell file operations were the
sanctioned git/worktree verbs and the build client; no `python3 -c`, no direct
`./pw`, no direct `ruff`/`mypy`/`pytest`, no `gh`/`glab`; no `sleep` (the 90-minute
review wait used `ci pr wait-for-comments`); no `git stash`/`restore`/`checkout
--`/`rebase`/forced push. One `rm`-free cleanup: `git worktree remove`, no force.
Restarts: none. Killed sub-agents: none. Re-dispatches: two self-review sub-agent
calls (rounds 2 and 3) plus round 1 — each re-read the full diff.

Spec read: `spec_source=ledger_worktree`; no `spec_differ` marker.
Executor-skew: `not_applicable` (source checkout) — answered, recorded, never asked.

Sub-agent rule breaks: none reported by the reviewers; both ran the executor for
their test runs.

## 8. Build server

- Setup preflight: **ready** (`registered: true`).
- Every build routed: `mechanism=daemon_longpoll` on every build in this run; **0** `in_process_fallback`.
- Fallbacks / retries:
  - `verify` at 1195 s: bound expiry (`timeout_used_seconds=1195`, `timeout_source=explicit`) → ran the split form (quality-gate, then module-tests), both green.
  - `quality-gate`: one bound expiry at the 330 s floor (`timeout_source=floor`) → re-ran with `--timeout 900` (raising the bound, not re-submitting it), green.
  - No launch-fault retry was needed.
- `killed` jobs: none.
- `runtime_stamp_reason`: none — the runtime stamp resolved on both the setup and the landing `resolve`.

## 9. Residue

1. **Open (disclosed, not fixed): the gate's scoped branch-6 corner.** Giving the
   root the `module-tests` canonical means `resolve --command module-tests --module
   <module-with-no-tests>` now cascades to the whole-reactor run instead of
   `Command not found`. Branch 6 then runs the whole reactor while its recorded
   `excluded_population` still says only the target module ran. The direction is
   coverage-increasing (never less than asked) and is pinned by
   `test_a_module_without_tests_cascades_to_the_reactor_roots_run`, but reconciling
   branch 6's "do NOT pay the whole-tree cost" invariant with that cascade is a
   follow-up outside this plan's declared surface.
2. `javac`'s `required:` / `found:` continuation fields are still filed as their own
   issues — the same class as `symbol:`/`location:`, outside D1's enumerated scope.
3. The "stated once" corpus guard for the selector grammar is phrase-level: a
   restatement in different words would pass.
4. D2's fourth and fifth Done-whens are not met as written (see §1); the cause is a
   refuted premise in the spec, corrected here and in the PR body.
