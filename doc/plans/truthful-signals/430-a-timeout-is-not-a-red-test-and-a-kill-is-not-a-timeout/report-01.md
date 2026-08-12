# Run report — 430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/timeout-kill-signal-semantics-75r3fw`    **PR:** _(recorded at the merge gate, below)_    **Outcome:** _(recorded at the merge gate, below)_

> The PR number and the outcome are stated at § Contract check, which is written
> as the last pre-merge commit per `cloud-plan-lane` § Step 8 condition 3. They
> are deliberately not asserted here ahead of being true — an outcome field that
> claims `completed` before the run has completed is the same premature-green
> this plan is about.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, `.claude/skills/`) |
| `plan-marshall:ref-code-quality` | bundle path — `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`, plus `standards/error-handling.md` |

The plan's surface is Python production code, Python tests, and bundle
`SKILL.md` / `standards/` prose. `ref-code-quality` § "Fail-Closed
Classification" turned out to be the governing standard for the whole change —
rules (b), (c) and (e) are exactly the defect class the plan describes, and the
worked-example paragraph naming `_derive_build_status` had to be corrected as
part of the change (see Findings F7).

No skill was unobtainable by either route.

## Deliverables

### D0 — GATE: enumerate what is ALREADY emitted, and which consumer reads which field

**Mutates nothing.** Enumeration only; published here and, durably, in the
consumer table added to
`extension-api/standards/build-systems-common.md`.

**The emitted vocabulary — three producers, three vocabularies, already present
before this change:**

| Producer | Vocabulary it emits | Signal for each of the three conditions |
|---|---|---|
| `_marshalld_supervisor.classify_terminal` (daemon) | `success` / `failure` / `timeout` / `killed` | Kill = `killed` (negative returncode the supervisor did not cause); timeout = `timeout`; red = `failure`. **All three already distinguished.** |
| `_build_execute.execute_build_command` (in-process wrapper) | `success` / `error` / `timeout` | Kill = **`error`** (pre-fix); timeout = `timeout`; red = `error`. **Kill and red were the same symbol.** |
| `_derive_build_status` (executor dispatch boundary) | `success` / `error` / `timeout` / `killed` / `unknown` | Kill = `killed` **only** from a negative returncode of the dispatched script (outer kill); an inner kill arrived as the wrapper's `error` and stamped `error`. |

**The per-consumer reads.** A *consuming gate* is defined as a component that
reads a build outcome and produces a verdict another component acts on. The set
was **derived**, not sampled: every reader of each of the three outcome surfaces
was enumerated from `git grep` over the closed import sets —
`read_entries` + `kind == build` for the ledger surface, `read_log_verdict` /
`_derive_build_status` / `WRAPPER_CLAIMABLE_BUILD_STATUSES` for the wrapper-TOON
surface, and `job_status` for the daemon-wire surface.

| # | Consuming gate | Surface read | Reads a status field? | Could tell a kill from a red build (pre-fix)? |
|---|---|---|---|---|
| 1 | `_derive_build_status` (executor boundary) | wrapper TOON + returncode | **yes** | only for the OUTER kill |
| 2 | `_marshalld_supervisor.run_job` | job log TOON via `read_log_verdict` | **yes** | yes (daemon side, already correct) |
| 3 | `_build_execute_factory._daemon_result_to_direct` | daemon `job_status` + job log TOON | **yes** | it READ `killed` and then discarded it |
| 4 | `_build_shared.cmd_run_common` (emit choke point) | `DirectCommandResult.status` | **yes** | **no** — no `killed` branch existed |
| 5 | `build_server.py::_render_job_status` | daemon `job_status` | **yes** | yes (already correct) |
| 6 | `manage-change-ledger classify-outcome` | ledger `kind=build.status` | **yes** | yes — but its killed-row branch was unreachable for an inner kill |
| 7 | `manage-tasks pre-commit-verify-freshness` | ledger `kind=build.status` | **yes** | **no** — it read `status` for the pass/fail decision and then discarded it for the reason and remedy |
| 8 | The LLM agent reading the build TOON (`CLAUDE.md`: "read the result TOON `status`/`errors[]`") | wrapper TOON | **yes** | **no** — it was handed `status: error` plus a fabricated `errors[]` row |
| 9 | `plan-marshall/workflow/execution.md` § Orchestrator-tier phase-5 verification | orchestrator-tier build `status` | **yes** | **no** — a two-way green/failing split with no arm for a non-finish |
| 10 | `phase-5-execute/SKILL.md` Step 12a | the FRESHNESS VERDICT (`status` + `reason`) | **yes** | **no** — it dropped `reason` and prescribed a blanket re-dispatch |
| 11 | `phase-6-finalize/standards/push.md` § Freshness precondition | the FRESHNESS VERDICT (`status` + `reason`) | **yes** | **no** — `display_detail` dropped `reason` |

