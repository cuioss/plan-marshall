envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:25Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high

# Register dispatch_boundaries as an aspect or hoist it out of log-analysis

## Context

`SECTION_SPEC` declares a `Phase Dispatch Boundaries` section whose `conditional_trigger` is the fragment key `dispatch_boundaries`. `compile-report` carries a dedicated gate for it (`_dispatch_boundaries_has_present_phase`, line 100) and a dedicated renderer (`render_dispatch_boundaries_body`, line 439). Both read a TOP-LEVEL bundle key.

No documented producer registers that key. `analyze-logs` emits `dispatch_boundaries` as a sub-block INSIDE the `log-analysis` fragment, and the SKILL.md aspect table has no row that registers it separately.

This run registered a `log-analysis` fragment carrying 22 dispatch rows across three phases, every phase with `present: true` — and `Phase Dispatch Boundaries` still reported as a benign omission. The gate looked for a top-level key that was never there, found nothing, and the section reported as though there were nothing to show.

The data is substantial and directly relevant: per-dispatch termination causes, token totals, and the four context-load columns for all 22 dispatches. It renders nowhere.

## Root cause

The producer nests the block and the consumer reads it at the top level. Because the trigger is absent rather than empty, the miss takes the benign-omission path — "the trigger fragment was absent, so there was nothing to lose" — which is exactly wrong here: the payload existed and was lost.

## Proposed action

Either register `dispatch_boundaries` as its own aspect (it is already in `valid_aspect_keys()`, so `collect-fragments add --aspect dispatch_boundaries` is accepted today) and document that step in the SKILL.md aspect table, or hoist the sub-block out of the `log-analysis` fragment at compile time. Whichever is chosen, a section whose renderer exists and whose data was collected should not be able to report as a benign omission.

## Evidence

- marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py line 145 - the section row and its trigger key.
- compile-report.py lines 100-121 (the gate, reading `fragments.get('dispatch_boundaries')`), line 131-132 (the dispatch), line 439 (the renderer), line 825 (the render branch).
- This run: `log-analysis` registered with `dispatch_boundaries` present for 4-plan, 5-execute and 6-finalize (22 rows total); `compile-report` returned `Phase Dispatch Boundaries` under `sections_omitted`, not `sections_dropped`.
