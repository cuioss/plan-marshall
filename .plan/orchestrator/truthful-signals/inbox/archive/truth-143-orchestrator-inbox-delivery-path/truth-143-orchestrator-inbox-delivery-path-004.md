envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:20Z

# outline-vs-shipped reports comparison: measured over an absent assessments store

component: plan-marshall:plan-retrospective
category: bug
confidence: high

## Context

The `outline-vs-shipped` aspect (aspect 15) ran on this plan and emitted:

- `assessments_store_present: false`
- `assessments_read: 0`
- `assessed_path_count: 0`
- `comparison: measured`
- `include_unrealised: {count: 0, denominator: 0, population: certain_include_assessed_paths}`
- `exclude_violated: {count: 0, denominator: 0, population: certain_exclude_assessed_paths}`
- `touched_but_unassessed: {count: 24, denominator: 24, population: realized_footprint_paths}`

Two of the three outcome classes report a confident `0` over a population of size `0`, from a store the fragment itself says is not present — and the top-level verdict says the comparison was `measured`.

## Root cause

The aspect's own contract says an unresolvable footprint yields `comparison: inconclusive` with the counts withheld. That guard is keyed on the **footprint** side. Here the footprint resolved fine (24 paths via `--diff-file`); it is the **assessment** side that is absent. There is no corresponding guard for it, so a run with a fully resolved footprint and an entirely absent assessment corpus takes the `measured` branch.

The denominators are honest — each `0` is published beside its `denominator: 0` and its named population, so a careful reader can reconstruct what happened. But `comparison: measured` is the field a consumer keys on, and it asserts that a comparison occurred. Two of the three classes had nothing to compare.

This is the epic's own archetype reproduced inside the retrospective that reports on it: a could-not-look rendering as a checked negative because the discriminator guards one input and not the other.

## Proposed action

Make `comparison` a three-state field over both inputs, not one. Concretely: `measured` requires a resolved footprint **and** `assessments_store_present: true` with `assessments_read > 0`; an absent or empty assessment store yields `comparison: no_assessments` (distinct from `inconclusive`, which stays reserved for the unresolvable-footprint case) and withholds `include_unrealised` / `exclude_violated` exactly as the footprint guard already withholds them.

`touched_but_unassessed` is legitimately measurable in that state — it needs only the footprint — so it should continue to report, which is precisely why the verdict must be per-class rather than a single top-level word.

## Evidence

- aspect: outline_vs_shipped — `assessments_store_present: false` and `assessments_read: 0` beside `comparison: measured`
- aspect: outline_vs_shipped — `include_unrealised` and `exclude_violated` both `count: 0, denominator: 0`
- contract: the existing footprint guard (`comparison: inconclusive` with counts withheld) demonstrates the intended shape; it simply does not cover this input