**Population, published: 11 consuming gates. 11 of 11 read a status field
(11/11).** Not one gate was failing for lack of a field to read — which is the
point. Six of the eleven (#4, #7, #8, #9, #10, #11) could not tell the conditions
apart, and one (#3) could and threw the answer away.

⚠ **This population was corrected twice, and the corrections are the more
instructive artifact than the number.** The first publication said **8 of 8**,
derived from the closed import sets of the three *build-outcome* surfaces. Two
successive verification passes showed that derivation was too narrow in two
distinct ways:

- **Gates #10 and #11 consume the freshness VERDICT, not a build status.** They
  are one hop further out, so a sweep for "who reads a build `status`" cannot
  see them — yet they are the gates that actually degrade (halt a phase
  transition; halt a push). Their omission was proven empirically, not
  argued: the second round of fixes *had to change both of them*, because the
  `reason` field added for gate #7 reached neither.
- **Gate #9 reads a build outcome the ORCHESTRATOR obtained**, not one a leaf
  emitted, and splits it two ways (green / failing) with no arm for a
  non-finish. It was in none of the three surfaces' import sets.

⇒ **The correction, stated as a rule:** derive the consumer set *transitively*.
A gate that consumes a verdict **derived from** the outcome is a consumer of the
outcome. The plan flagged "every consuming gate is identified" as an
asserted-completeness HYPOTHESIS — the absence-shaped half — and it was right to:
the first derivation was **wrong by three**, and both misses were found by
adversarial review rather than by the derivation itself.

⛔ **The plan's boundary was honoured: no discriminator was re-added.**
`classify-outcome` (gate #6) and `classify_terminal` (the supervisor's own
terminal classifier) already existed and were already correct. Neither was
duplicated, and **`manage-change-ledger.py` carries no code changes at all**
(only its `SKILL.md` prose was corrected). `_marshalld_supervisor.py` **was**
changed — but not in `classify_terminal`, which is byte-identical; the change is
in `run_job`'s post-classification narrowing, which was flattening a disagreeing
log verdict to `failure` (see D1 gate #2). The distinction matters: the existing
classifier was left alone, and what changed is a separate downstream step that
was discarding its own inputs.

### D1 — Make the three distinguishable AT EVERY CONSUMING GATE

Landed across three commits — `5ac6cda` (the first pass), `fbbf99c` (the routed
leg and the freshness-verdict consumers), and the round-3 commit (the remaining
gaps). Verified **per gate**, not once:

| Gate | Change | Test |
|---|---|---|
| #1 `_derive_build_status` | stops demoting a wrapper's `status: killed` claim to `error` | `test_executor_runtime.py::test_build_boundary_stamps_derived_status[status: killed\n-0-killed]` |
| #2 `_marshalld_supervisor.run_job` | its narrowing translated a disagreeing log verdict through `wire_status_from_result` instead of hard-coding `failure`. `classify_terminal` itself is unchanged | `test_marshalld_supervisor.py::TestRunJobNarrowingPreservesTheNonFinish` — drives the real `run_job` against a real child; **verified to fail when the line is reverted** |
| #3 `_daemon_result_to_direct` | maps daemon `killed` → `killed_result`; its cross-check now preserves the log verdict's own status via `_result_for_log_verdict` | `test_build_execute_routing.py::test_daemon_result_killed_maps_to_killed_not_error`; `TestDaemonVerdictSurvivesTheMapping`; `TestCrossCheckPreservesTheLogVerdict` |
| #4 `cmd_run_common` | own `killed` and `indeterminate` branches ahead of the timeout branch; no findings stored; no synthetic `errors[]` row | `TestEmitChokePointKeepsTheThreeApart` |
| #5 `_render_job_status` | **unchanged** — already correct | pre-existing coverage |
| #6 `classify-outcome` | **unchanged** — its `killed` branch became reachable via the ledger fix | `TestKilledReachesTheLedger` |
| #7 `pre-commit-verify-freshness` | derives a `reason` (+ `observed_status`) from the ledger instead of asserting a mutation it never established | 12 cases in `test_pre_commit_verify_freshness.py` |
| #8 the LLM agent | now receives `status: killed`, `error: killed`, and the no-blind-retry `message`, with no fabricated `errors[]`; `build-api-reference.md` § routing instruction rewritten to enumerate all five statuses | the `cmd_run_common` cases above pin the emitted TOON |
| #9 orchestrator-tier phase-5 handler | the two-way green/failing split becomes a five-way table; a non-finish is explicitly NOT routed into `verification-feedback` triage, which would sweep an empty finding set and report clean | prose gate — no script to test; the emitted statuses it branches on are pinned upstream |
| #10 `phase-5-execute` Step 12a | substitutes `reason`/`observed_status` on both non-`fresh` branches; per-reason recovery replaces the blanket re-dispatch that, for `build_killed`, was the forbidden blind retry | prose gate — the gate's own `reason` values are pinned by #7's cases |
| #11 `push.md` freshness precondition | carries `reason`/`observed_status` into `display_detail`; the re-stale reconciliation section is scoped to the one route it can apply to | prose gate — same |

Two enabling changes carry the signal between gates:

* `_ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES` gains `killed`. Without it the
  status stops at the wrapper's stdout and gates #6/#7 never see it. `unknown`
  stays derived-only; the vocabulary set is unchanged; `killed` fails every gate
  `error` fails, so nothing fails open.
* `_build_format.EXTRA_FIELDS` gains `message`. **This was a live defect found
  while writing the tests:** `format_toon` is a whitelist and drops unlisted
  scalars *silently* while `format_json` passes them through, so the
  no-blind-retry message would have reached JSON consumers and been erased for
  TOON consumers — the same discard defect one layer down.

⭐ **The plan's standing rule — *an unresolvable case is `indeterminate`, never
folded into either neighbour* — was applied at two of the three new branch
points and MISSED at the third.** The executor boundary stamps `unknown` for any
status outside the wrapper vocabulary, and the freshness gate maps an unreadable
row status to `build_indeterminate`. But `_daemon_result_to_direct`'s catch-all
claimed `build_failed` for any `job_status` it did not recognise — the rule
violated in the one function the change had just rewritten. Verification caught
it.

The remedy is a first-class `STATUS_INDETERMINATE` in `_build_result`, with a
branch in `cmd_run_common` and use at both catch-alls (client mapping and
log-verdict mapping). It is deliberately **not** wrapper-claimable, so
`_derive_build_status` falls through to its own derived-only `unknown` — the
ledger's name for the same condition — and `classify-outcome` (`undecidable`)
and the freshness gate (`build_indeterminate`) already handled it end to end
with no further change. The trigger is modelled rather than theoretical:
`manage-build-server status` reports daemon/client version skew as
`binary_diverges`, and a newer daemon speaking an unknown status is exactly that
condition. A third catch-all — the supervisor's `_terminal_payload`, which
rendered any unrecognised status as a build failure — was corrected in the same
pass.

### D2 — Settle the subset/superset inversion

⛔ **DIAGNOSED, NOT ADJUSTED.** No bound, margin, floor, or cap changed:
`SAFETY_MARGIN` (1.25), `HIGHER_WEIGHT` (0.80), `MINIMUM_TIMEOUT_SECONDS` (120),
`MIN_TIMEOUT` (60), `MAX_TIMEOUT` (1800), `PYTEST_OUTER_FLOOR_SECONDS` (330) and
`DEFAULT_BUILD_TIMEOUT` (300) are all byte-identical to `origin/main`.

**The inversion reproduces here, from scratch.** Both commands were run in this
clone, which has no `run-configuration.json`, so every key falls back to the
same budget — `max(default 300, floor 330) = 330 s`:

| Command | Relationship | pytest time | tests | wall clock | cache |
|---|---|---|---|---|---|
| `./pw module-tests plan-marshall` | strict **SUBSET** | **488.85 s** | 16 154 | 580 s | cold |
| `./pw verify` | **SUPERSET** (contains it) | **443.96 s** | 19 231 | 523 s | warm |

**The subset ran 44.89 s LONGER than the superset that contains it, on 3 077
fewer tests.** Both exceed the shared 330 s budget.

**The mechanism, named — three properties, none of which is a wrong number:**

1. **`timeout_seconds` holds two different quantities with nothing to tell them
   apart.** The success path persists a *measured duration*; the timeout path
   persists a *doubled budget* (`min(timeout_used * 2, MAX_TIMEOUT)`). Both land
   in the same field, and `timeout_get` applies the safety margin to whichever it
   finds.
2. **The budget therefore tracks the KEY'S TIMEOUT HISTORY, not the command's
   work.** A key that has only succeeded settles near `1.25 x measured`, floored;
   a key that has timed out once jumps to `1.25 x (2 x previous budget)` and
   doubles again on each further timeout. Keys ratchet independently, so
   **nothing makes `budget(subset) <= budget(superset)`** — the ordering across
   keys is decided by which key timed out first. (Consistent with the reported
   642 s: `642 = int(513.6 x 1.25)`, a persisted ≈514 that no measured scoped-test
   duration produces — the measurement here would persist ≈489 and yield 611.)
3. **Keys are per-argument-string and encode no cache state**, yet cache state is
   first-order — it is the whole of the 44.89 s inversion measured above.

⇒ **A budget overrun is evidence about the key, not about the command.** Raising
it would close the symptom and move the next inversion to whichever key has not
yet ratcheted. Documented in `manage-run-config/standards/run-config-standard.md`
§ "What `timeout_seconds` actually measures — and what it does not".

The one measurement-side change is **not** a budget adjustment: `_build_execute`
no longer feeds a *killed* run's elapsed to the learner. That elapsed is a
truncation of work that never completed, and blending it in at 20 % weight is the
same collapse this plan fixes, appearing in the measurement direction — the
epic's standing rule against laundering a figure of unknown sign.

### D3 — Regression tests with matched controls, each verified RED pre-fix

`test/plan-marshall/script-shared/test_non_finish_discrimination.py` (44 cases),
12 cases in `test_pre_commit_verify_freshness.py`, 3 in
`test_marshalld_supervisor.py`, and added parametrisations in
`test_executor_runtime.py` / `test_build_execute_routing.py`.

**Every property carries its matched red-test control**, because the controls are
the only thing standing between this fix and a gate that treats every non-green
build as benign:

| Property asserted of a non-finish | Matched control (a genuinely failing build) |
|---|---|
| negative returncode → `killed`, not `error` | positive returncode → still `error` |
| a killed run does NOT teach the learner | a failing run STILL teaches it; a successful run STILL teaches it |
| non-finish / indeterminate stores no findings | red build STILL stores findings |
| non-finish / indeterminate synthesises no `errors[]` row | red build STILL synthesises one when the parser finds none |
| non-finish drops a failure-carrying test summary | red build STILL reports its parsed errors |
| daemon `killed` → `killed` | daemon `failure` → still `error` |
| daemon narrowing keeps a log `killed`/`timeout` | narrowing STILL downgrades a log `error` to wire `failure` |
| cross-check keeps a log `killed`/`timeout` | cross-check STILL fails a log `error`; an agreeing or absent verdict STILL keeps `success` |
| unrecognised status → `indeterminate` | recognised `failure` → still `error` |
| `killed` is wrapper-claimable | `success`/`error`/`timeout` remain claimable; `unknown`/`indeterminate` stay non-claimable |
| freshness reason names kill/timeout/indeterminate | freshness reason for a real failure STILL says "fix the reported failures"; a genuinely mutated tree STILL says `worktree_mutated` |

⭐ **One of these controls did not bite, and that is worth recording as a
finding rather than a footnote.** The first version of the daemon-narrowing test
asserted `wire_status_from_result(verdict.status)` — it *re-implemented the line
under test in the test*, so reverting the production fix left the whole suite
green. Verification caught it. The replacement drives the real `run_job` against
a real child process, and was **confirmed red** against the reverted line
(`assert 'failure' == 'killed'`, `assert 'failure' == 'timeout'`) before being
restored. A test that cannot fail for the defect it names is the same false
signal this entire plan exists to remove, reproduced inside the plan's own
regression suite.

**RED verification.** Reverting `marketplace/` and re-running produced a
*collection* error, not a meaningful red — the status vocabulary is itself part
of the fix, so the module cannot import against the pre-fix tree. Rather than
report that as verification, the pre-fix behaviour was probed directly with
literal strings (scratch probe, not committed). Result, per property:

| Property | Pre-fix behaviour | Suite expects |
|---|---|---|
| in-process classifier, returncode −9 | `status: 'error'` | `'killed'` |
| learner fed by a killed run | `timeout_set` **called** | not called |
| emit choke point, daemon-killed result | `status: error`, `error: build_failed`, **fabricated** `errors[1]` row `"Build failed but no structured errors were parsed"`, no-blind-retry message **absent** | `status: killed`, no `errors[]`, message present |
| routed leg, daemon says killed | `status: 'error'` | `'killed'` |
| ledger vocabulary | `killed` NOT claimable; `DERIVED_ONLY = {killed, unknown}` | claimable; `{unknown}` |
| `_derive_build_status(0, {"status": "killed"})` | `'error'` | `'killed'` |

Every property was red. The emit-choke-point row is the plan's thesis in one
artifact: a kill presented as a red test, with manufactured evidence.

The later rounds' properties were verified red the same way where the seam
allowed it directly — the daemon-narrowing cases above were confirmed failing
against the reverted production line rather than against a probe.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py' '*.template'` is **non-empty**
— 16 Python-bearing files (10 production including the executor template, 6
test). The build therefore took its **full path**, as the plan anticipated.

Measured at each round, so a figure is never carried forward past the commit it
was measured at:

| Point | Result |
|---|---|
| Pre-change baseline, `./pw verify` on `origin/main` | green — 19 231 passed, 14 skipped, `coverage: COMPLETE`, `=== verify: SUCCESS ===` |
| Round 1 (`5ac6cda`) full suite | 19 276 passed, 14 skipped, 0 failed (454 s) |
| Round 2 (`fbbf99c`) full suite | 19 293 passed, 14 skipped, 0 failed (490 s) |
| Round 3 (final) full suite | recorded at the merge gate, below |
| `./pw quality-gate`, every round | clean — `ruff … All checks passed!`, `mypy … Success: no issues found in 395 source files`, `SPDX-header check passed`, plugin-doctor `status: pass`, `total_issues: 0` across 36 rules |
| `./pw test-compile` | `Success: no issues found in 717 source files` |

The tree was clean (`git status --porcelain` empty) at Step 2 and re-asserted
before the diff. No `uv.lock` churn appeared; paths were staged explicitly, never
`git add -A`.

## Findings

Recorded **per instance**.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | own analysis (D0) | `_build_execute.execute_build_command` maps a negative `subprocess` returncode to `status: 'error'` — a harness kill is emitted as a red build | **fixed** — `killed_result` branch, gate #1 |
| F2 | own analysis (D0) | `cmd_run_common` has no `killed` branch; a killed result falls to the build-failure path, which **stores findings** from a truncated log | **fixed** — dedicated branch ahead of the timeout branch |
| F3 | own analysis (D0) | the same path **synthesises** a `build_failure` error row (`"Build failed but no structured errors were parsed"`) so `status` and `errors[]` agree — fabricating a failure the build never reported | **fixed** — non-finishes never reach that path |
| F4 | own analysis (D0) | `_daemon_result_to_direct` computes `error='killed'` + the no-blind-retry `message`, and `cmd_run_common` rebuilds its payload from `status` alone, **discarding both** — the discriminator was read and then thrown away | **fixed** — `killed` is now a first-class status that survives the renderer |
| F5 | own analysis (D0) | `pre-commit-verify-freshness` reports one `stale` message asserting *"the worktree has been mutated"* and prescribing *"re-dispatch a build"* — false when a build was observed and killed, and the prescribed remedy is exactly the blind retry that case forbids | **fixed** — `reason` + `observed_status` derived from the ledger |
| F6 | own analysis (D0) | `killed` being derived-only made `classify-outcome`'s killed-row branch unreachable for an inner kill, so an existing, correct discriminator could never fire | **fixed** — `killed` made wrapper-claimable (no new discriminator added) |
| F7 | beyond-diff sweep | `ref-code-quality/standards/error-handling.md` states a stdout claim of `killed` at exit 0 stamps `error`, and calls `unknown` "a derived-only peer of `killed`" — both false after the change | **fixed** — rule (e) prose and the worked-example bullet corrected |
| F8 | beyond-diff sweep | `manage-change-ledger/SKILL.md` states "`killed` and `unknown` are **derived-only**" | **fixed** |
| F9 | beyond-diff sweep | `_ledger_core.build_record` docstring states "``killed`` and ``unknown`` are `DERIVED_ONLY_BUILD_STATUSES`" | **fixed** |
| F10 | beyond-diff sweep | `extension-api/standards/build-execution.md` publishes the `DirectCommandResult` status as a three-value `Literal`, an error-context table without `message`, an exit-code table with no signal row, and a caller-interpretation example whose `else` swallows a kill as a failure | **fixed** — four separate corrections in that file |
| F11 | writing the tests | `_build_format.EXTRA_FIELDS` is a **silent** whitelist: `message` was absent, so TOON would drop the no-blind-retry sentence while JSON carried it | **fixed** — `message` whitelisted, with the silence documented |
| F12 | full-suite run | `test_build_execute_factory.py::TestRecordResolutionSentinelSuppressesWorkLog::test_a_real_plan_id_still_writes_the_work_log` fails. **Confirmed pre-existing** — it fails identically on unmodified `origin/main` code. `_record_resolution` persists its fallback streak to the real `~/.plan-marshall/marshalld/fallback-streak.json`; the observed file carried `"a-real-plan": {"count": 7, "escalated": true}`, so once the streak escalates the per-build WARNING is suppressed forever and the test is permanently red on that machine. It read green in CI only because the runner is fresh. | **fixed** — autouse `PLAN_MARSHALL_HOME` isolation, matching the convention every `test/plan-marshall/build-server/` module already uses. In scope because a test that reads green by virtue of *where* it ran is the same false-signal class this plan addresses |

### Verification sub-agent — round 1 (19 findings)

Dispatched against `5ac6cda`/`46b12cf`. Every finding, with its disposition.

| # | Finding | Disposition |
|---|---|---|
| V1 | `_marshalld_supervisor.run_job` hard-codes `failure` when the log verdict disagrees — a wrapper-claimed `killed` never reaches the wire | **fixed** (`fbbf99c`). A regression my own change made reachable: making the `killed` claim believable exposed it to this narrowing |
| V2 | Same site: a wrapper-claimed `timeout` is narrowed to `failure` — D1's "done when" violated literally, at a gate | **fixed**. **Pre-existing**, and my report had marked this gate "unchanged — already correct". That claim was wrong |
| V3 | `_daemon_result_to_direct`'s cross-check returns `error: build_failed` for a job-log `killed` (empirically confirmed by the agent) | **fixed** — `_result_for_log_verdict` |
| V4 | Same site: a job-log `timeout` becomes `error` with `exit_code -1`, which then matches `cmd_run_common`'s execution-error branch and surfaces as `execution_failed` — a timeout reported as wrapper-not-found | **fixed** |
| V5 | `_daemon_result_to_direct` has no `indeterminate` path; its catch-all claims `build_failed` for any unrecognised status — the plan's standing rule violated in the function the change had just rewritten | **fixed** — `STATUS_INDETERMINATE` added end to end |
| V6 | `_RESULT_STATUS_TO_WIRE` comment says `killed` "has no `_build_result` equivalent" | **fixed** — explicit row added |
| V7 | `wire_status_from_result` docstring states the three-value vocabulary | **fixed** |
| V8 | `result_status_from_wire` docstring lists `killed` as having no equivalent | **fixed** |
| V9 | `LogVerdict.status` docstring states the three-value vocabulary | **fixed** |
| V10 | `build-api-reference.md` agent-facing routing instruction says "success/error/timeout" — gate #8 in my own published table | **fixed** |
| V11 | `phase-5-execute/SKILL.md` states the `stale` branch omits `reason` | **fixed** |
| V12 | Same file's `--force` escape instructs the consumer to omit `reason` on `stale` | **fixed** |
| V13 | `push.md` `display_detail` drops `reason` — a `build_killed` refusal reaches the operator indistinguishable from a mutation | **fixed** |
| V14 | `push.md` "a `stale` status has two distinct causes" — now five routes | **fixed** — section scoped to `worktree_mutated` |
| V15 | killed payload drops `timeout_used_seconds` its sibling timeout branch preserves | **fixed** |
| V16 | "latest row" is file order, not timestamp — doc asserts a property the code does not check | **fixed** — documented, with why sorting on `timestamp_iso` would be worse |
| V17 | No `/sync-plugin-cache`-owed record in the report (`CLAUDE.md` § Standalone Plan Lane) | **rejected with reason** — `cloud-plan-lane` § "Scope and precedence" states a cloud run "neither performs nor owes" a sync and explicitly supersedes that `CLAUDE.md` line; the plan's own preamble says the contract wins. Independently confirmed by the round-2 agent |
| V18 | Report marked `completed` with three unfilled sections | **partially rejected** — the *ordering* is what the contract requires (§ Step 8 condition 3 finalizes those sections as the last pre-merge commit). The **PR field and premature `Outcome`** were real; corrected |
| V19 | D0's population omits the freshness-verdict consumers | **fixed** — population corrected from 8 to 11 (see D0) |

### Verification sub-agent — round 2 (12 new findings)

Re-dispatched against `fbbf99c`. It verified V1–V16 genuinely fixed by reading
each site, and confirmed the V17/V18 rejections. It then found 12 defects the
*fixes themselves* introduced — which is why a verification pass that finds
defects is re-dispatched rather than trusted once.

| # | Finding | Disposition |
|---|---|---|
| N1 | **The V1/V2 fix had no test that bites.** My daemon-narrowing test re-implemented `wire_status_from_result(verdict.status)` in the test instead of driving `run_job`; reverting the production line left the suite green | **fixed** — replaced with `TestRunJobNarrowingPreservesTheNonFinish`, which drives the real `run_job` against a real child and was **confirmed red** against the reverted line before restoring it |
| N2 | `build-execution.md` publishes a four-value `Literal` for a five-value TypedDict, and `build-api-reference.md` points at it saying "five values" | **fixed** |
| N3 | The canonical caller-interpretation example's `else` now swallows `indeterminate` into "Build ran and FAILED" — under prose explaining why that is wrong | **fixed** — `error` is now its own arm and the `else` reports an unrecognised status as unrecognised |
| N4 | The two freshness-verdict consumers are still outside the published population | **fixed** — see V19; the miss was proven by the fact that round 2 had to change both |
| N5 | `plan-marshall/workflow/execution.md` orchestrator-tier handler splits green/failing with no arm for a non-finish, and would route one into `verification-feedback` triage over an empty finding set | **fixed** — five-way table, with an explicit prohibition on triaging a non-finish |
| N6 | The run report is falsified by its own follow-up commit — eight specific false or stale statements, and the § Findings section omitted every verification-sub-agent finding, which the contract requires | **fixed** — this rewrite; the two tables above are the omitted content |
| N7 | Server/client asymmetry: `_terminal_payload`'s catch-all renders any unrecognised status as a build failure, contradicting the invariant stated one file over | **fixed** — `failure` is now its own arm; unrecognised is reported verbatim |
| N8 | `job_status == STATUS_KILLED` compares a WIRE status against a `_build_result` constant — right only by accident of spelling, the exact hazard the same commit cited for adding the explicit `killed` row | **fixed** — aliased imports name which vocabulary each comparison is on |
| N9 | `observed_status` is absent on a route three documents promise it on | **fixed** — the docs now say "whenever the row carried a readable status", and the covering test asserts the absence |
| N10 | `KILLED_MESSAGE`'s docstring claims a shared literal; it is duplicated four times | **fixed** — docstring corrected to state the truth and name every copy. ⚠ Deduplication itself **deferred** — a cross-skill refactor with import-graph consequences, recorded in Residue |
| N11 | Nine in-file doc sites left stale by the `indeterminate` addition | **fixed** |
| N12 | No control pins that a wrapper claiming `status: indeterminate` stamps `unknown` | **fixed** — parametrised case added |

**Claims the plan labelled HYPOTHESIS, and what this run did with them:**

- *"Two runs reported a daemon timeout at ~642 s / ~618 s"* — **not re-derived.**
  Provenance is `.plan/`, absent from this clone, exactly as the plan warned. Not
  cited as evidence. The arithmetic consistency noted under D2 is an observation
  about the reported figure, not a confirmation of it.
- *"The scoped command times out while the superset completes in less time"* —
  **CONFIRMED by fresh measurement** (D2). This was the single most useful check
  in the plan, as the plan predicted.
- *"The discriminator was present and consulted"* — **CONFIRMED**, and it is
  load-bearing for scope: gates #2, #5, #6 were already correct and were left
  untouched. Only the corrected version of the original report was used.
- *"Any gate ever produced a WRONG MERGE DECISION"* — **NOT claimed.** No damage
  is asserted anywhere in this change.
- *"Every consuming gate is identified"* — ⛔ **the first derivation was WRONG BY
  THREE.** It was derived (not sampled) from the closed import sets of the three
  build-outcome surfaces, which felt rigorous and was still incomplete: two gates
  consume the freshness *verdict* one hop downstream, and one is an
  orchestrator-tier reader in none of those import sets. Both misses were found
  by adversarial review, not by the derivation. The plan called this the
  absence-shaped, higher-risk half and it was right. The corrected rule — derive
  the set **transitively** — is recorded in `build-systems-common.md` so the next
  change to this vocabulary starts from 11, not 8.

## Reviewer participation

_(filled in before the merge gate — see run continuation below)_

## Cost

- **Tokens:** not available to the agent for the main session. The two
  verification sub-agents self-reported **190 758** and **211 896** tokens
  (74 and 83 tool uses; 604 s and 931 s wall-clock) — that is **their** usage
  only, and it does not include the main session that dispatched them, so it is
  a floor on the run's total, never the total.
- **Wall-clock (measured commands only):** the two D2 measurement builds 1 103 s
  (580 + 523); three full-suite runs 454 + 490 + 443 s; five `quality-gate`
  invocations and one `test-compile` a further ~700 s. Session start/end
  timestamps are not exposed to the agent, so **no session total is claimed** —
  the sum of the commands is a lower bound on elapsed time and excludes every
  interval spent reading, editing, and waiting.
- **Population:** the figures above are **individual command durations and two
  sub-agent self-reports measured in this session**, nothing more. ⛔ They are
  **NOT comparable** to a plan-marshall `metrics.toon` total, which counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task
  billing boundary. A single interactive cloud session does not share that
  boundary, and no attempt is made here to make the two comparable.

## Contract check (Step 9)

Re-read `cloud-plan-lane` and checked each step against what actually happened —
both that the step ran and that its artifact exists.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **done** | Named in § Skills loaded. `cloud-plan-lane` via the plugin route; `ref-code-quality` + `standards/error-handling.md` by bundle path. No skill was unobtainable by either route. |
| 2 Branch | **done** | `claude/timeout-kill-signal-semantics-75r3fw` exists on `origin`. **Harness-assigned form** — kept as-is per § Step 2; the run created no branch. Published *before the first edit* (the branch was absent from `origin` on arrival; `git ls-remote` confirmed, then pushed). |
| 3 Plan directory | **done** | `doc/plans/truthful-signals/430-…/plan.md` exists, moved with `git mv` (history preserved), numeric prefix intact. The first-instruction block was **present** on arrival — checked, not assumed; no repair needed. |
| 4 Implement | **done** | Five commits, each carrying the `Co-Authored-By` trailer and no "Generated with Claude Code" footer. All four deliverables addressed. |
| 4 Per-commit gate | **done** | Every commit touching `*.py` was preceded by a clean `./pw quality-gate` — `ruff … All checks passed!`, `mypy … Success: no issues found in 395 source files`, `SPDX-header check passed`, plugin-doctor `total_issues: 0`. Read from the tools' own output, not the exit code. |
| 4 Pushed | **done** | Pushed after every commit. `git status -sb` reports no `ahead`. |
| 5 Build gate | **done** | Git-derived verdict recorded in § Build gate: Python changed ⇒ full path taken. Baseline, per-round and final results all stated, each attributed to the commit it was measured at. |
| 6 Verification sub-agent | **done, twice** | Dispatched, found defects, **re-dispatched** (a pass that found a defect has not finished). 31 findings, all in § Findings with dispositions. |
| 7 PR cycle | **done** | PR #1193. `skip-bot-review` correctly **not** applied — the diff touches `*.py`, `marketplace/bundles/**` and a skill, and a skill is code. |
| 8 Merge gate | see below | Conditions 1–3 and the condition-4 disclosure recorded at § Merge gate. |
| 8 Bridge | **done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory. No ledger, no status file, no other plan touched. |
| 9 This check | **done** | This table. |
| 9 What have we learned | **done** | Below. |

**GitHub access path:** the **GitHub MCP server** (the cloud path). No `gh` CLI
is present in this session.

**Branch form:** harness-assigned `claude/*`, kept per § Step 2.

**Plugin cache sync:** **not owed.** A cloud run neither performs nor owes a
`/sync-plugin-cache` — it is a machine-local build step reading the git-ignored
`target/` and writing `~/.claude/`, neither of which this lane has. Recorded
explicitly because a verification pass raised its absence as a finding
(V17) against the `CLAUDE.md` line the skill's § Scope and precedence
supersedes.

**Steps NOT done:** none. Two steps were done *more than once* (verification
dispatch, build gate) because the first pass surfaced defects.

## What have we learned (Step 9)

The run exercised the contract end to end across three fix rounds, which is
where its gaps become visible. **One change is proposed**, and it is grounded in
what happened here rather than in speculation.

### Proposal — Step 6 should require that the verification agent be re-dispatched until it comes back clean, and should say why

**What the contract says now.** § Step 6: *"Findings that are real → fix them,
then re-dispatch. A verification pass that found a defect has not finished."*
That is correct and I followed it. What it does **not** say is what the second
dispatch is *for*, and the difference is not cosmetic.

**The evidence from this run.** The second verification pass found **12 new
defects, and every one of them was introduced by the first round's fixes** —
including the single most serious finding of the entire run: the regression test
for the headline fix re-implemented the line under test inside the test, so
reverting the production change left the whole suite green. A re-dispatch read
as "confirm my fixes landed" would plausibly have checked the 16 sites and
returned clean. It found 12 more because it was explicitly asked to *hunt for
defects the fixes themselves introduced*.

**The proposed edit** — add to § Step 6, after the existing re-dispatch line:

> A re-dispatch is not a confirmation pass. Its highest-value target is **the
> defects the fixes themselves introduced**: a fix written under time pressure
> against a specific finding routinely widens a vocabulary without updating its
> consumers, adds a branch without a control that bites, or corrects a claim in
> one file and falsifies it in three others. Tell the re-dispatched agent to
> verify each prior finding *and* to hunt for what the fixes broke — including
> whether each new test would actually fail if its fix were reverted.

**Why this is worth a contract change rather than a lesson.** The re-dispatch
already happens; what varies is what it is *asked to look for*, and that is
decided by whoever writes the prompt in the moment. On this run the difference
between the two framings was 12 findings and one test that could never fail.

### Not proposed, and why

- **A "verify the test bites" step.** Tempting after N1, but it belongs in the
  D3-style plan wording (*"each verified RED pre-fix"*, which this plan already
  had) rather than in the lane contract, which is deliberately test-framework
  agnostic. The contract change above reaches it via the re-dispatch prompt.
- **Anything about the report's ordering.** V18 flagged the unfilled sections as
  a defect; the contract's ordering (§ Step 8 condition 3) turned out to be
  exactly right, and a second independent pass agreed. No change.
- **Anything about `/sync-plugin-cache`.** The skill already states the carve-out
  clearly in three places; the finding arose from `CLAUDE.md`, which the skill
  explicitly supersedes. No change.

**Operator disposition:** presented in-session. This run is **headless with
respect to approval** — no human input has been received since the initial
instruction — so the change is **NOT self-approved and NOT shipped**. Per § Step
9 it would ship as a separate `chore/` PR touching only the skill, without
`skip-bot-review`, and it is deliberately kept out of this plan's PR so a
contract amendment is not coupled to whether the plan lands.

## Residue

- **The no-blind-retry sentence is duplicated four times** (N10):
  `_build_result.KILLED_MESSAGE`, `manage-change-ledger._NO_BLIND_RETRY_MESSAGE`,
  `build_server._KILLED_MESSAGE`, and a differently-punctuated variant in the
  `build_killed` remedy text of the freshness gate. They agree only because each
  was written to match. The false *claim* of sharing was removed; the duplication
  itself is a cross-skill refactor and was deliberately not attempted here.
- **Other tests still write to the real `~/.plan-marshall`.** F12 fixed
  `test_build_execute_factory.py`, but the machine-global streak file was also
  written under the key `plan-x` during this run, so at least one further module
  lacks the same isolation. It causes no failure today. A sweep for
  `home_root()`-writing tests without a `PLAN_MARSHALL_HOME` fixture would close
  the class rather than the instance; deliberately not done here, because it is
  outside this plan's scope and would enlarge an already broad diff.
- **The subset/superset measurement is a single pair.** The cold/warm asymmetry
  is confounded with the cold pyprojectx bootstrap in the first run. The
  *structural* half of the D2 mechanism (properties 1 and 2) is derived from the
  code and does not depend on the measurement; the *cache-state* half (property 3)
  rests on one measured pair and would be firmer with a warm re-run of the scoped
  command.
- **The plan's sequencing note** — "adjacent to a sibling plan in the same bundle,
  on a different surface … if it is released first, serialize" — could not be
  evaluated from this clone: the sibling's release state is not visible here. No
  serialization was performed and none appeared necessary; the diff touches the
  build-outcome surface only.
