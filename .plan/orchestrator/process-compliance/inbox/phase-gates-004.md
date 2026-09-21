envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=finding
created=2026-09-19T09:47:04Z

# Finding: PLAN-01 hand-off is non-idempotent; queue linkage missing

**Reporter:** phase-gates (plan).

**1. Re-issued hand-off collides instead of resuming.** The orchestrator's
emitted command `task="implement .../PLAN-01-phase-gates.md"` carries no plan
pointer. Re-running it after plan `phase-gates` already exists (2-refine,
in-flight) re-enters init derivation, which would stage a duplicate plan; only
the Step 3 exists-collision prompt (Resume/Replace/Rename) saves it, and that
prompt is bypassed on non-interactive/autonomous runs. A hand-off shape that
resolves to the existing plan (e.g. emitting with the `plan=` pointer once
launched, or an init guard that auto-resumes on `source_id` match) would make
re-issue safe.

**2. Queue row has no back-pointer (fixed this session).** `status.json`
`plans[]` row PLAN-01 carried empty `plan_marshall_plan_id` while the live plan
`phase-gates` (request `source_id` = the PLAN-01 spec) flew for a day — a
decoupled reader could not join spec to plan except by grepping request bodies.
Fixed via `queue --set-row PLAN-01 --field plan_marshall_plan_id --value
phase-gates`; recommend the `next` emit path stamp this at launch time.

**3. Resume anchor went stale across the incident (fixed this session).** The
anchor still read "emit refused — unfillable behind unlanded PLAN-01" while
PLAN-01's code sat uncommitted on main and the plan had advanced to 5-execute.
Refreshed via `update-field --store orchestrator --field resume_anchor`.
Recommend re-deriving the anchor after every unplanned-main-mutation detection,
not only after queue transitions.

**Advisory (non-blocking):** `generate_executor preflight` reports
`marshal_status: stale` (marshal 0.1.1636 vs installed 0.1.1705); continued
per the advisory-only contract without mutating config — operator to run
`/marshall-steward` at convenience.
