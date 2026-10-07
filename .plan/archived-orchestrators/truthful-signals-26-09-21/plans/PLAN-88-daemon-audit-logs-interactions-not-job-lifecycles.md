# PLAN-88: The Daemon Audit Logs INTERACTIONS, But Is Read As A JOB LOG — So It Cannot Answer The Question It Appears To Answer

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Raised 2026-07-27 from a live operator diagnosis ("is the build server stuck?"), where the audit log
> could not distinguish a completed job from an abandoned one. **Operator-directed: the logging must
> become genuinely useful, not merely more verbose.**
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

`manage_build_server logs` presents rows shaped like job records — `job_id`, `outcome` — but the store
behind it is an **interaction** audit: exactly one record per *request*, whose `outcome` is that
request's *response status*. A `submit` therefore rests permanently at `outcome: queued`, which is a
truthful statement about the **request** and an unanswerable one about the **job**. Job completion is
not a request, so no record is ever written for it. Make the operator-facing surface able to answer
"what happened to this job?" — the question it already looks like it answers.

## ⚠ Mechanism — verified first-party 2026-07-27, read this before scoping

- OBSERVED: `marshalld.py` § `_audit_interaction` (`:302-336`) records **one row per request**, with
  `outcome=str(response.get('status', ''))` (`:332`). Its own docstring says "Append exactly one
  attributed interaction record for **this request**" (`:303`) — the class is named
  `InteractionAudit`, and it is behaving exactly as designed.
- OBSERVED: `_marshalld_audit.py:18-25` fixes the record schema at `op` / `project_root` / `plan_id` /
  `job_id` / `outcome` / `timestamp` (+ a non-secret `reason`), with a deliberate secrets discipline
  that must be preserved by any fix.
- OBSERVED (live, this project): three `submit` records exist — `2026-07-25T15:48:48Z`,
  `2026-07-25T19:56:04Z`, `2026-07-27T06:39:29Z` — **all `outcome: queued`, with no terminal record of
  any kind, and no result-collection record for any of them.**
- **⇒ The defect is a category mismatch, not a missing field.** `queued` is not a stale value that
  someone forgot to update; it is the *correct and final* answer to "how did the submit request
  resolve?". The surface is honest at the record level and misleading at the reading level — which is
  this epic's archetype in its purest form: **a truthful field answering a different question than the
  reader's.**
- **⇒ Therefore "log more" is the wrong instinct** and D1 must resist it. Adding rows to an
  interaction log leaves the same ambiguity; the fix is to make job *lifecycle* observable, or to stop
  the read surface implying a lifecycle it cannot see.
- HYPOTHESIS: the three jobs above were genuinely abandoned (submitted, never collected). The absence
  of a result-collection record is *consistent* with abandonment but does not prove it — a completed
  job that was never polled would look identical. **Confirm/refute against the daemon's own job/queue
  state store, not the audit log** (verify-at-outline). ⚠ **This ambiguity IS the bug — do not resolve
  it by assumption, and do not let a plausible reading of these three rows become a finding.**

## Deliverables

### D1 — GATE: decide what the operator surface must answer, and pick the layer (mutates nothing)

(a) **Establish the job lifecycle the daemon actually has** — the real states between accept and
completion (queued / running / finished / failed / timed-out / abandoned / evicted), read from the
scheduler, not assumed from the audit schema.
(b) **Choose the layer.** Two families, and the choice is the deliverable:
**(i) emit job-lifecycle events** — the daemon writes a terminal record when a job leaves the
scheduler, making the log a genuine job history; **(ii) join at read time** — `logs` reports live job
state alongside the interaction rows, leaving the audit store untouched. ⚠ Weigh a real trade: (i)
gives durable post-hoc history but writes on a path that must never block request handling; (ii) is
cheaper and cannot lie about the present, but tells you nothing after the daemon restarts. **A hybrid
is legitimate — say so explicitly if chosen.**
(c) **Settle the unknowable case.** A job whose fate genuinely cannot be determined (daemon restarted
mid-flight) MUST render as `unknown`, never as `queued` and never as a terminal state.
**Fail-closed: an absent record is not evidence of success, and it is not evidence of failure either.**
(d) ⚠ **Preserve the secrets discipline** (`_marshalld_audit.py:18-25`) and the best-effort guarantee
(`marshalld.py:335-336` — audit writing must never abort request handling). Neither may be traded for
observability.

