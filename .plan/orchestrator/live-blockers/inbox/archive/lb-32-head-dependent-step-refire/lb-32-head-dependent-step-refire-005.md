envelope_version=1
sender_type=plan
sender_id=lb-32-head-dependent-step-refire
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T03:27:58Z

component=plan-marshall:phase-6-finalize
category=bug
source_plan=lb-32-head-dependent-step-refire
confidence=high

# Forward the step key on every record-dispatch-boundary call

## Context

On plan `lb-32-head-dependent-step-refire` every dispatch-boundary row was written without a step key: 2 of 2 rows in `4-plan`, 6 of 6 in `5-execute` and 46 of 46 in `6-finalize` are keyless. The execution log holds 19 execute rows and 56 finalize rows that do carry step ids. With no key on the boundary side, the dispatch audit paired zero firings in every phase, and all four context-load columns are `unmeasured` on all 54 rows.

The practical effect showed up in this retrospective: finalize cost 9498815 tokens across 46 dispatches, and the record cannot say how much of that each step consumed. The cost of 11 lessons-housekeeping firings and 10 plugin-doctor firings — the subject of the plan itself — had to be estimated from row shape.

## Root cause

The call sites that record a dispatch termination do not pass `--step-id`. The `manage-metrics` documentation says to forward the dispatch's step key on every call and that an omitted flag writes an empty key; the flag is optional, so the omission is silent.

## Proposed action

- Pass `--step-id` at every `record-dispatch-boundary` call site in the finalize dispatcher and the execute and plan workflows.
- Pass the four context-load flags where the dispatch return carries them.
- Consider having the verb report a keyless row in its return so the omission is visible at write time.
- Add a retrospective check that grades a phase with boundary rows and zero paired firings as unmeasured rather than leaving it to a reader.

## Evidence

- aspect: execution_context_dispatch_audit — `keyless_boundary_rows`: 2, 6 and 46; `paired_firings: 0` in all three phases; `unpaired_execution` 19 and 56; channel `confidence: low` (9 distinct finalize dispatch lines against 51 completions); `corroboration: uncorroborated` with 45 of 45 dispatch lines from a caller that resolved nothing for the role
- aspect: logging_gap_analysis — 54 of 54 boundary rows keyless
- aspect: plan_efficiency — per-step finalize cost reported as an estimate for this reason
