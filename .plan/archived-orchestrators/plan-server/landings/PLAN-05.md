# Landing Analysis: PLAN-05 — Capture the client build-routing resolution/fallback log

epic: plan-server
workstream: WS-01
pr: #971 — https://github.com/cuioss/plan-marshall/pull/971 (merged 2026-07-22, squash via merge queue, `5caf22e3c` on origin/main)

> Landing record for one shipped plan. Claims below verified against ground truth
> (merged diff `5caf22e3c`, the live `_build_execute_factory.py` / `_pyproject_execute.py`
> / `_maven_execute.py` source, PR state via the CI abstraction) — not the paste.

## Deliverable Fidelity vs Spec

The spec listed 3 deliverables (capture + regression tests + doc note); the landing reports
"2 deliverables" because D1 (capture) and D2 (tests) were shipped as one code deliverable and
D3 (doc) as the other — same surface, no scope drop.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — capture the three client resolution lines to a durable sink | shipped-as-specified | `_build_execute_factory.py` diff: new `_record_resolution()` helper (L165) dual-emits `print(msg, file=sys.stderr)` (unconditional, `[EXEC]` parity) + `log_entry('work', plan_id, level, msg)` when `plan_id` set; `level = WARNING if resolved=='fail-loud' or reason is not None else INFO`. All three `logger.info` call sites migrated (fail-loud L350, routed L614, in_process L646). Rides PLAN-03's existing `plan_logging.log_entry` seam (`build_server._audit_log` wrapper) — no new handler/basicConfig, so the PLAN-32 coordination constraint was discharged by construction, verified: no second logging-config mechanism in the diff. |
| D2 — regression tests, all three paths | shipped-as-specified (+expanded) | New `test/plan-marshall/build-server/test_acceptance_resolution_log.py` (+242) asserting routed / in-process-with-named-fallback / daemon fail-loud emit to the captured sink; plus plan-less and daemon-child cases. `test_build_execute_routing.py` updated (±26). Asserts at the seam so a regression to bare `logger.info` fails the suite. |
| D3 — doc note (fold, not split) | shipped-as-specified | `build-server-client/SKILL.md` (+7) cross-referencing where the client resolution log lands; cross-reference, not duplication. |
| in_daemon_child re-entrancy guard | added-unplanned (loop-back fix) | CodeRabbit caught a real defect in this plan's OWN new code: the `MARSHALLD_JOB` daemon-child re-entrancy path emitted `resolved=in_process` while the routing PARENT emitted `resolved=routed` — two contradictory lines per routed request, directly undermining the plan goal. Fix verified in-tree: `in_daemon_child` flag (L588) set when `reason == 'in_daemon_job'`, suppresses the child's own `_record_resolution` (L645 `if not in_daemon_child`). +2 tests. |

## Metrics and Anomalies

- Tokens: 2.2M
- Duration: 1h58m worked
- Anomalies: none in cost. One in-plan loop-back (the CodeRabbit-caught double-line defect above) — caught and fixed before merge, exactly the pre-submission barrier working.

## Routing and Merge Behavior

- Review: 1 reviewer (CodeRabbit), 2 actionable comments → 1 fixed (the daemon-child double-line, a genuine defect in new code), 1 accepted. review-retrospective recorded 1 reviewer / 2 actionable.
- CI/merge: all checks green; merged via the merge queue (squash); branch `feature/client-resolution-log-capture` cleaned up; archived `.plan/local/archived-plans/2026-07-22-client-resolution-log-capture`. deploy-target v0.1.1184, 10 bundles synced, executor regenerated on-main at finalize.
- No cross-epic collision: the predicted PLAN-32 captured-logging-seam adjacency did not materialize — the outline found PLAN-03's `plan_logging` seam already present and rode it, so no second mechanism was authored and nothing collided.
- lessons-capture: 1 lesson `2026-07-22-07-002`.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-05 → shipped, pr `#971`, landing `landings/PLAN-05.md`
- [x] epic.md Ordered Queue row PLAN-05 → shipped
- [x] Open Defect "client resolution log dropped" → RESOLVED (code) for the routing adapters; **re-scoped**: the fix is correct and complete for maven/npm/gradle but structurally CANNOT reach pyproject (see the pyproject-routing-bypass defect below)
- [x] OBSERVED-NEGATIVE worktree-routing watch → COLLAPSED into world-1 (structural call-site bypass), with the mechanism now identified at the pyproject adapter
- [x] New Open Defect opened: pyproject adapter discards the factory routing handler
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

**pyproject-routing-bypass — VERIFIED ROOT CAUSE of the OBSERVED-NEGATIVE watch (candidate PLAN-06).**
Ground-truth code reading (not the paste) establishes the surface-drift signal's mechanism:

- The factory `create_execute_handlers()` returns `(execute_direct, cmd_run)`. The **second** element
  (`cmd_run`, `_build_execute_factory.py:648`) is the routing handler — it holds `_route_to_daemon`
  and the three `_record_resolution` calls.
- **Maven** (`_maven_execute.py:51`): `execute_direct, cmd_run = create_execute_handlers(...)` — uses
  BOTH handlers, so its `cmd_run` IS the factory's routing handler. Maven builds route and now emit the
  captured line. (npm/gradle follow the same shape.)
- **Pyproject** (`_pyproject_execute.py:76`): `_inner_execute_direct, _ = create_execute_handlers(...)`
  — DISCARDS the routing `cmd_run` into `_`, then defines its OWN local `cmd_run` (L154) that wraps only
  `build_queue_slot(plan_id)` around the self-heal `execute_direct`. No `_route_to_daemon`, no
  `_record_resolution`, and `plan_id` is not even forwarded into `execute_direct`.

**Consequence:** every `pyproject_build` in this repo (`./pw`, quality-gate, verify, coverage,
module-tests) runs in-process unconditionally, regardless of daemon liveness/registration, and emits no
`[BUILD-SERVER] resolved build` line even on stderr. This exactly reproduces the operator's observation
(no line despite `--plan-id` forwarded) and the daemon's zero audit activity during this repo's
build-heavy phases. It also means the daemon's core thesis — routing THIS repo's long, reap-exposed
builds so a killed waiter re-polls instead of destroying work — is NOT realized for the plan-marshall
repo, because its build tool is pyproject and pyproject can't route. Maven consumers (API-Sheriff) DO
route, which is why routing was ever observed at all.

The pyproject adapter overrode `cmd_run` to add the one-shot self-heal retry (`.pyprojectx` cache
corruption) but in doing so lost the daemon-routing path. A fix must re-thread routing THROUGH the
pyproject adapter (route first, then in-process fallback wrapping the self-heal + queue slot) rather than
bypassing it — a small, bounded plan on `_pyproject_execute.py` + `_build_execute_factory.py`, with
tests asserting a registered worktree pyproject build routes. This is larger than small-ops → staged as
a plan, not done inline. **Recommend staging PLAN-06 (pyproject-routing-integration).**

Cross-references: recorded as a recurrence on lesson `2026-07-21-14-001` (the operator's finalize note),
and it resolves the epic's long-standing routing Open Defect + OBSERVED-NEGATIVE watch into a concrete,
fixable call-site gap.