### D2 — implement the D1 choice

Scoped to D1. **Hard constraint: `outcome` must never carry a value that reads as terminal when the
daemon does not know the job's fate.** If the schema keeps `outcome`, D1(c)'s `unknown` is a required
member; if it splits request-outcome from job-outcome, the read surface must label which is which.

### D3 — the read surface stops implying a lifecycle it cannot see

`manage_build_server logs` must make the record's *kind* unmistakable — an interaction row is labelled
as one. ⚠ **This deliverable stands even if D1 picks the cheapest option**: the current surface's core
problem is that a reader cannot tell they are looking at request outcomes, and that is fixable
independently of any lifecycle work.

### D4 — tests

(a) A submitted-then-completed job is distinguishable from a submitted-then-abandoned one at the
operator surface — **the test must be verified to FAIL against current code**, where both render
identically as `outcome: queued` (this epic has a recorded `test-pins-the-defect` archetype).
(b) A daemon restart mid-flight renders `unknown`, not `queued` and not a terminal state.
(c) The secrets discipline holds: no new field carries a path beyond `project_root`, env, or argv.
(d) An audit-write failure still cannot abort request handling.

Four deliverables (D1 a gate) — under the split guard.

## Expected Surface

- OBSERVED: `manage-build-server/scripts/marshalld.py` — `_audit_interaction` `:302-336`, the
  `outcome` derivation `:332`, the best-effort guard `:335-336`, `_audit_attribution` / `_audit_job_id`
  (called at `:320-321`), and the scheduler `submit` seam at `:383`.
- OBSERVED: `manage-build-server/scripts/_marshalld_audit.py` — the schema/secrets contract `:18-25`,
  `record()` `:147`, `read_all()` `:200`, `read_records_or_none()` `:218`.
- OBSERVED: `manage-build-server/scripts/manage_build_server.py` — the `logs` verb (the operator read
  surface D3 changes).
- HYPOTHESIS: the scheduler module owning job state — exact file resolved at outline; D1(a) reads the
  real lifecycle from it (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/manage-build-server/**`.
- OBSERVED: `manage-build-server/SKILL.md` — the `logs` verb is documented as read-only inspection of
  the interaction audit; the doc moves in lock-step with whatever D3 changes.

**Disjointness:** `manage-build-server` (+ tests). Disjoint from PLAN-79 (`platform-runtime` /
`manage-status` / `manage-locks`), PLAN-56 (`marshall-orchestrator`), PLAN-75
(`manage-execution-manifest`), PLAN-87 (`script-shared` / `pm-dev-oci` / `extension-api`), PLAN-86
(`phase-5-execute`).
⚠ **Adjacent to PLAN-62** (`build-timeout-learned-value-truthfulness`) — PLAN-62 owns build-timeout
reporting and touches `ci_base` / build engines, not the daemon audit; file-disjoint, but if PLAN-62
lands a timeout-truthfulness change, D1(a)'s lifecycle list should include the timed-out state as
PLAN-62 defines it rather than inventing a parallel vocabulary.
⚠ **Adjacent to PLAN-58** (`marshalld-self-reload-on-version-signal`) — same bundle, different concern
(version reconciliation vs. job observability). **Do not run concurrently**; whichever lands second
re-grounds.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-58** — same bundle; sequence, do not parallelize.
- Adjacent to: PLAN-62 (see above) — coordination on the timed-out vocabulary only.
- ⚠ **Related standing defect, NOT this plan's to fix:** timed-out builds are recorded with
  `exit_code: 0` (two confirmed sightings — PLAN-55 landing and the PLAN-80 landing #1021). That is
  **PLAN-59**'s. If D1(a) finds the daemon's own timeout path shares the mechanism, record the finding
  and route it to PLAN-59 rather than absorbing it here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-88-daemon-audit-logs-interactions-not-job-lifecycles.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception
for orchestrated plans. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
