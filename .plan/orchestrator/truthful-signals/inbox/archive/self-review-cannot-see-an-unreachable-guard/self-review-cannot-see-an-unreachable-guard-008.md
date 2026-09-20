envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:16:56Z

component=plan-marshall:plan-retrospective
category=improvement
created=2026-07-29

# Add multi_module rows to the plan-efficiency calibration anchor table

## Context

On plan `self-review-cannot-see-an-unreachable-guard` (`scope_estimate=multi_module`,
`change_type=enhancement`), the `plan-efficiency` aspect's Section 2 calibration table has no row
for `multi_module` — only `surgical`, `single_module`, `cross_cutting`, and `complex` are anchored.
The aspect fell back to the generic ratio thresholds (`tokens_per_file_modified > 50_000`,
`seconds_per_task > 900`, `total_tokens_per_deliverable > 500_000`), all three of which tripped, but
the fallback thresholds are not tuned to `multi_module`'s actual complexity band and may be
systematically too tight for a legitimately-scoped multi-module plan.

## Root cause

`scope_estimate` takes the value `multi_module` in `references.json` (see also
`work/module_mapping.toon`), but the plan-efficiency reference's Section 2 table was authored
against the `scope_estimate` enum documented elsewhere (`surgical` / `single_module` /
`cross_cutting` / `complex`) and never gained a `multi_module` row.

## Proposed action

Either (a) add explicit `multi_module` rows (one per `change_type`) to the Section 2 calibration
table in `plan-retrospective/references/plan-efficiency.md`, calibrated from a corpus of prior
`multi_module` plans, or (b) confirm `multi_module` is meant to alias `cross_cutting`'s anchors and
document that alias explicitly instead of silently falling through to the generic fallback.

## Evidence

- aspect: plan-efficiency — `tokens_per_file_modified=253251` (fallback warning at 50000, unanchored),
  `seconds_per_task=5070` (fallback warning at 900, unanchored), `total_tokens_per_deliverable=696443`
  (fallback warning at 500000, unanchored) — all three [BUDGET] findings cite
  "multi_module+enhancement unanchored"
