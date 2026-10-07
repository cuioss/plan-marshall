envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:09:01Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_aspects=plan-efficiency

# Plan-efficiency anchor table cannot match three of five live scope_estimate values

## Context

`references/plan-efficiency.md` § 2 defines a calibration-anchor table keyed on `(scope_estimate, change_type)` that supplies the warning and error token thresholds for `[BUDGET]` findings. Its scope vocabulary is `surgical | single_module | cross_cutting | complex`.

The `scope_estimate` enum the composer actually validates is `none | surgical | single_module | multi_module | broad` (`manage-execution-manifest compose --help`).

The two sets overlap on exactly `{surgical, single_module}`. So three of five live enum values — `none`, `multi_module`, `broad` — can never match an anchor row, and two table rows — `cross_cutting`, `complex` — name scopes the system cannot produce.

This plan is `scope_estimate=multi_module`, so no row matched and the aspect fell through to the generic ratio fallbacks. All four fallback thresholds tripped (tokens_per_file_modified 361,407 vs 50,000; total_tokens_per_deliverable 1,084,222 vs 500,000; seconds_per_task 2,504 vs 900; max_phase_token_share 0.51 vs 0.50), so findings were still emitted — but they carry `UNANCHORED` instead of a calibrated threshold, and a plan that is genuinely over budget for its class is indistinguishable from one that merely has few files.

## Root cause

Same shape as the M3 defect filed alongside this one: a lookup table whose keys were authored against a vocabulary that later diverged from the enum the system validates, with no test asserting the two agree.

## Proposed action

Derive the anchor table's scope keys from the same enum `compose` validates, add rows for `multi_module` and `broad` (and decide whether `none` should be exempt rather than unanchored), and drop `cross_cutting` / `complex` or map them to their live equivalents. Add a conformance test asserting every value of the live enum has an anchor row — a population-derived check, not a spot check.

Also make the unanchored fall-through visible: the aspect currently degrades silently to generic ratios, which reads as a calibrated verdict.

## Evidence

- `manage-execution-manifest compose --help` — `scope_estimate (none|surgical|single_module|multi_module|broad)`
- `references/plan-efficiency.md` § 2 table rows — `surgical`, `single_module`, `cross_cutting`, `complex`
- `references.json` — `"scope_estimate": "multi_module"`; decision.log `2b7e7a` refined `single_module` to `multi_module`
- This run's fragment records `anchor_lookup.row_matched: false`
