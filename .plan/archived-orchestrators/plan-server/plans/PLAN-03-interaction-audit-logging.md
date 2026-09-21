# PLAN-03: marshalld interaction audit logging — client work-log + server-side audit

epic: plan-server
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.

## Objective

Every marshalld interaction must be auditable from both sides. On the **client** side, each daemon
interaction is logged to the plan work log — submit/enqueue with its result, and every status query
with its result — so a session's dealings with the daemon are reconstructable from plan artifacts. On
the **server** side, the daemon keeps its own structured, append-only interaction log (this plan
settles its shape — central vs project-specific). The two sides share a correlation id so any single
interaction can be traced end-to-end. This closes the observability gap that let the registered-but-
inert defect (PLAN-02) stay invisible: the failure class survived because outcomes left no legible
per-interaction trace.

## Operator-stated requirements (the contract to satisfy)

- **Client side → work log.** Each interaction logged via `manage-logging` (work verb, per-plan):
  enqueue/submit **with its result** (job_id, status, eta, queue_position), and **each status query
  with its result** (the status TOON — running+liveness, or terminal). Fallback and
  `refused(reason=…)` outcomes are logged too (parity with the preflight "every outcome logged" rule).
- **Server side → its own log.** The daemon records every request/response. **Design question to
  settle (do NOT pre-decide in the spec):** central single log vs project-specific logs. Recommended
  frame for the outline to evaluate: a machine-global daemon argues for a central authoritative
  append-only log, each record stamped with `project_root` + `plan_id` + `job_id` + timestamp +
  outcome so it filters per-project; a project-scoped view is *derived*, not a second source of
  truth. `job-logs/` (per-job build output) already exists — extend, don't duplicate.
- **Auditable.** Each interaction is individually reconstructable — who submitted, what, when, what
  the daemon answered, and the terminal outcome.
- **Silent fail-soft is the bug this closes (field evidence, API-Sheriff 2026-07-19).** When the
  daemon `refused`/was unreachable, the client fell back to in-process AND logged the reason only at
  Python INFO — which nothing captures — so the system looked armed while doing nothing for every
  build. HARD requirement: every fallback and every `refused(reason=…)` is logged at a CAPTURED
  level (the plan work log via `manage-logging`), never only at an uncaptured Python log level. A
  fallback that leaves no legible artifact is a defect, not acceptable degradation.

## Deliverables

1. **Client-side interaction logging.** `build-server-client` logs every daemon interaction to the
   plan work log through `manage-logging` — submit (+result), each wait/status query (+result TOON),
   fallback, and refusal. No interaction is silent.
2. **Server-side interaction log.** `marshalld` writes a structured append-only record per
   request/response (submit, wait/poll, refuse, terminal transition), stamped with the attribution
   fields above. Settle central-vs-project-specific structure with a recorded rationale.
3. **End-to-end correlation.** A shared correlation id (the `job_id`, already written to the
   change-ledger `kind=job` at submit) ties the client work-log entries ↔ the server records ↔ the
   ledger entry, so one interaction is traceable from either side.
4. **Audit affordance + retention.** A way to inspect an interaction (e.g. a `manage-build-server`
   status/logs read verb over the server log); retention caps + GC (ties into S6); **no secrets in
   any log** (S4 — provider secrets never logged; redact env/args as needed).
5. **Tests.** Assert: client logs enqueue + each status query with results; the server log carries
   exactly one auditable, attributed record per interaction; the correlation id is present and
   matches on both sides and in the ledger; a refusal/fallback is logged, not silent.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/build-server-client/**` (client-side logging calls)
- `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` (server log)
- `marketplace/bundles/plan-marshall/skills/manage-build-server/**` (audit/logs read verb)
- `manage-logging` integration (client work-verb usage)
- change-ledger `kind=job` correlation-id linkage
- tests for the above

## Dependencies and Sequencing

- Depends on: none hard — logging can land independently of PLAN-02. BUT sequenced after PLAN-02
  because the two share surface (`marshalld.py`, `build-server-client`), and the routed-interaction
  audit is only exercisable end-to-end once PLAN-02 makes routing live (before that, only
  refusals/no-ops route through the client).
- Overlaps with: PLAN-02 (`marshalld.py`, `build-server-client`) → run sequentially, PLAN-02 first.

## Hand-Off Command

```text
/plan-marshall task="Add full interaction audit logging to the marshalld build server. Client side (build-server-client): log every daemon interaction to the plan work log via manage-logging — submit/enqueue with result (job_id/status/eta/queue_position), each status query with its result TOON, plus fallback and refused outcomes. Server side (marshalld.py): keep a structured append-only interaction log recording every request/response stamped with project_root + plan_id + job_id + timestamp + outcome; settle central-vs-project-specific structure with rationale (recommended: central authoritative log with per-project attribution + derived project-scoped view; extend existing job-logs/, do not duplicate). Provide end-to-end correlation via the change-ledger kind=job job_id so an interaction is traceable client↔server↔ledger; add a manage-build-server logs/status read affordance; retention caps + GC; no secrets in logs. Tests assert client logs enqueue + each query with results, one attributed server record per interaction, and correlation-id match on both sides. Spec: .plan/local/orchestrator/plan-server/plans/PLAN-03-interaction-audit-logging.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-03.md}
