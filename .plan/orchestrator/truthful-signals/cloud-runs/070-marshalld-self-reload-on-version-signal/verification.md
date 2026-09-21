# Verification — 070-marshalld-self-reload-on-version-signal

**Verified against:** commit `ac06e4fc`   **Landed as:** PR #1152, commit `8f3c7fe0`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding is distinguishable from an unexamined one:

- Read `plan.md` and `report-01.md` in full; extracted all six deliverables with their *Done when*
  conditions, the Out-of-scope list, the Expected surface, the Claim-labels table and the Verification
  section.
- Located the landed commit with `git log --oneline --all --grep '#1152'` → `8f3c7fe0`
  (15 files, +1598/−34). Read the full diff of every production file it touched.
- Checked for later supersession with `git log --oneline 8f3c7fe0..HEAD -- <each touched file>`.
  **Corrected during adversarial review:** re-running the sweep over the *complete* file list from
  `git show --name-only 8f3c7fe0` returns **three** later commits, not two — `d4ae2e81` (#1193,
  `_build_execute_factory.py`), `6514cf24` (#1290, `test_acceptance_resolution_log.py` +
  `test_fallback_escalation.py`) and `9135f275` (#1287, `phase-1-init/SKILL.md`), which the original
  enumeration missed. `9135f275`'s diff on that file is confined to the
  `session_id` → `session_ids` rename in the Step 3a check and does **not** touch the D5 preflight
  line at `:962`. The conclusion — no later commit reverts this plan's surface — is unchanged.
- Opened at HEAD: `manage_build_server.py` (`run_status`, `_read_process_argv`,
  `_running_binary_path`, `_ping`, `run_upgrade`, `run_drain`, `_start_daemon`, `_build_arg_parser`),
  `marshalld.py` (`Daemon._ping`), `_marshalld_scheduler.py` (`running_count`, `queued_count`,
  `available_slots`), `_build_execute_factory.py` (`_update_fallback_streak`, `_write_fallback_state`,
  `_record_resolution`, `_route_to_daemon`), `build_server.py` (`run_preflight`, `run_submit`,
  `run_wait`, `_audit_log`), `reconcile_daemon.py` (whole file), `marketplace_paths.home_root` /
  `resolve_home`, `toon_parser._parse_value`, both sync `SKILL.md` files, `manage-build-server/SKILL.md`,
  `phase-1-init/SKILL.md`, `marshall-steward/SKILL.md`.
- Tree sweeps (`grep -rn`): `binary_path`, `running_binary_path`, `no action required` /
  `Preflight ready`, `socket_absent`, `manage-build-server status`, `ping`.
- Ran the plan's tests: `uv run python -m pytest test/sync-plugin-cache/test_reconcile_daemon.py
  test/plan-marshall/build-server/test_manage_build_server.py
  test/plan-marshall/build-server/test_daemon_ping_counts.py
  test/plan-marshall/build-server/test_fallback_escalation.py -o addopts="" -q` → **60 passed in 4.02s**.
- Re-derived the report's "67 tests" figure: `def test_` counts are 19 + 29 + 2 + 10 + 6 = 66 across
  the five files, plus one `@pytest.mark.parametrize('child_execution_mode', ['auto','daemon'])` in
  `test_acceptance_resolution_log.py:190` → **67 collected**. Figure confirmed.
- **Executed** `reconcile_daemon.decide()` on a hand-built status dict rather than reading it, to
  settle the missing-counts case (result below).
- **Mutation 1 (the BUSY guard, the plan's highest-risk safety property):** replaced
  `if in_flight > 0 or queued > 0:` with `if False:` in `reconcile_daemon.decide` →
  `test_busy_and_stale_decides_defer_not_upgrade`, `test_queued_work_also_counts_as_busy`,
  `test_busy_defer_never_runs_a_reconcile_verb_and_writes_marker` and
  `test_defer_count_increments_across_busy_syncs` all went **RED** (4 failed, 15 passed). Not vacuous.
- **Mutation 2 (the D4 fail-closed substitution — the exact defect the plan names):** replaced the
  `running_binary_path if … is not None else _UNKNOWN_PROVENANCE` expression with
  `running_binary_path or resolved_binary_path` → `test_status_unknown_provenance_never_falls_back_to_resolved`
  and `test_status_unknown_when_argv_has_no_marshalld_token` went **RED** (2 failed, 27 passed). Not vacuous.
- Both mutations were reverted by copying back byte-for-byte copies saved to the scratchpad before
  mutating (`cp <scratchpad>/<file>.bak <path>`); no `git checkout`/`restore`/`stash` was used. Neither
  file appears in `git status --porcelain` afterwards. (Other files do appear dirty in this shared
  checkout — `phase-6-finalize/standards/branch-cleanup.md`,
  `tools-script-executor/templates/execute-script.py.template`,
  `workflow-integration-git/scripts/git-workflow.py`, and two sibling plan directories — none of which
  this verification touched or read-modified.)

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: settle the idle-conditional reconcile contract | contract recorded, naming exact `status` fields and the exact reconcile call per case | yes | yes | **partial** | **partial** | Contract table in `report-01.md` § D1 GATE; fields exist: `marshalld.py::Daemon._ping` returns `in_flight`/`queued`; `_marshalld_scheduler.py:105,110` `running_count`/`queued_count`; `manage_build_server.py:669` surfaces them. Stop condition correctly resolved (accessor was trivially exposable). **But** absent counts are silently defaulted to `0` — see G1 |
| D2 | Wire the reconcile into the project-local sync skill | reconcile runs from the meta-project sync surface only; absent/disabled build server = silent no-op | yes | yes | **partial** | yes | `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py` (378 lines); wired at `.claude/skills/sync-plugin-cache/SKILL.md:147` and `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md:154`; fail-open no-op proven by `test_invoke_executor_absent_executor_fails_open`, `test_not_enrolled_is_silent_noop_with_no_verb`. No shared-daemon behaviour changed (only an additive `ping` field). **But** a failed reconcile is reported as success — see G2, and the missing `upgrade` failure signal that makes G2 unfixable in isolation — see G7 |
| D3 | The deferral is observable, not silent | a deferral is readable after the fact without a raw log scan | yes | yes | **partial** | yes | `reconcile_daemon.py` `RECONCILE_MARKER_FILENAME`, `write_marker`, `marker_path()` → `$PLAN_MARSHALL_HOME/marshalld/reconcile-owed.json`; `defer_count` accumulation proven by `test_defer_count_increments_across_busy_syncs` (1,2,3, `since` pinned to T1, `runner.calls == []`). **But** the marker is cleared on an unverified reconcile — see G2 |
| D4 | `status` reports the RUNNING daemon's provenance; fail closed to `unknown` | a deliberately stale daemon makes `status` show the divergence | yes | yes | yes | **partial** | `manage_build_server.py::_read_process_argv`, `::_running_binary_path`, `run_status` → `running_binary_path` / `resolved_binary_path` / `binary_diverges` / `note`; `test_status_stale_daemon_shows_divergence`, `test_status_unknown_provenance_never_falls_back_to_resolved`. Mutation 2 → RED. **But** stale prose survives at three restatement sites — see G3, G4, G5 |
| D5 | A readiness probe reports an observation, not a guarantee; escalate once | one transition event replaces the repeat, init line no longer a whole-run contract | yes | yes | yes | yes | `phase-1-init/SKILL.md:962` rephrased ("observed at this init-time probe … NOT a whole-run guarantee"); `_build_execute_factory._update_fallback_streak` + `_record_resolution` emit one `ERROR` and suppress repeats, proven by `test_record_resolution_escalates_to_one_error_after_the_streak`. Upgraded from **partial** during adversarial review: the second emission site alleged by G6 does not repeat — `_route_to_daemon` preflights on every build and returns before `run_submit` (see the G6 refutation in `gaps.md`) |
| D6 | Tests, incl. BUSY-not-drained and provenance-unknown | all cases pass, with the BUSY and `unknown` cases present | yes | yes | yes | **partial** | 60 tests pass in the four primary files; both mandatory cases present and mutation-proven non-vacuous. **But** the missing-counts case has no test — see G1 |

**D1 — `manage_build_server.py:669` (`run_status`).** The contract's whole safety premise is
"idleness is read from the daemon's own scheduler count, never inferred from anything else"
(`report-01.md` § STOP CONDITION resolution). The code writes
`'in_flight': int(response.get('in_flight', 0) or 0)`, which cannot distinguish *"the daemon says
zero"* from *"the daemon did not answer that question"*. The population that cannot answer it is
exactly the population the reconcile targets: a **stale** daemon is by definition one executing a
marshalld copy that predates this commit, so its `Daemon._ping` returns only `status`/`pid`/`version`
(`manage_build_server._ping` performs no version gate — verified at
`manage_build_server.py:238-265`, no version check anywhere in the function). I executed the
consequence rather than reading it:

```
$ uv run python -c "... rd.decide({... 'binary_diverges': True, 'in_flight': 0, 'queued': 0 ...})"
old-daemon (counts defaulted to 0): ReconcileDecision(action='upgrade', reason='idle_and_stale')
```

`upgrade` is `run_drain` then `_start_daemon` (`manage_build_server.py:597-618`); `run_drain` SIGTERMs
and waits `_DRAIN_GRACE_SECONDS`, and an in-flight job is marked `killed` and replayed. That is the
outcome D1's stop condition exists to prevent, reached by the exact mechanism it forbids.

**D2/D3 — `reconcile_daemon.py:212-215` (`reconcile`).** On `UPGRADE`/`START` the orchestration records
`summary['reconcile_result'] = str(result.get('status', 'unknown'))` and then calls
`clear_marker(marker)` unconditionally. `run_upgrade` always returns `'status': 'success'` regardless
of whether the drain succeeded, and `_start_daemon` (`:495-524`) refuses to launch a second daemon when
one is still live, returning `already_running: True` — also `status: success`. So a drain that times
out at 30 s leaves the **old stale daemon running**, the reconcile reports `success`, and any
accumulated `reconcile-owed` marker is deleted. The drift becomes invisible again on the surface built
to make it visible.

**D4 — restatement completeness.** The divergence itself is correct and well-tested, but three places
still state the pre-D4 shape: the `status` sub-parser `help=` string
(`manage_build_server.py:872`, "Report running version + binary path."), the `_ping` docstring's
Returns block (`manage_build_server.py:249-250`, documenting the response as
`{'status','pid','version'}` after the counts were added), and the `marshall-steward` health-check
pointer (`marshall-steward/SKILL.md:262-264`, which relays only `running`/`version`/`registered`, so a
stale daemon still reads clean there).

**D5 — the escalation site is the only one that repeats.** The suppression is applied in
`_build_execute_factory._record_resolution`, which is the correct site for the flagship
`socket_absent` case: `run_preflight` (`build_server.py:572-605`) writes no log line, so the observed
repeats came from `_record_resolution` alone. This document originally also filed the client's own
`run_submit` / `run_wait` degradation WARNINGs (`build_server.py:440,450,461,472,522,531`) as an
unfolded second site. **That finding was refuted during adversarial review**: `_route_to_daemon`
(`_build_execute_factory.py:546-605`) calls `run_preflight` on *every* build and returns at `:571-573`
before `run_submit` is reached, so a sustained outage never re-enters the client's degraded paths, and
the `run_wait` loop returns on the first `degraded` result. The exposure is one WARNING on the single
transition build — not a repeat. Full evidence in `gaps.md` § Refuted.

## Report accuracy

Re-derived every stated figure and named symbol:

- **"67 tests"** — confirmed exactly (66 `def test_` + 1 parametrize expansion). Not an error.
- **"`test_fallback_escalation.py` (10)"** — confirmed, 10 `def test_`.
- **"`test_daemon_ping_counts.py` (2)"** — confirmed.
- **D1 claim confirmations** — all re-verified against the tree: `run_upgrade` = `run_drain` +
  `_start_daemon` ✓; `run_drain` is SIGTERM + `_DRAIN_GRACE_SECONDS`, never SIGKILL ✓;
  `Scheduler.running_count`/`queued_count`/`available_slots()` exist ✓; `_resolve_daemon_command` pins
  `Path(marshalld.__file__)` ✓.
- **"No undeclared collateral change: the `status` verb's old `binary_path` key was renamed …
  `run_start`/`run_install` keep their own `binary_path` … and the sole `status` consumer
  (`reconcile_daemon.py`) reads the new keys."** — the code half is correct: a tree-wide `binary_path`
  sweep leaves only `_resolve_daemon_command` (`:188-197`), `_start_daemon` — shared by `run_start`
  and `run_install` — (`:514-522`) and `run_upgrade` (`:616`), plus their tests. *(Attribution
  corrected during adversarial review: `:616` is inside `run_upgrade`, not `run_install`; see G7, where
  that key being `None` is the only accidental trace of a failed upgrade.)* **The claim is nevertheless incomplete as a completeness statement**: the sub-parser
  `help=` string at `:872` still names the removed key, and `marshall-steward/SKILL.md` is a second
  documented consumer of `status` (it names only still-valid keys, so nothing there is *wrong*, but it
  is not "the sole consumer").
- **F4 disposition ("additive and backward-compatible; the client handshake reads only
  `status`/`version`")** — confirmed for the *client*, but the disposition does not consider the
  reverse skew (a NEW client reading an OLD daemon's ping), which is where G1 lives. The statement is
  true as written and incomplete as a safety argument.
- **P1 disposition ("mirrors the canonical `marketplace_paths.home_root()` exactly")** — **not exact**.
  `reconcile_daemon._daemon_state_dir` uses `Path.home()`; `home_root()` uses `resolve_home()`, which
  catches the `RuntimeError` `Path.home()` raises in a `HOME`-less container
  (`marketplace_paths.py:39-55`). The consequence is benign — `marker_path()` is called inside
  `main()`'s blanket `except Exception` and degrades to `reconcile_error`, a fail-open no-op — so this
  is an imprecise sentence, not a defect. It does mean the reconcile marker and the D5 streak file can
  resolve to different roots in that one environment.
- **Build-gate figures** (`quality-gate` clean, 1851/13, 18817/14, CI green) — **not verifiable from
  the tree**; not re-run here (see below).

No other statement in `report-01.md` is contradicted by the tree.

## Out-of-scope compliance

The three declared out-of-scope items are all respected: no in-daemon `execv` self-reload exists
(`grep` for `execv` in `marshalld.py` finds nothing added), no general daemon-side liveness contract was
introduced, and no job-lifecycle audit observability was added.

Two files outside the literal Expected-surface list were written:

- `marshalld.py::Daemon._ping` (+15/−2) — a shared bundle. Report F4 dispositions this as authorized by
  D1's stop condition ("if trivially available, add a **read-only** accessor and say so"). I confirmed
  the change is purely additive: two new keys on the ping response, no behaviour change, and the
  build-server client's handshake reads only `status`/`version` (`build_server._handshake`). Compliant.
- `script-shared/scripts/build/_build_execute_factory.py` (+178/−4) — the fallback emission path. D5
  cannot be built anywhere else; the Expected-surface list simply did not enumerate it. Not a violation,
  but an undeclared surface the plan should have named.

The only other collateral is an `_isolate_home` autouse fixture added to
`test_acceptance_resolution_log.py` (+8), required because `_record_resolution` now writes streak state
to the machine-global home. Necessary and correctly scoped.

`_marshalld_scheduler.py` was declared read-only and was indeed not modified.

## Residue carried forward

| `report-01.md` residue | Still open today? |
|---|---|
| CLA signature (operator) | **Closed** — the PR merged as `8f3c7fe0` on `main`. |
| Reviewer re-coverage (`coderabbitai`, `sourcery-ai` rate-limited) | **Closed by landing** — the PR merged with the 1-of-3 disclosure; no re-review is recoverable now. |
| In-daemon self-reload / general daemon liveness contract / job-lifecycle audit observability, all deliberately out of scope | **Still open**, correctly — no code in the tree attempts any of them. |
| F2 (BUSY survival discharged structurally, not by a live-job snapshot) — accepted as adequate | **Still structural.** I agree with the disposition: `runner.calls == []` proves the reconcile's only daemon-affecting channel is never used, and `test_ping_reflects_running_and_queued_jobs` independently proves a real `Scheduler` with a running job yields `in_flight == 1`. Not raised as a gap. |
| F3 (`partial`-sync divergence) — fixed | **Confirmed fixed**: both SKILL.md files now say reconcile on `success` only. |
| P2 (non-atomic state write) — fixed | **Confirmed fixed**: `_write_fallback_state` and `write_marker` both use per-pid temp + `os.replace`. |

## What could NOT be verified

- **The build-gate numbers.** `./pw quality-gate` clean, "1851 passed, 13 skipped", "18817 passed,
  14 skipped", and the CI check names/conclusions on the PR head are historical facts about a run I
  cannot reproduce from this clone; the full suite was not re-run here (26.5 min claimed). I ran only
  the four test files this plan added/changed most heavily (60 passed).
- **The live-daemon end-to-end behaviour.** No marshalld daemon runs in this environment, so
  `_read_process_argv`'s `ps` fallback branch (non-`/proc` platforms), a real drain-then-start, and a
  real stale-daemon `status` were exercised only through fakes and the one `/proc/self` test.
- **The cold reads** the plan mandated (a reader shown the preflight line and the stale-`status`
  output with no other context). I read both with full context, which is not the same test; I can
  confirm the text *contains* the disclaimers, not that a cold reader parses them as intended.
- **The original incident logs** (`status` showing `0.1.1231` while `ps` showed `0.1.1212`, and the
  eighty-minute preflight run). The plan itself records these as unreachable from a clone.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked — by what means.**

*Files opened at HEAD:* `manage_build_server.py` (`_resolve_daemon_command`, `_ping`,
`_read_process_argv`, `_running_binary_path`, `_start_daemon`, `run_start`, `run_install`, `run_stop`,
`run_drain`, `run_upgrade`, `run_status`, `_build_arg_parser`, the `_UNKNOWN_PROVENANCE` /
`_DRAIN_GRACE_SECONDS` / `_STOP_GRACE_SECONDS` constants); `marshalld.py` (`Daemon._ping`) **and its
pre-image** via `git show 8f3c7fe0^:…/marshalld.py`; `reconcile_daemon.py` in full;
`_build_execute_factory.py` (`:186-410` streak block, `_route_to_daemon` `:546-605`, the wait loop);
`build_server.py` (`_audit_log`, `_degraded`, `run_submit`, `run_wait`, `run_preflight`);
`marketplace_paths.py` (`resolve_home` `:39-55`, `home_root` `:496-504`); `toon_parser._parse_value`;
`manage-build-server/SKILL.md`, `marshall-steward/SKILL.md`, `phase-1-init/SKILL.md` § Step 8e, both
sync `SKILL.md` files; `test_reconcile_daemon.py`, `test_manage_build_server.py`,
`test_daemon_ping_counts.py`, `test_fallback_escalation.py`.

*Commands run:* `git show --stat 8f3c7fe0` (15 files, +1598/−34 — figure confirmed); the corrected
supersession sweep over the complete `--name-only` file list (three commits, not two); three sweeps
run **broader** than the originals — `binary_path` across `*.py|*.md|*.json|*.toml` tree-wide rather
than the source tree alone, a preflight-wording sweep widened from `"no action required"` to
`no action required|Preflight ready|preflight.*ready|route to the daemon`, and a consumer sweep for
every spelling of `manage-build-server status`; `pytest` on the four primary files (**60 passed**,
re-derived); `pytest --collect-only` on all five files (**67 collected** — the report's figure
confirmed by collection, not only by hand-counting `def test_`).

*Functions executed (not read):* `reconcile_daemon.decide` on three hand-built status dicts including
one with `in_flight`/`queued` **absent**; `manage_build_server.run_status` with `_ping` stubbed to a
countless pre-`8f3c7fe0` response; `manage_build_server.run_upgrade` with `_running_pid → 9999` and
`_wait_for_exit → False` (the drain-timeout case); the real `manage_build_server status` verb through
`.plan/execute-script.py`; and `reconcile_daemon.py` end to end, which confirmed the TOON round-trip
parses `registered: false` as a real boolean (`toon_parser._parse_value` `:77-80`) rather than a
truthy string — a failure mode that would have made `binary_diverges` always-true and was checked
explicitly.

*Mutation applied:* a **third** guard neither original mutation covered — `decide`'s
`if running_binary in ('', 'unknown'):` fail-closed branch replaced with `if False:` →
`test_unknown_provenance_defers_never_drains` went **RED** (1 failed, 18 passed). Restored from a
byte-copy saved to the scratchpad before mutating; `md5sum` matched the pre-mutation file and
`git diff --quiet` returned 0. No `git checkout` / `restore` / `stash` was used. The file was verified
clean with `git diff --quiet` *before* mutating.

**Not re-checked.** The two mutations the original author ran (the BUSY guard, the D4 fail-closed
substitution) were **not** re-applied — a third guard was mutated instead, so those two remain
single-sourced. Also not re-checked: the build-gate numbers and CI conclusions (unreproducible from
this clone, as already recorded below); live-daemon end-to-end behaviour; the cold reads the plan
mandated; the original incident logs; `_marshalld_scheduler.py` beyond confirming
`running_count`/`queued_count` exist; and the D1 contract table in `report-01.md` was read for its
claims, not audited clause by clause.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | absent ping counts default to `0`, so a busy stale daemon is reconciled as idle — `high` | **upheld, rationale narrowed** | Re-executed end to end: `run_status` with a countless `_ping` returns `in_flight: 0, queued: 0, binary_diverges: True`; `decide` on that exact dict returns `upgrade/idle_and_stale`. Pre-image confirmed at `git show 8f3c7fe0^`. But "the daemons that carry no count are **exactly** the ones this feature targets" over-claims — only stale daemons pinned *below* the counts extension omit them. Clause rewritten; severity `high` stands (a guard that passes against the defect it names) |
| G2 | reconcile reports `success` and clears the owed marker without verifying — `medium` | **upheld, Fix rewritten** | Defect real (`reconcile_daemon.py:210-215`). The **Fix was unactionable**: executed `run_upgrade` on the drain-timeout case returns `{'drained': True, 'running': True}`, so both proposed criteria (`drained == False`, `running == False`) are inert, and the Done-when's fixture describes a state the verb never produces. Rewritten and made dependent on new G7 |
| G3 | `status` sub-parser `help=` still names the removed `binary_path` key — `medium` | **upheld** | `manage_build_server.py:872` reads `help='Report running version + binary path.'`; a tree-wide `binary_path` sweep confirms the key is gone from `run_status`; the proposed replacement matches `manage-build-server/SKILL.md:177` verbatim. Done-when (a grep returning nothing) is observable |
| G4 | `_ping` docstring's Returns block omits `in_flight`/`queued` — `low` | **upheld** | `manage_build_server.py:250-251` documents `{'status','pid','version'}`; `marshalld.Daemon._ping:313-317` returns five keys. Severity `low` correct — no behaviour depends on it |
| G5 | steward health-check pointer relays `running`/`version`/`registered` only — `medium` | **upheld** | `marshall-steward/SKILL.md:260-268`; the file was **not** touched by `8f3c7fe0` (`git show --stat`), so the omission is real and unswept. Done-when observable |
| G6 | client `run_submit`/`run_wait` WARNINGs repeat per build outside the D5 streak — `low` | **refuted** | `_route_to_daemon` preflights on every build and returns at `:571-573` before `run_submit`; the `run_wait` loop returns on the first `degraded`. Maximum exposure is one WARNING on the transition build. Moved to `gaps.md` § Refuted with the residual narrow path recorded |
| **G7** *(new)* | — | **added, `medium`** | `run_upgrade` (`:597-618`) discards `run_drain`'s `exited` and `_start_daemon`'s `already_running`, so its return cannot express a failed upgrade. Proven by execution. Blocks G2 |
| D5 row | `Complete? partial` on the strength of G6 | **re-graded to `yes`** | G6 refuted; no second repeating emission site exists |
| "67 tests" | report figure | **upheld** | `pytest --collect-only` on the five files → 67 collected |
| supersession sweep | "only `d4ae2e81` and `6514cf24`" | **corrected** | Three commits: `9135f275` (#1287, `phase-1-init/SKILL.md`) was missed. Its diff is the `session_id` → `session_ids` rename and does not touch D5's line `:962`; the conclusion is unchanged |
| `binary_path` sweep | "leaves only `_resolve_daemon_command`/`run_start`/`run_install` (`:188-197, 514-522, 616`)" | **corrected** | Re-run tree-wide across `.py/.md/.json/.toml`: same set, but `:616` is `run_upgrade`, not `run_install` |
| P1 (`Path.home()` vs `resolve_home()`) | "not exact, benign" | **upheld** | `marketplace_paths.resolve_home:39-55` catches the `RuntimeError`; `reconcile_daemon._daemon_state_dir:133` calls `Path.home()` directly |
| Out-of-scope compliance | all three respected | **upheld** | No `execv` anywhere in `marshalld.py`; no daemon-side liveness contract; no job-lifecycle audit surface added |
| Verdict | `implemented-with-gaps` | **upheld** | All six deliverables are implemented and documented; none is missing, so `partially-implemented` would be wrong. The open gaps are correctness/completeness holes inside shipped deliverables |

**Documents corrected.** In `gaps.md`: G1's mechanism clause narrowed to the population that actually
omits the counts and its evidence replaced with a re-execution (the original cited a dict with the
counts *present as zero*, which does not exercise the absent-key path); G2's Fix and Done-when
rewritten after executing `run_upgrade` and finding both proposed failure criteria inert, with the
superseded text retained as a dated correction note; G6 refuted and moved to a new
`## Refuted during adversarial review` section carrying both the refutation and the one narrow
residual path it does not cover; **G7 added** for `run_upgrade`'s missing failure signal; the header
re-derived (still 6 open — one refuted, one added). In `verification.md`: the supersession enumeration
corrected from two commits to three; the `binary_path` sweep attribution corrected (`:616` is
`run_upgrade`); the D5 row re-graded from `partial` to `yes` and its narrative paragraph rewritten
around the refutation; the D2 row now points at G7.

**Residual doubt — what a third reviewer should look at first.**

1. **Whether `binary_diverges` can ever be `true` in the meta-project.** In this clone the real
   `status` verb returns `resolved_binary_path:
   /home/user/plan-marshall/marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py`
   — the repository source tree, not a versioned plugin-cache path. `_resolve_daemon_command` pins
   `Path(marshalld.__file__)`, so if the developer machine's generated executor also maps
   `manage-build-server` to the repo source, the resolved path never changes on a cache bump and the
   reconcile never fires in the very repository it was built for. The plan's own incident report
   (`0.1.1231` vs `0.1.1212`) implies cache paths there, so the two observations disagree. This is
   environment state that no clone can settle; it should be checked on the machine that saw the drift,
   because if it holds, Group A is inert where it matters and no test in the suite would notice.
2. **The two mutations this review did not re-run** (the BUSY guard and the D4 fail-closed
   substitution). Both are still attested by a single agent.
3. **Whether G2/G7 should be one finding or two.** They are split here because the missing signal is a
   defect in a shared operator verb independent of the project-local reconcile — any caller of
   `upgrade` is misled — but a reader who regards the reconcile as the only consumer would merge them.
4. **`reconcile()`'s `not_registered` no-op clears an owed marker** (`:238-241`) while
   `status_unavailable` deliberately preserves it. `registered` is also `False` when
   `main_checkout_root()` raises, and the marker is machine-global while registration is per-repo — so
   an indeterminate registration read can discard genuine accumulated `defer_count` evidence. Judged
   too thin to file (no path to it was demonstrated), but it is the next place the G2 failure mode
   would reappear.
