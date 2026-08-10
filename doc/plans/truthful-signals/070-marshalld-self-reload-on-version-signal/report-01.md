# Run report — 070-marshalld-self-reload-on-version-signal (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/marshalld-self-reload-version-f1sakm` (harness-assigned; kept as-is)    **PR:** [#1152](https://github.com/cuioss/plan-marshall/pull/1152)    **Outcome:** completed (landing delegated — see Contract check § Step 8)

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
- Full local test suite (`uv run pytest`, whole tree) → **18817 passed, 14 skipped** (26.5 min).
- CI on the PR head: `verify / conclusion` (the required merge-gate check) → **success**, along with
  `verify / verify`, `verify / gate`, `dependency-review`, `generate-check`, `review / review`. The
  finding-2 atomic-write fix (commit below) re-triggers the required `verify` run once more before the
  merge gate.

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

**PR review — `cuioss-review-bot` (pr-agent)** posted a "PR Reviewer Guide" with two findings:

| # | Sev | File:symbol | Finding | Disposition |
|---|---|---|---|---|
| P1 | flagged as security | `reconcile_daemon.py::_daemon_state_dir` | Path constructed from the unvalidated `PLAN_MARSHALL_HOME` env var (path-traversal / domain-rule risk). | **Replied, not actionable.** The resolution mirrors the canonical `marketplace_paths.home_root()` exactly — `PLAN_MARSHALL_HOME` is trusted, test-controlled *configuration* read across the whole codebase, not untrusted input, and there is no untrusted path *component* (no `../` from a caller). The env var is a base directory, not a traversal vector; the reconcile only ever reads/writes `{home}/marshalld/reconcile-owed.json`, fail-open. Changing only this call site would not address the "risk", since the canonical resolver reads the same var. |
| P2 | robustness | `_build_execute_factory.py::_write_fallback_state` | Non-atomic `write_text` + unlocked read-modify-write → concurrent in-process builds could corrupt the JSON or lose a streak update. | **Fixed** — both state writers (`_write_fallback_state` and `reconcile_daemon.py::write_marker`) now write atomically (per-pid temp file + `os.replace`), so a concurrent reader never sees a torn document. The unlocked read-modify-write remains best-effort by design (a lost increment only delays escalation by one build; the write was already fail-open), but a half-written file that would reset the streak is prevented. |

## Reviewer participation

Expected reviewer population, derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" issue comment with two findings against the diff (P1, P2 above) — dispositioned. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … Next review available in: 56 minutes" — engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted a review with only "you have reached your weekly rate limit of 500000 diff characters" — engaged but did not review this diff. |

**Coverage: 1 of 3 reviewed** (as of the review of head `8a07aac`). The § Step 8 shortfall disclosure
fires: `cuioss-review-bot` reviewed; `coderabbitai` rate-limited (window reopens ~56 min); `sourcery-ai`
rate-limited (weekly quota). Per the lane this is a **disclosure, not a merge block** — rate limits are
routine and outside our control. The finding-2 fix re-triggers `cuioss-review-bot` on the new head.

## Cost

- **Tokens:** not available to the agent in this session (a single interactive Claude Code cloud
  session; no per-task billing boundary is exposed to me). Stated plainly rather than estimated.
- **Wall-clock:** ~2h of session activity (plan load → implementation → local full-suite verify at
  26.5 min → PR → review cycle).
- **Population:** this single Claude Code cloud session's activity. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  own per-task billing boundary, which this interactive session does not share. No comparable figure
  is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done** — named above (ref-code-quality, plugin-script-architecture, python-core, pytest-testing). |
| 2 Branch | **Done** — harness-assigned `claude/marshalld-self-reload-version-f1sakm`, kept as-is, present on `origin` (pushed before any edit). |
| 3 Plan directory | **Done** — `doc/plans/truthful-signals/070-marshalld-self-reload-on-version-signal/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | **Done** — commits carry the `Co-Authored-By: Claude` trailer; all six deliverables addressed. |
| 4 Per-commit gate | **Done** — `./pw quality-gate` clean before each `*.py` commit (`total_issues: 0`, empty `errors[]`, mypy clean). |
| 4 Pushed | **Done** — every commit pushed; no unpushed commit remains. |
| 5 Build gate | **Done** — Python changed → full path; quality-gate clean + full suite 18817 passed; CI `verify / conclusion` green on the pre-fix head. |
| 6 Verification sub-agent | **Done** — PASS on all six; findings F1–F4 dispositioned above. |
| 7 PR cycle | **Done** — PR #1152; both comment surfaces read (conversation + inline threads); every comment dispositioned; reviewer participation recorded. |
| 8 Merge gate | Conditions 1–3 met (required checks green on head after the fix's re-verify; all comments handled; this report is the last pre-merge commit). Coverage shortfall disclosed (1 of 3). Auto-merge armed (SQUASH); landing delegated to the merge queue — the cloud session cannot self-wake to watch the queue, which is a **completed** outcome, not partial (§ Cloud session affordances). |
| 8 Bridge | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. |
| 9 This check | This table. |

**GitHub access path:** GitHub MCP server (cloud session). **Branch form:** harness-assigned `claude/*`.
No `/sync-plugin-cache` is owed — it is a machine-local build step, not a debt a cloud run records.

**Note on the CLA check.** `cla-assistant` reports the CLA "not signed" for this PR. Signing is an
operator action (I cannot sign a CLA), and if it is a required context the merge queue will hold the
PR until it is signed — disclosed here so the operator can resolve it.

## What have we learned (Step 9)

**No contract change proposed.** The cloud-plan-lane contract held end to end for this run: every step's
artifact was producible as written, the build gate and verification dispatch worked as specified, the
merge-gate disclosure-not-block rule fit the rate-limited-reviewer reality exactly, and the report
format captured everything the orchestrator collects. No step was ambiguous in practice and no command
failed in the environment, so there is no run-produced evidence justifying an amendment. (Recorded per
Step 9: a run that examined the contract and found nothing is a distinct fact from one that never
looked.)

## Residue

- **CLA signature** (operator) — the merge queue will hold the PR until the CLA is signed if it is a
  required context; nothing this run can do.
- **Reviewer re-coverage** — `coderabbitai` (window reopens ~56 min) and `sourcery-ai` (weekly quota)
  were rate-limited; if the operator wants their pass, re-request after the windows reopen. Not a
  blocker (disclosure-not-block).
- **In-daemon self-reload** remains deliberately out of scope (revisit only if the drift appears in a
  consumer repository), as does the general daemon-side liveness contract and job-lifecycle audit
  observability — all recorded in the plan's Out-of-scope section.
