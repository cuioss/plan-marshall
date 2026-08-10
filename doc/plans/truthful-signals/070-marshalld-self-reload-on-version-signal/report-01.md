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

_(updated as implemented)_

## Build gate

_(pending)_

## Findings

_(pending)_

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
