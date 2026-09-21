envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:43:01Z

# A deep-lane plan recorded zero per-file assessments, leaving outline-vs-shipped vacuous

component: plan-marshall:phase-3-outline
category: improvement
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

`check-outline-vs-shipped` reported `assessments_store_present: false` and
`assessments_read: 0`. Both of its comparison classes therefore had denominator 0:

- `include_unrealised`: 0 of 0 `certain_include_assessed_paths`
- `exclude_violated`: 0 of 0 `certain_exclude_assessed_paths`
- `touched_but_unassessed`: 41 of 41 `realized_footprint_paths`

The aspect nonetheless returned `comparison: measured`, so a reader sees two
confident zeros over a population that was never assessed.

The same under-declaration shows up in the footprint: the outline declared 23
modification-intent paths and the plan shipped 41, and `ci_base.py` — the parser
this plan existed to fix — was declared `read`-intent in two deliverables and then
modified.

## Root cause

Nothing requires a deep-lane outline to record assessments, so the substrate the
outline-vs-shipped aspect consumes can be entirely absent while every downstream
count still renders as measured.

## Proposed action

Either require assessment capture on the deep lane, or have
`check-outline-vs-shipped` report `comparison: inconclusive` when
`assessments_read == 0` — the same could-not-look discipline the script already
applies to an unresolvable footprint. Two zeros derived from an empty population
must not present as measured findings.

## Evidence

- aspect: outline_vs_shipped — `assessments_store_present: false`, `assessments_read: 0`, `comparison: measured`
- aspect: artifact_consistency — `affected_files_exact_match` warn, 18 `references_only` paths
- aspect: request_result_alignment — 17 scope-creep paths; `ci_base.py` declared read, observed modified
- references.scope_estimate: multi_module; status.metadata.planning_lane: deep
