# WS-04: Footprint, Surface & References

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns the realized-vs-declared footprint machinery: upstream-base diffs with
creation-SHA bookkeeping, declaration containment rules, and git-output parsing
that never files prose as paths. Closed when the footprint a
plan reports is the footprint it realized, on a base it names.

## Scope

- In scope: manage-references footprint diffs and keys, orchestrator disjointness gate and
  corpus surfaces, baseline-reconcile parsing, self-review surfacer base refs.
- Out of scope: ledger cost attribution (WS-01), phase-5 absorb mechanics (WS-06).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-07-footprint-surface | running | Upstream-base diffs, creation SHA, containment rule, origin/main surfacing |
| PLAN-08-baseline-reconcile | staged | Localized-git parsing, drift recovery routing, lesson dedup keys |

## Sequencing and Surface Notes

- PLAN-07 (references/orchestrator) and PLAN-08 (workflow-integration-git) are
  surface-disjoint and may run concurrently.
