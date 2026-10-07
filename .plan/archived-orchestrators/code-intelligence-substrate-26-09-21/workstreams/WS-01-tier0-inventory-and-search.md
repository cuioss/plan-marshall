# WS-01: Tier 0 — Inventory and Search Foundations

epic: code-intelligence-substrate

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-tier0-inventory-and-search.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Tier 0 is the always-available, **zero-configuration** layer of the substrate: the files inventory,
content search, and `build_map`. It closes when a question about "what files exist" and "which files
contain S" is answered completely and honestly for any project, with **nothing installed and nothing
configured**. This workstream exists because the operator's binding constraint — *"if they are not
configured, there is no gain"* — makes Tier 0 the floor that every higher tier degrades to.

## Scope

- **In scope**: the files inventory (categories, completeness), content search as a first-class
  capability, the honesty of a zero-result answer for the inventory verbs, and the documentation of
  the sweep primitive available to dispatched leaves.
- **Out of scope**: dependency-edge derivation and the resolver seam (WS-02); the skill-corpus
  reference index and its LSP surface (WS-03); measurement-window and cost-accounting correctness
  (WS-04); detector and derivation integrity in the planning phases (WS-05).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-inventory-blind-spot | staged | 130 markdown files invisible to BOTH inventories; make `find`'s zero-result honest |
| PLAN-03-content-search-seam | staged | `architecture search --content` via a script seam that reaches dispatched leaves |

## Sequencing and Surface Notes

- ⛔ **PLAN-01 and PLAN-03 both touch `manage-architecture` — NEVER pair them.** They are one
  serialization class. PLAN-01 runs first.
- ⭐ **PLAN-01 is the epic-wide pinch point.** It is the ONLY plan touching both
  `manage-architecture` and `tools-marketplace-inventory`, so it collides with WS-02's PLAN-04 and
  WS-03's PLAN-06 as well. **Run it alone, first, before any parallel wave opens.**
- PLAN-01 is a hard **prerequisite for WS-03**: an index built on an inventory blind to 130 files
  (33 of them `workflow/` docs, where verb contracts live) produces find-references and broken-xref
  answers that are wrong in the same confident direction the substrate already fails in.
- Cross-epic: neither plan touches `manage-execution-manifest`, `plan-retrospective`,
  `phase-3-outline`/`phase-4-plan`, or the project-local auditor, so neither trips the standing
  inverse obligation toward `truthful-signals`.
