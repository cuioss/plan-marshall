envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:07:37Z

component=plan-marshall:manage-references
category=improvement
title=affected_files under-records the realized footprint, and recorded deviations stay unparseable prose

# affected_files under-records the realized footprint, and recorded deviations stay unparseable prose

## Context

For plan `a-refusal-is-recorded-as-a-refusal-the-record`, `references.json` holds:

- `affected_files`: 24 paths
- `realized_footprint`: 32 paths

The 8-path gap is not noise. Six of the eight are genuine scope growth (finalize's own `phase-6-finalize/SKILL.md`, `workflow-pr-doctor/standards/automated-review-lifecycle.md`, and four test modules); the other two were declared read-intent and became writes.

What makes this instance worth a lesson is that **the plan detected the problem itself, three times, and the detection went nowhere**. `decision.log` carries three `FOOTPRINT DEVIATION` entries:

1. `test_comments_stage.py` — declared read-only, forced to a write by the deliverable-2 record-shape change. The entry names the archetype explicitly: "this is the affected_files under-declaration archetype".
2. `test_pr_wait_for_comments_rate_limited.py` — in neither `affected_files` nor `read_intent_files`, forced to a write by the same change. The entry concludes: "the reconciliation at finalize should expect both".
3. `test_review_merge_invocation_contract.py` — same class, deliverable 4.

All three are free-text prose in `decision.log`. No consumer parses them. The finalize footprint reconciliation the second entry addresses by name never received them.

## Root cause

There is a structured surface for the declared footprint and a structured surface for the realized footprint, but no structured surface for the **deviation between them discovered mid-execute**. The only channel available to an agent that notices one is the decision log, which is a narrative record, so a correctly-detected, correctly-reasoned deviation degrades into text.

## Impact

Every finalize step that scopes itself from `affected_files` scoped against 24 of 32 files — a quarter of the real footprint invisible to it. In this plan that includes plugin-doctor scope selection, simplify scope, and architecture-refresh's affected-module derivation. The retrospective's own `tokens_per_file_modified` ratio inherits the same under-count and is therefore a conservative over-estimate.

## Proposed action

1. Add a structured deviation verb, e.g. `manage-references record-deviation --path P --deliverable N --declared-intent {read|write|undeclared} --actual-intent {read|write} --reason TEXT`, appending to a deviation ledger the finalize reconciliation reads.
2. Have the three-way reconciliation consume that ledger, so a deviation the plan declared is reported as a **declared** divergence rather than as undeclared drift — which is exactly what the second decision-log entry was trying to arrange by hand.
3. Consider updating `affected_files` at the point of deviation, so downstream affected_files-scoped steps see the real surface rather than the outline's estimate of it.

## Evidence

- aspect: artifact_consistency — `affected_files_exact_match: warn`, `references_only[8]`
- aspect: outline_vs_shipped — `touched_but_unassessed: 7 of 32 realized_footprint_paths`
- aspect: request_result_alignment — `footprint_recording_gap: 24 vs 32, delta 8`
- log: `decision.log` entries at 22:30:46Z, 22:40:25Z (2026-08-29) and 23:11:46Z — the three `FOOTPRINT DEVIATION` records
- aspect: llm_to_script_opportunities — candidate "Recording a footprint deviation", repetition_count 3, complexity low
