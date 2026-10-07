envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:18:43Z

component=plan-marshall:phase-1-init
category=bug

# session_id not captured at init leaves every dispatch context-load unmeasured

## Context

`phase-1-init` logged a WARNING at plan creation: "session_id not captured at plan-init - phase-6-finalize will attempt a late session capture before its hard-block abort". The late capture did succeed, and the session id was eventually appended to `status.metadata.session_ids` at phase-5 entry. But the gap is not cosmetic, and its cost is measurable rather than theoretical: `manage-metrics enrich` attributes per-phase context-load figures by walking the session transcript against recorded phase windows, and without a session binding during phases 1 through 4 it had no anchor for those windows.

## Root cause

The session id is resolved late rather than at init, so the earliest phases run with no session binding. Anything that keys on the session — transcript attribution above all — has nothing to key on for the windows that elapsed before the late capture.

## Proposed action

Capture the session id at plan-init rather than deferring to a late attempt in finalize, or, where the runtime genuinely cannot supply it that early, make the consequence visible at the point of loss rather than only as an init-time warning: a metrics report whose entire Billing column is empty currently gives the reader no indication that a missing session binding is the cause.

## Evidence

- work.log line 3 — `[WARNING] (plan-marshall:phase-1-init) session_id not captured at plan-init - phase-6-finalize will attempt a late session capture before its hard-block abort`
- aspect: log_analysis — all 18 dispatch-boundary rows across `4-plan`, `5-execute` and `6-finalize` carry `unmeasured_columns: ["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]`
- aspect: log_analysis — `context_position_cost`: `total_rows: 18`, `measured_rows: 0`, `unmeasured_rows: 18`, `position_multiple: unmeasured`
- metrics.md — the `Billing (cost)` column is empty for every phase and for the Total; `totals_billing_weighted_total: 0` with `totals_billing_weighted_total_population_count: 0`
- Possibly related to existing lesson `2026-04-24-15-001` (session_id-resolver gap) — the orchestrator should reconcile before filing, since global-corpus dedup does not run on the orchestrated branch
