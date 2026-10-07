envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:24:02Z

component=plan-marshall:plan-retrospective
category=bug
title=The plan-efficiency calibration table has no row for change_type=enhancement, so no such plan can trip a token anchor

# A budget anchor table whose key space does not cover the values the system emits

## Context

`references/plan-efficiency.md` Section 2 defines token/time anchors keyed on `(scope_estimate, change_type)`. The `change_type` column enumerates exactly three values: `bug_fix`, `feature`, `refactor`.

This plan's `status.metadata.change_type` is `enhancement`. The lookup misses, and the aspect falls through to the weaker generic ratio thresholds.

## Root cause

The anchor taxonomy and the taxonomy `manage-status change-type-heuristic` actually emits have diverged. A plan carrying any unlisted `change_type` is structurally incapable of tripping a `[BUDGET]` finding on its absolute token total — it can only trip the per-file and per-deliverable ratios.

For this plan the fallbacks did fire (3 of 4 tripped: 420,831 tokens/file against a 50,000 threshold; 1,332,632 tokens/deliverable against 500,000; 2,260 s/task against 900). So the escape was not silent **here**. But a plan with a large footprint would divide its way under every fallback while consuming millions, and the absolute anchor that exists to catch exactly that would never be consulted.

## Proposed action

Derive the table's `change_type` key space from the emitting enum rather than restating it, or add the missing rows. Per the project's own doctrine on restated enumerations: prefer removing the duplicated list over correcting it.

## Evidence

- aspect: plan_efficiency — `anchor_lookup.anchored: false`, reason "change_type 'enhancement' is absent from the anchor taxonomy"
- `status.metadata.change_type: enhancement`
- `references/plan-efficiency.md` Section 2 table
