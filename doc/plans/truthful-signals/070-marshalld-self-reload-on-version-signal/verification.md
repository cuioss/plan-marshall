# Verification — 070-marshalld-self-reload-on-version-signal

**Verified against:** commit `ac06e4fc`   **Landed as:** PR #1152, commit `8f3c7fe0`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding is distinguishable from an unexamined one:

- Read `plan.md` and `report-01.md` in full; extracted all six deliverables with their *Done when*
  conditions, the Out-of-scope list, the Expected surface, the Claim-labels table and the Verification
  section.
- Located the landed commit with `git log --oneline --all --grep '#1152'` → `8f3c7fe0`
  (15 files, +1598/−34). Read the full diff of every production file it touched.
- Checked for later supersession with `git log --oneline 8f3c7fe0..HEAD -- <each touched file>`:
  only `d4ae2e81` (#1193) and `6514cf24` (#1290) touched them; neither reverts this plan's surface.
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
| D2 | Wire the reconcile into the project-local sync skill | reconcile runs from the meta-project sync surface only; absent/disabled build server = silent no-op | yes | yes | **partial** | yes | `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py` (378 lines); wired at `.claude/skills/sync-plugin-cache/SKILL.md:147` and `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md:154`; fail-open no-op proven by `test_invoke_executor_absent_executor_fails_open`, `test_not_enrolled_is_silent_noop_with_no_verb`. No shared-daemon behaviour changed (only an additive `ping` field). **But** a failed reconcile is reported as success — see G2 |
| D3 | The deferral is observable, not silent | a deferral is readable after the fact without a raw log scan | yes | yes | **partial** | yes | `reconcile_daemon.py` `RECONCILE_MARKER_FILENAME`, `write_marker`, `marker_path()` → `$PLAN_MARSHALL_HOME/marshalld/reconcile-owed.json`; `defer_count` accumulation proven by `test_defer_count_increments_across_busy_syncs` (1,2,3, `since` pinned to T1, `runner.calls == []`). **But** the marker is cleared on an unverified reconcile — see G2 |
| D4 | `status` reports the RUNNING daemon's provenance; fail closed to `unknown` | a deliberately stale daemon makes `status` show the divergence | yes | yes | yes | **partial** | `manage_build_server.py::_read_process_argv`, `::_running_binary_path`, `run_status` → `running_binary_path` / `resolved_binary_path` / `binary_diverges` / `note`; `test_status_stale_daemon_shows_divergence`, `test_status_unknown_provenance_never_falls_back_to_resolved`. Mutation 2 → RED. **But** stale prose survives at three restatement sites — see G3, G4, G5 |
| D5 | A readiness probe reports an observation, not a guarantee; escalate once | one transition event replaces the repeat, init line no longer a whole-run contract | yes | yes | yes | **partial** | `phase-1-init/SKILL.md:962` rephrased ("observed at this init-time probe … NOT a whole-run guarantee"); `_build_execute_factory._update_fallback_streak` + `_record_resolution` emit one `ERROR` and suppress repeats, proven by `test_record_resolution_escalates_to_one_error_after_the_streak`. **But** the client's own duplicate WARNING path is not folded — see G6 |
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

**D5 — one escalation site of two.** The suppression is applied in
`_build_execute_factory._record_resolution`, which is the correct site for the flagship
`socket_absent` case: `run_preflight` (`build_server.py:572-605`) writes no log line, so the observed
repeats came from `_record_resolution` alone. However when the daemon answers preflight and then dies,
`run_submit`/`run_wait` (`build_server.py:441,451,462,473,522,532`) each `_audit_log(..., 'WARNING',
'build-server {submit,wait} degraded: reason=unreachable …')` per build, and those are not folded by
the streak.

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
  sweep leaves only `_resolve_daemon_command`/`run_start`/`run_install` (`:188-197, 514-522, 616`) and
  their tests. **The claim is nevertheless incomplete as a completeness statement**: the sub-parser
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
