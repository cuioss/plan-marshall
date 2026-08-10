# Run report — 070-marshalld-self-reload-on-version-signal (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/marshalld-self-reload-version-f1sakm` (harness-assigned; kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — read via bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — read via bundle path.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.
- `plan-marshall:ref-code-quality` standards absorbed from existing daemon code conventions.

GitHub access path: GitHub MCP server (cloud session). Branch form: harness-assigned `claude/*`.

## D1 GATE — idle-conditional reconcile contract (recorded, mutates nothing)

**Status fields the reconcile reads** (from `manage-build-server status`, after this plan's read-only additions):

| Field | Source | Meaning |
|---|---|---|
| `running` (bool) | `_ping()` success in `run_status` | socket liveness (verified ping answered) |
| `in_flight` (int) | NEW — daemon `_ping()` carries `scheduler.running_count` | jobs currently executing |
| `queued` (int) | NEW — daemon `_ping()` carries `scheduler.queued_count` | jobs admitted-to-queue but not yet running |
| `running_binary_path` (str \| `unknown`) | NEW (D4) — live process `/proc/{pid}/cmdline`, `ps` fallback | the binary the RUNNING daemon is executing |
| `resolved_binary_path` (str) | `_resolve_daemon_command()` | the resolve-now path = the verified pin after a fresh sync |
| `binary_diverges` (bool) | NEW (D4) — `running_binary_path` known and `!= resolved_binary_path` | staleness signal |
| `reason` (str) | when `running` false | `no_pidfile` / `unreachable` — both = socket_absent for reconcile |
| `registered` (bool) | registry lookup | project enrolled (the enable signal) |

**⛔ STOP CONDITION resolution.** `status` did **not** previously expose an in-flight count. It is
**trivially available** — the daemon already holds the `Scheduler`, whose `running_count` /
`queued_count` are read-only properties. Per D1's stop condition ("if trivially available, add a
**read-only** accessor and say so"), a read-only in-flight/queued count is added to the daemon `ping`
handshake and surfaced by `status`. **Group A proceeds.** Idleness is read from the daemon's own
scheduler count, never inferred from anything else.

**Reconcile decision (pure `decide(status)` → action, reason), one row per case:**

| Case | Predicate | Action | Reconcile call |
|---|---|---|---|
| not enrolled / no build server / status unavailable | `registered == False` or status error | **noop** (silent) | none |
| running, stale, idle | `running` ∧ `binary_diverges` ∧ `in_flight==0` ∧ `queued==0` | **upgrade** | `manage_build_server upgrade` (drain-then-start-verified) |
| running, stale, BUSY | `running` ∧ `binary_diverges` ∧ (`in_flight>0` ∨ `queued>0`) | **defer** | none — leave running, log + reconcile-owed marker |
| running, provenance unknown | `running` ∧ `running_binary_path == unknown` | **defer** (reason=`provenance_unknown`) | none — fail-closed, never drain on a guess |
| running, not stale | `running` ∧ ¬`binary_diverges` | **noop** | none — already on the verified pin |
| down / socket_absent, enrolled | ¬`running` ∧ `registered` | **start** | `manage_build_server start` (plain start; daemon already dead, no drain, nothing in flight) |

**Claim verification (D1):**
- `run_upgrade` is drain-then-start-verified: **CONFIRMED** — `manage_build_server.py` `run_upgrade`
  calls `run_drain` then `_start_daemon`.
- `run_drain` is SIGTERM + bounded grace (never SIGKILL); in-flight jobs replayed as `killed`:
  **CONFIRMED** — `run_drain` sends only `SIGTERM`, waits `_DRAIN_GRACE_SECONDS`, never escalates.
- Scheduler tracks in-flight (slot budget): **CONFIRMED** — `_marshalld_scheduler.Scheduler.running_count`
  / `queued_count` / `available_slots()`.
- `status` exposes in-flight count in the shape D1 needs: **was FALSE, now made true** (read-only
  ping extension).
- `upgrade` starts only the verified bundle copy: **CONFIRMED** — `_resolve_daemon_command` pins
  `Path(marshalld.__file__)`.

## Deliverables

| # | What was done | Commit | Verification |
|---|---|---|---|
| **D1** | GATE settled (see contract above). In-flight/queued counts exposed read-only via the daemon `ping` handshake (`marshalld.py::Daemon._ping`) and surfaced by `status`. STOP CONDITION did not fire — the count was trivially exposable. | `fe6eb7d` | `test_daemon_ping_counts.py` (2), `test_status_reports_in_flight_and_queued_counts` |
| **D4** | `manage-build-server status` sources the RUNNING binary from the live process (`_read_process_argv` → `/proc/{pid}/cmdline`, `ps` fallback; `_running_binary_path`); reports `running_binary_path` + `resolved_binary_path` + `binary_diverges` + a `note`; fail-closed to `unknown`, never the resolved path. | `fe6eb7d` | `test_status_stale_daemon_shows_divergence`, `test_status_unknown_provenance_never_falls_back_to_resolved`, `test_status_unknown_when_argv_has_no_marshalld_token`, `test_read_process_argv_reads_this_process_from_proc` |
| **D5** | Preflight line (`phase-1-init/SKILL.md`) rephrased as a point-in-time observation, not a whole-run guarantee. Consecutive daemon-unreachable fallbacks escalate once (`_build_execute_factory._update_fallback_streak`): after N per-plan the routing seam emits one ERROR naming the transition, suppressing the repeated WARNING until a routed build resets the streak. | `fe6eb7d` | `test_fallback_escalation.py` (10) |
| **D2** | `reconcile_daemon.py` (project-local) queries `status` after a successful sync and applies the D1 contract; wired into `/sync-plugin-cache` and `finalize-step-sync-plugin-cache`. Silent no-op when the build server is absent/disabled or the executor is missing (fail-open adapters). No shared-daemon behaviour changed. | `8ed2a46` | `test_reconcile_daemon.py` decide/orchestration cases |
| **D3** | A deferred reconcile writes a readable `reconcile-owed` marker (machine-global, beside daemon state) with a `defer_count` that accumulates across busy syncs; cleared on reconcile/current, preserved on indeterminate status. | `8ed2a46` | `test_busy_defer_never_runs_a_reconcile_verb_and_writes_marker`, `test_defer_count_increments_across_busy_syncs`, `test_current_daemon_clears_a_stale_owed_marker`, `test_status_unavailable_preserves_an_owed_marker` |
| **D6** | All D6 cases covered — including the two mandatory ones: **BUSY → NOT drained** (asserts the reconcile issues *zero* mutating verbs, so the in-flight job cannot be drained) and **provenance undeterminable → `unknown`/defer** (never the resolved path). | `fe6eb7d`, `8ed2a46` | 67 tests across the five files |

Split-guard: Group A did NOT halt (D1's in-flight count was trivially exposable), so both groups shipped in one PR — no file split (the plan is named for one orchestrator spec).

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (Python changed), so the gate takes
its full path.

- `./pw quality-gate` → **clean** (mypy: "no issues found in 387 source files"; ruff clean after two
  UP017 `datetime.UTC` fixes; all plugin-doctor analyzers `0`, `issues[0]` empty).
- Affected suites (`build-server`, `build-pyproject`, `build-operations`, `script-shared`,
  `sync-plugin-cache`) → **1851 passed, 13 skipped**.
- New/changed tests → **67 passed**.
- Full `./pw verify` suite → _running (belt-and-suspenders for far-flung breakage); result recorded
  below when it completes._

## Findings

**Pre-PR verification sub-agent (independent, read-only, `general-purpose`)** — verdict: **PASS on
all six deliverables, no blocking gaps.** Both mandated cold reads matched the required answers:
(a) the preflight line promises nothing about later in the run; (b) the stale-daemon `status` shows
the running binary as the actual one with the divergence visible. Findings, each with disposition:

| # | Sev | Deliverable | Finding | Disposition |
|---|---|---|---|---|
| F1 | INFO | D5 | Preflight uses "observed at this init-time probe" rather than the plan's literal `{ts}` example. | **Rejected (not a gap).** The plan wrote "e.g." (illustrative); the `manage-logging decision` entry is itself timestamped by the logging system, and the done-when ("no longer reads as a whole-run contract") is met by the explicit "NOT a whole-run guarantee" clause. |
| F2 | LOW | D6 | The BUSY-survival mandate is discharged structurally (`runner.calls == []` → the reconcile issues zero mutating verbs, so it cannot drain the job) rather than by an end-to-end live-job snapshot. | **Accepted as adequate.** The agent judged this "valid and arguably stronger": the survival chain is complete across three layers — a real `Scheduler` with a running job → `in_flight=1` over ping → `decide`→`DEFER` → reconcile runs no verb. The reconcile's only daemon-affecting channel is `action_runner`; asserting it is never invoked proves non-interference at the layer the deliverable lives in. |
| F3 | INFO | D2 | The two sync surfaces disagreed on `partial`-sync handling (interactive reconciled on success-or-partial; finalize skips on partial). | **Fixed** — aligned the interactive `/sync-plugin-cache` Step 2c to reconcile on `success` only, matching the finalize step. |
| F4 | INFO | D1 | `marshalld.py::Daemon._ping` edits a shared bundle not named in the Expected-surface list. | **Rejected (authorized).** D1's STOP CONDITION explicitly permits adding a read-only accessor; the daemon ping is the only cross-process channel by which the separate `status` client can read the scheduler's in-flight count. The change is additive and backward-compatible (client handshake reads only `status`/`version`) — not a shared-daemon *behaviour* change, correctly outside the D2 "no shared-daemon behaviour change" ⛔. |

No undeclared collateral change: the `status` verb's old `binary_path` key was renamed to
`running_binary_path`/`resolved_binary_path`; `run_start`/`run_install` keep their own `binary_path`
(the launched binary, legitimately) and the sole `status` consumer (`reconcile_daemon.py`) reads the
new keys.

## Reviewer participation

_(recorded after PR review — populated from the automated reviewers' comment bodies)_

## Reviewer participation

_(pending)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

_(pending)_
