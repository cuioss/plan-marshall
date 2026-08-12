# Run report — 430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/timeout-kill-signal-semantics-75r3fw`    **PR:** _(see below)_    **Outcome:** completed

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

**Population, published:** **8 consuming gates. 8 of 8 read a status field
(8/8).** Not one gate was failing for lack of a field to read — which is the
point. Three of the eight (#4, #7, #8) could not tell the three conditions
apart, and one (#3) could and threw the answer away.

⛔ **The plan's boundary was honoured: no discriminator was re-added.**
`classify-outcome` (gate #6) and `classify_terminal` (gate #2) already existed
and were already correct; **neither was duplicated and neither was rewritten.**
The change made gate #6's existing `killed` branch *reachable* for an inner kill
rather than building a second classifier beside it. This is verified by the
diff: `manage-change-ledger.py` and `_marshalld_supervisor.py` carry **no code
changes at all** (`manage-change-ledger.py` is untouched; only `SKILL.md` prose
was corrected).

### D1 — Make the three distinguishable AT EVERY CONSUMING GATE

Commit `5ac6cda`. Verified **per gate**, not once:

| Gate | Change | Test |
|---|---|---|
| #1 `_derive_build_status` | stops demoting a wrapper's `status: killed` claim to `error` | `test_executor_runtime.py::test_build_boundary_stamps_derived_status[status: killed\n-0-killed]` |
| #2 `classify_terminal` | **unchanged** — already correct | pre-existing coverage |
| #3 `_daemon_result_to_direct` | maps daemon `killed` → `killed_result`, not `error_result` | `test_build_execute_routing.py::test_daemon_result_killed_maps_to_killed_not_error`; `test_non_finish_discrimination.py::TestDaemonVerdictSurvivesTheMapping` |
| #4 `cmd_run_common` | own `killed` branch ahead of the timeout branch; no findings stored; no synthetic `errors[]` row | `TestEmitChokePointKeepsTheThreeApart` (11 cases) |
| #5 `_render_job_status` | **unchanged** — already correct | pre-existing coverage |
| #6 `classify-outcome` | **unchanged** — its `killed` branch became reachable via the ledger fix | `TestKilledReachesTheLedger` |
| #7 `pre-commit-verify-freshness` | derives a `reason` (+ `observed_status`) from the ledger instead of asserting a mutation it never established | 11 new cases in `test_pre_commit_verify_freshness.py` |
| #8 the LLM agent | now receives `status: killed`, `error: killed`, and the no-blind-retry `message`, with no fabricated `errors[]` | the `cmd_run_common` cases above pin the emitted TOON |

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

⭐ The plan's standing rule — *an unresolvable case is `indeterminate`, never
folded into either neighbour* — is honoured at both new branch points: the
executor boundary still stamps `unknown` for any status outside the wrapper
vocabulary (pinned by two added cases), and the freshness gate maps an unknown
or unrecognised row status to `build_indeterminate` rather than to a neighbour
(pinned by a parametrised case including a deliberately unrecognised literal).

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

`test/plan-marshall/script-shared/test_non_finish_discrimination.py` (32 cases,
4 seams) plus 11 cases added to `test_pre_commit_verify_freshness.py`.

**Every property carries its matched red-test control**, because the controls are
the only thing standing between this fix and a gate that treats every non-green
build as benign:

| Property asserted of a non-finish | Matched control (a genuinely failing build) |
|---|---|
| negative returncode → `killed`, not `error` | positive returncode → still `error` |
| a killed run does NOT teach the learner | a failing run STILL teaches it; a successful run STILL teaches it |
| non-finish stores no findings | red build STILL stores findings |
| non-finish synthesises no `errors[]` row | red build STILL synthesises one when the parser finds none |
| non-finish drops a failure-carrying test summary | red build STILL reports its parsed errors |
| daemon `killed` → `killed` | daemon `failure` → still `error` |
| `killed` is wrapper-claimable | `success`/`error`/`timeout` remain claimable; `unknown` stays derived-only |
| freshness reason names kill/timeout/indeterminate | freshness reason for a real failure STILL says "fix the reported failures"; a genuinely mutated tree STILL says `worktree_mutated` |

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

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (7 Python
files: 5 production, 4 test — one `.template` also carries Python). The build
therefore took its **full path**, as the plan anticipated.

- **Pre-change baseline** (`./pw verify` on `origin/main`): green — 19 231
  passed, 14 skipped, `coverage: COMPLETE`, `=== verify: SUCCESS ===`.
- **Per-commit gate** (`./pw quality-gate`, before the implementation commit):
  clean — `ruff … All checks passed!`, `mypy … Success: no issues found in 395
  source files`, `SPDX-header check passed`, plugin-doctor `status: pass`,
  `total_issues: 0` across 36 rules.
- **Post-change full suite:** **19 276 passed, 14 skipped, 0 failed** (454.49 s).
- `./pw test-compile`: `Success: no issues found in 717 source files`.

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
- *"Every consuming gate is identified"* — the set was **derived** from the closed
  import sets of the three outcome surfaces rather than assembled by looking; the
  derivation method is stated under D0 so it can be re-run.

## Reviewer participation

_(filled in before the merge gate — see run continuation below)_

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** the two D2 measurement builds account for 1 103 s (580 s + 523 s);
  the post-change full suite 454 s; the pre-commit and pre-PR quality gates a
  further ~300 s. Session start/end timestamps are not exposed to the agent, so no
  total is claimed.
- **Population:** the figures above are **individual command durations measured in
  this session**, nothing more. ⛔ They are **NOT comparable** to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary. A single interactive cloud session
  does not share that boundary, and no attempt is made here to make the two
  comparable.

## Contract check (Step 9)

_(filled in before the merge gate)_

## What have we learned (Step 9)

_(filled in before the merge gate)_

## Residue

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
