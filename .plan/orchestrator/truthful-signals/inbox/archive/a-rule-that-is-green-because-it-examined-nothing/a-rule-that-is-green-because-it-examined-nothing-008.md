envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:41:44Z

component=plan-marshall:plan-retrospective
category=bug
title=compile-report drops the dispatch-boundaries section and then deletes the evidence
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing

# compile-report drops the dispatch-boundaries section and then deletes the evidence

# Context

Both halves of this were observed live, in this retrospective's own compilation pass.

**Half 1 — the section that drops is the one carrying the largest numbers.** `dispatch_boundaries` is the only key in the `collect-fragments` registry whose fragment must be a **bare per-phase dict** (`{"6-finalize": {present: true, rows: [...]}, ...}`). Every other aspect fragment is status-wrapped (`aspect:` / `status:` / payload). The gate `_dispatch_boundaries_has_present_phase` iterates the fragment's top-level values looking for a dict with `present: true`; a status-wrapped fragment presents `aspect`, `status`, `plan_id`, … instead, so it is silently gated out.

Compounding it: `dispatch_boundaries` has **no row in the SKILL.md aspect table** and **no reference doc**. Nothing in the documented Step 3 workflow produces it, so on a by-the-book run section 5 "Phase Dispatch Boundaries" never renders at all. The shape requirement exists only as a docstring in `compile-report.py`.

The first compile returned:

```
status: warning
sections_written[17]
sections_dropped[1]:
  - Phase Dispatch Boundaries
```

The dropped section carried this plan's single largest figure — 6-finalize's 2,895,242 dispatched tokens, 2.01× the whole `metrics.md` total, and the only place that number exists.

**Half 2 — the bundle is deleted on the very path that needs it.** `compile-report run` auto-deletes the fragment bundle after the report is written. The documented retention rule is *"On failure paths (before the report is flushed to disk), the bundle is retained so the aspect fragments remain available for debugging."* A `status: warning` run writes the report, so it is not a failure path — and the bundle was deleted. Recovering the dropped section required re-running `collect-fragments init` and re-registering all 17 fragments by hand.

The `warning` path is precisely the debugging path: it is the only status that means "content the aspect produced never reached the report".

## Root cause

Half 1 is an undocumented shape exception in a registry that is otherwise uniform, on a key with no aspect-table row to document it. Half 2 is a retention rule partitioned on `report_written` when the condition that matters is `sections_dropped == []`.

## Proposed action

- Retain the bundle whenever `sections_dropped` is non-empty, not only on the pre-write failure path. One-line condition change; it is the difference between a one-command retry and re-registering every fragment.
- Give `dispatch_boundaries` a row in the SKILL.md aspect table and a short reference doc stating the bare per-phase shape, or (preferably) normalise the gate to accept a status-wrapped fragment carrying its phases under a `phases:` key like every other aspect.
- Have the drop message name *why* the section was gated out (which predicate failed), not only which heading was lost.

## Evidence

- aspect: dispatch_boundaries — first compile `status: warning`, `sections_dropped[1]: Phase Dispatch Boundaries`; after reshaping to the bare form, `sections_written[18] sections_dropped[0]`
- source: `compile-report.py` `_dispatch_boundaries_has_present_phase` and the `dispatch_boundaries` carve-out in `should_emit`
- source: `plan-retrospective/SKILL.md` Step 3 aspect table has 15 rows, none for `dispatch_boundaries`; `references/report-structure.md` section 5 depends on it
