# History: Plan-Server (marshalld) build-server — CLOSED 2026-07-22

slug: plan-server
final phase: closed
closed: 2026-07-22 (definitive close; supersedes the 2026-07-18 first close that was reopened 07-19)
workstreams: WS-01 (build-server) — complete
plans: 6 shipped, 0 parked, 0 dropped

> Frozen record of the closed epic. The live tree (`epic.md`, `status.json`, `plans/`, `landings/`,
> `logs/`) remains on disk as the audit record — close freezes, never deletes. Unresolved leads were
> carried to the successor epic `truthful-signals` (see Carried Forward).

## Vision as pursued

Move ownership of expensive long-running work (builds, tests) out of the harness-reaped Claude
session into a machine-level owner — an opt-in Python asyncio daemon (`marshalld`) that supervises
builds as its own PID-1-reparented process, so a killed session-side `wait` re-polls a surviving job
instead of destroying real work, and one machine-global build queue coordinates otherwise-uncoordinated
concurrent builds. Scope was strictly a build server (a job belongs in marshalld IFF killing its waiter
destroys local work OR it contends for local CPU; CI-waits stayed on bounded `ci:wait` primitives).

**"Done" was reached and then exceeded:** Rung 2 shipped (registration-as-enable-signal, bounded
long-poll client, verify-not-resolve submit security, WSL2 Windows support, as-built docs), and the
epic went on to close a chain of post-ship defects — culminating in the core work-preservation thesis
being *realized* for this repo (pyproject builds now route to the daemon; `resolved=routed` confirmed
live) and the routed-build verdict made truthful.

## Queue outcome — all 6 plans shipped

| Plan | PR | Landing | Outcome |
|------|----|---------|---------|
| PLAN-01 plan-server-core | #933 | landings/PLAN-01.md | Rung 2 daemon + client skill + machine-global queue; +unplanned S2 cwd-escape fix. |
| PLAN-02 registration-scope-population | #941 | landings/PLAN-02.md | register populates `notation_allowlist`+`worktree_containers`; re-register = idempotent repair. |
| PLAN-03 interaction-audit-logging | #949 | landings/PLAN-03.md | central `interaction-audit.log`, `logs` verb, client↔server↔ledger job_id correlation, captured-level fallback logging. |
| PLAN-04 explicit-execution-mode | #956 | landings/PLAN-04.md | `execution_mode = auto\|in_process\|daemon` on the routing seam; hermetic `in_process` tests resolved the 8-spurious-failures defect. |
| PLAN-05 client-resolution-log-capture | #971 | landings/PLAN-05.md | `_record_resolution()` dual-emit (captured `plan_logging` + stderr) for the client routing-resolution line; +`in_daemon_child` double-line fix. Landing found the pyproject-routing-bypass root cause. |
| PLAN-06 pyproject-routing-integration | #979 | landings/PLAN-06.md | pyproject rides the shared factory routing `cmd_run` via additive `wrap_execute_fn` — **thesis realized, `resolved=routed` live**; +mid-execute D4: `_marshalld_supervisor.py` false-green fix (exit 0 necessary-but-not-sufficient; job-log verdict must agree). |

## Decision record (condensed)

Full entries live in `epic.md` § Decisions and `logs/decision.log`. Highlights:
- Rung 1 (#923) + Rung 2 (#933) shipped; the setsid/double-fork gate passed with the hard constraint
  that the server launches via full double-fork daemonization.
- Registration IS the single enable signal (no config knob); verify-not-resolve submit security model;
  WSL2-only Windows support.
- 07-18 first close after Rung 2; 07-19 REOPENED (marshalld registered but inert — empty scope) → PLAN-02.
- 07-22: PLAN-05 landing established the verified root cause of the epic's routing mystery — the
  pyproject adapter discarded the factory routing handler → PLAN-06 (operator-directed).
- 07-22: PLAN-06 realized the thesis and, mid-execute, fixed the routed-build false-green (D4).
- #909 never-timeout-shaped contract HOISTED (scoped): terminal-status-correctness → shared build
  layer; bound-expiry running-liveness → daemon-local. (Relay to plan-optimization carried forward.)

## Carried Forward → successor epic `truthful-signals`

These unresolved leads were migrated (not dropped) into `truthful-signals` (build/status verdict
integrity), whose flagship theme — a confident signal that hides the caveat making it wrong — is
their natural home:

1. **Client-side routed-verdict cross-check** → `truthful-signals` **PLAN-45** (staged).
   `_daemon_result_to_direct` (`_build_execute_factory.py:220`) trusts the daemon's `job_status`
   verbatim = single point of truth. The daemon-side false-green was fixed by PLAN-06 D4 (#979); PLAN-45
   adds the client backstop (fail-closed cross-check + `errors[]` fidelity + both-modes regression test).
2. **⚠ URGENT operational advisory — daemon restart owed.** The machine-global marshalld daemon must be
   RESTARTED against v0.1.1190 for the PLAN-06 D4 false-green fix to take effect. Until then, routed
   builds can still report a false green (two live API-Sheriff false-greens already observed, incl. a
   662s-timeout integration run with zero tests that read as success). One restart fixes all consumers;
   until then read job logs, not outer build status. Carried as a `truthful-signals` advisory.
3. **#909 relay to plan-optimization** — report the settled hoist decision so PLAN-32 D3 can be designed,
   noting PLAN-06 D4 already narrowed the daemon-local verdict; first check whether merged #972
   (attach-test-evidence-to-timeout-killed-status) discharged the terminal-status-correctness half.
4. Already represented in `truthful-signals`: the false-green routed-build is its flagship watch (n=4);
   the orchestrator queue-verb pr/landing tooling gap is its candidate (d).

Out-of-epic operator housekeeping (not epic work, not migrated): `marshal.json` stale
(`/marshall-steward` + restart); stale worktree `worktrees/metrics-corpus-integrity/`.

## Closing rationale

Every chartered deliverable plus every discovered follow-up shipped; the core work-preservation thesis
is realized and verified live. The remaining items are a defense-in-depth hardening and two advisories
that are better tracked in the successor `truthful-signals` epic, which owns the build/status-truthfulness
theme across both execution paths. Migrating them there and closing keeps a single live home for the
theme rather than a second standing-open epic. Closed at operator direction 2026-07-22.
