# WS-03: Identifier Vocabulary

epic: orchestrator-refactor

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-identifier-vocabulary.md` and is tracked in the
> epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns aspect 3 of the epic: the same value — the epic's own name — is spelled `--slug`
(twice), `--plan-id` (twice), and `--epic` (once) across five first-party scripts. This
workstream decides ONE vocabulary for "the name of the thing I am operating on" and
executes that decision for the epic-name half of the surface. It explicitly does NOT
attempt the fleet-wide `--plan-id` rename in the same breath — that surface is ≥38 scripts
and 215 doc files, an order of magnitude larger, and bundling it here would produce a plan
too large to verify.

## Scope

- In scope: the decision (which spelling wins, what happens to the four scripts already
  using `--name` for something else, how the epic-name and the plan-row `slug` field are
  told apart, how the two same-named "orchestrator" entities in this codebase are
  disambiguated); execution of that decision across `orchestrator.py`, `platform_runtime.py`,
  `manage-status`, `manage-logging`, `epic-surface-partition.py`, and their ~19 doc call
  sites; the `argument-naming.md` standard amendment the decision requires.
- Out of scope: the fleet-wide `--plan-id` rename across the other ≥36 scripts and ~215 doc
  files that use it for a Plan (successor plan, not staged here); any file-layout or schema
  restructuring beyond what the rename itself touches (WS-01 owns schema shape).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-04-identifier-vocabulary-decision | staged | Decision-only: derive the population, settle the vocabulary, amend the standard, write an ADR. Renames nothing. |
| PLAN-05-identifier-rename-execution | staged | Executes PLAN-04's decision for the epic-name half only. Depends on PLAN-04; sequenced after PLAN-02 (WS-01) since both touch the `status.json` schema. |

## Sequencing and Surface Notes

- PLAN-05 depends on PLAN-04 by construction (it executes the decision PLAN-04 produces) and
  both touch `argument-naming.md` — sequential, not concurrent.
- PLAN-05 collides with WS-01's PLAN-02 on `orchestrator.py`, `plan-orchestrator/SKILL.md`,
  and `manage-status/**` (incl. `_status_core.py`, `status-lifecycle.md`) — the sharpest
  collision in the epic's corpus, since PLAN-02 changes the `status.json` shape and PLAN-05
  may rename its `slug` field. PLAN-02 (WS-01) must land first.
- PLAN-05 also collides with WS-04's PLAN-06 (`_orchestrator_inbox.py`,
  `tools-epic-surface-partition/**`) and PLAN-07 (`plan-orchestrator/**`).
- PLAN-04 collides with WS-02's PLAN-03 on `plugin-doctor/references/rule-catalog.md` — see
  WS-02's charter note; sequence rather than parallelize.
