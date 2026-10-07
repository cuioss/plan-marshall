# WS-01: Shared Store Substrate

epic: orchestrator-refactor

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-shared-store-substrate.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns aspect 1 of the epic: move the orchestrator ledger's address from
`.plan/local/orchestrator/{name}/` (machine-local, git-ignored) to a shared, git-tracked
`.plan/orchestrator/{name}/`, and restructure the two files that today grow monolithic
(`status.json`, `epic.md`) into self-contained, per-concern files so two sessions on two
machines can mutate the same epic without a shared-file collision. Closes when the ledger
resolves at the new address, no file inside a tree is a whole-epic bottleneck, and the
plan-row status vocabulary matches what every live ledger actually writes.

## Scope

- In scope: the store-path resolver family (`resolve_main_anchored_path`, `get_store_dir`,
  `get_archived_orchestrator_dir`), the `.gitignore` negation, the `kind=orchestrator`
  status.json schema and its per-concern decomposition, the plan-row status vocabulary,
  and the `archive` verb's move mechanism (must become git-aware once the tree is tracked).
- Out of scope: the migration/redirect mechanism that lets the OLD address keep resolving
  for a bounded window (WS-02 owns the mechanism; this workstream may consume it but does
  not build it); any identifier rename (WS-03); orchestrator.py's own module structure
  (WS-04).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-tracked-orchestrator-store-resolver | staged | Move the address only — one resolver tier, one `.gitignore` negation, git-aware `archive`. No shape change, no rename. |
| PLAN-02-ledger-decomposition-and-row-vocabulary | staged | Split status.json/epic.md into per-concern files and settle the plan-row status vocabulary (19% of live rows carry an unexpressible status today). Assumes PLAN-01 has landed. |

## Sequencing and Surface Notes

- PLAN-01 must land before PLAN-02: PLAN-02's Non-Goals explicitly assume the address has
  already moved, and both plans touch `orchestration-model.md` § Directory Layout.
- PLAN-01 also collides with WS-02's PLAN-03 on `script-shared/scripts/marketplace_paths.py`
  (PLAN-03's redirect primitive is added to the same resolver tier PLAN-01 creates) — PLAN-03
  is sequenced after PLAN-01, never concurrent with it.
- PLAN-02 collides with WS-03's PLAN-05 on `manage-status/**` and `orchestrator.py` (both
  touch the `status.json` schema; PLAN-05 may rename the plan-row `slug` field, PLAN-02
  changes its shape) — do not run PLAN-02 and PLAN-05 concurrently.
- PLAN-02 has an unresolved-at-decompose-time overlap with `truthful-signals` PLAN-TRUTH-151
  (staged, declares `orchestration-model.md`) — a sibling-epic collision the disjointness gate
  cannot see across ledgers; check PLAN-TRUTH-151's status before staging PLAN-02's command.
