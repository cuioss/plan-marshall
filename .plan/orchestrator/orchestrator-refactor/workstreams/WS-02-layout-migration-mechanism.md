# WS-02: Layout Migration Mechanism

epic: orchestrator-refactor

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-layout-migration-mechanism.md` and is tracked in
> the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns aspect 2 of the epic: a REUSABLE, self-terminating migration mechanism — a read
against a retired address resolves transparently to its successor, the redirect carries a
machine-evaluable expiry, and a scheduled sweep reports (and on `--apply` removes) every
redirect whose expiry has fired. The existing `SHIM(A)`/`SHIM(B)` marker convention already
covers authoring and static validation; this workstream builds the missing half — the part
that actually fires — as a generic extension over ALL marked shim sites, not a bespoke
one-off for the orchestrator move. The orchestrator store relocation (WS-01) is this
mechanism's first consumer, proving it end to end, not its only one.

## Scope

- In scope: an additive, machine-evaluable expiry grammar on top of the existing
  `shim-owner`/`shim-floor`/`shim-remove-when` markers; a dry-run-by-default/`--apply` sweep
  over the marked-shim population; a `marshal.json` `system.retention` knob for the expiry
  window; the redirect primitive at the shared resolver (consumed by WS-01); an ADR, since
  none currently governs deprecation/migration/shim in this codebase.
- Out of scope: deciding WHETHER the orchestrator-store move needs a shim at all (that is
  the four-condition checklist's call, taken when WS-01's plans reach outline); retroactively
  re-marking the 18 existing shim sites beyond a first-party classification; anything about
  the orchestrator's own identifier vocabulary (WS-03) or file layout (WS-01).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-self-terminating-layout-migration | staged | Extends the shipped shim-marker convention with a firing sweep. Sequenced after PLAN-01 (shares the resolver tier it adds a redirect to). |

## Sequencing and Surface Notes

- PLAN-03 depends on PLAN-01 (WS-01): its D6 ("the orchestrator store migration as the first
  consumer") reads PLAN-01's landed resolver tier, and both touch
  `script-shared/scripts/marketplace_paths.py`. Never run concurrently.
- PLAN-03 has no declared surface overlap with PLAN-02 or PLAN-06 — the one genuinely disjoint
  pair found in this epic's corpus — but DOES overlap PLAN-04 (WS-03) on
  `pm-plugin-development/.../plugin-doctor/references/rule-catalog.md` (both plans register a
  new rule/entry there: PLAN-03 for the expiry-sweep finding classes, PLAN-04 for the
  argument-naming enforcement amendment). This overlap was not caught by the corpus
  cross-check's automated matcher (both files resolve the same path via different bullets) —
  recorded here by hand. Sequence PLAN-03 and PLAN-04 rather than emitting them concurrently.
