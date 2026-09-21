envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:04Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=plan_efficiency

# Retrospective can never read billing composition - enrich runs 3 orders later

## Context

Every `quality-verification-report.md` this system produces renders the `Billing (cost)` column
as `-` and reports `totals_billing_weighted_total: 0` with
`totals_billing_weighted_total_population_count: 0`. This run is no exception. It is not a
per-plan data gap.

## Root cause

`manage-metrics enrich` is the only producer of `billing_weighted_total` and of the four-field
`message.usage` view. It is invoked by `default:record-metrics`, whose finalize `order` is 998.
`plan-marshall:plan-retrospective` runs at `order: 995`. The retrospective's Step 2.5 reconcile
calls `manage-metrics generate`, which folds the durable accumulators but does NOT compute the
billing view. So the plan-efficiency aspect structurally reads billing as unmeasured on every
run, and the epic whose top priority is token reduction has no billing composition in any of its
own retrospectives.

## Proposed action

Either (a) call `enrich` from the retrospective's Step 2.5 alongside `generate` — it is
idempotent per-phase and `record-metrics` would overwrite with the authoritative close, or
(b) move the retrospective after `record-metrics`, or (c) have the plan-efficiency aspect
declare billing as `unmeasured_by_construction` with the ordering as its stated reason, so the
empty column stops reading as "this plan had no billing cost".

Option (c) is the minimum: an empty column that looks like a measured zero is precisely the
epic's theme. Options (a)/(b) are what actually make the number available.

## Evidence

- aspect: plan_efficiency — `totals_billing_weighted_total: 0`, `population_count: 0`, while
  `totals_tokens: 2684301`
- ordering: `plan-retrospective` frontmatter `order: 995`;
  `phase-6-finalize/standards/record-metrics.md` frontmatter `order: 998`, and its body
  sequences `end-phase` -> `enrich` -> `generate`
