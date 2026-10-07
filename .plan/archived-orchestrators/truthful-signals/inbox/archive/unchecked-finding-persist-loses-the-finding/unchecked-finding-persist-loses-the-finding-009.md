envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T17:24:27Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
created=2026-07-28

# Dispatched finalize steps reach terminal outcomes with no [DISPATCH] log evidence

## Context

The execution-context-dispatch-audit retrospective aspect found that two finalize steps
classified DISPATCHED in `standards/dispatch-inline-split.md` — `create-pr` (its only pass)
and `automatic-review` (its SECOND pass, triggered by `re_review_on_branch_cleanup` after a
loop-back) — reached a terminal `outcome=done` / `outcome=executed` record in
`status.metadata.phase_steps["6-finalize"]` / the execution manifest's `execution_log` with
ZERO matching `[DISPATCH]` work-log line anywhere in the plan's `logs/work.log`. Every OTHER
dispatched built-in step in the same run (`pre-submission-self-review`, `finalize-step-simplify`,
`automatic-review`'s first pass, both `project:`-prefixed steps) DID emit the canonical
`[DISPATCH]` line. `architecture-refresh`'s absence is separately explained and benign
(its only dispatching tier, Tier 1 LLM re-enrichment, was skipped this run because
`change_type=bug_fix`) — this lesson is scoped to `create-pr` and the automatic-review
re-review path only.

## Root cause

Not fully diagnosed from this plan's evidence alone. The pattern (first pass of a step emits
`[DISPATCH]`, a re-triggered/re-entrant pass of the SAME step does not; `create-pr` never emits
one at all) suggests the dispatch-logging instrumentation may be attached at a call site that
`create-pr` bypasses, or that re-entrant dispatches within an already-open finalize envelope
skip the logging call a fresh top-level dispatch takes.

## Proposed action

Trace `create-pr`'s and the re-review `automatic-review` invocation's actual dispatch call
sites against `ref-workflow-architecture/standards/dispatch-logging.md` § "Emission contract"
and confirm whether they route through the same instrumented dispatcher used by
`pre-submission-self-review` / `finalize-step-simplify`. If they use a distinct call path, add
the `[DISPATCH]` emission there; if they share the same call path but a re-entrant invocation
short-circuits past it, guard the short-circuit so every terminal outcome still gets its own
`[DISPATCH]` line.

## Evidence

- aspect: execution-context-dispatch-audit — 2 `dispatch_coverage_violation` findings (create-pr;
  automatic-review second pass), full plan: unchecked-finding-persist-loses-the-finding, PR #1038
- aspect: logging-gap-analysis — corroborating ARTIFACT_EMISSION gap in the same plan shows a
  parallel pattern (only the LAST/re-entrant task in a sequence gets its expected log emission)
