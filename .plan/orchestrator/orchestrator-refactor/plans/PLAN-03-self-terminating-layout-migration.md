# PLAN-03: A layout migration that terminates itself

epic: orchestrator-refactor
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-03-self-terminating-layout-migration.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Give this codebase a REUSABLE, self-terminating migration mechanism: a read against a
retired address resolves transparently to its successor, the redirect carries its own expiry,
and a scheduled sweep reports — and on `--apply` removes — every redirect whose expiry
condition has fired. The orchestrator store move (PLAN-01) is its first consumer, not its
only one. The convention half of this already exists (the `SHIM(A)`/`SHIM(B)` marker
convention, shipped) and MUST be extended rather than duplicated. What does not exist is
anything that ever fires.

## Deliverables

1. **D0 — GATE: derive the marked-shim population first-party.** Do not carry the figure 18
   forward as given; re-derive it, publish the method, and classify each site A or B.
2. **D1 — the expiry grammar**, as an ADDITIVE extension of the existing three fields. A
   machine-evaluable trigger beside the existing prose `shim-remove-when`, not instead of it —
   the honest long-horizon prose trigger the convention already blesses must stay expressible.
3. **D2 — the sweep**: dry-run by default, `--apply` to act, a report that names for every
   retained redirect the FIRST rule that kept it and for every removal the trigger that fired,
   with `knob_source` annotated and an `empty_population` state that says which zero it is.
4. **D3 — the redirect primitive at the shared resolver**, so a retired address resolves to
   its successor once, for every caller, per ADR-016.
5. **D4 — the retention knob** in `marshal.json` `system.retention`, alongside the eight that
   are already there.
6. **D5 — an ADR**, because the tree has none governing this and the next migration will need
   the decision rather than this plan's code.
7. **D6 — the orchestrator store migration as the first consumer**, marked with the new
   grammar, proving the mechanism end to end.

## Non-Goals

- No retrospective marking sweep over the existing 18 sites beyond D0's classification.
- This plan does not decide whether the orchestrator move gets a shim at all — that is the
  four-condition checklist's call, taken at outline.

## Claim Labels

- OBSERVED — `pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`
  (100 lines) defines `SHIM(A)` / `SHIM(B)` plus three required fields — `shim-owner`,
  `shim-floor`, `shim-remove-when` — with an explicit non-shim exclusion list and a single
  discriminator question. Shipped via PLAN-TRUTH-003, PR #1153.
- OBSERVED — `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py`
  (520 lines) emits `shim_marker_malformed` and `shim_unmarked` over a derived population
  (every `*.py` under `marketplace_root/*/skills/*/scripts/`), publishing `population_size` and
  an `empty_population` finding.
- OBSERVED — that analyzer validates only the marker's PRESENCE and WELL-FORMEDNESS. Nothing
  in the tree evaluates `shim-remove-when`; there is no expiry sweep and no removal task. This
  is the gap this plan fills.
- OBSERVED — 18 source files carried `SHIM` markers at research time, so the sweep has a real
  population from day one and is not a one-off wrapper around this epic's own migration.
- OBSERVED — `phase-3-outline/standards/outline-workflow-detail.md:809-831` already decides
  WHETHER to shim, via a four-condition checklist and a two-row decision table, and the
  convention (lines 95-99) names itself the mechanized form of that table's removal window.
- OBSERVED — the reusable expiry shape exists twice already: `manage-lessons` `supersede` →
  `[SUPERSEDED]` redirect stub + permanent `.tombstones/{id}.json`, pruned by
  `cleanup-superseded` on a `marshal.json`-driven window with three report buckets
  (`removed` / `already_removed` / `skipped_no_tombstone`, the last refusing to act when the
  audit record is missing); and `marshall-steward/scripts/cache_retention.py`, a union-keep
  sweep with `marshal.json`-resolved knobs, an annotated `knob_source`, dry-run-by-default plus
  `--apply`, and a report naming the FIRST keep-rule that fired for every retained item.
- OBSERVED — `.orphaned_at` (the plugin-cache retention marker) is NOT ours. `cache_retention.py`'s
  docstring states Claude Code's own plugin GC is its sole producer, that it is advisory only
  here, and that it is NEVER consulted as a keep-or-delete oracle. Do not model anything on it.
- OBSERVED — no ADR in `doc/adr/001..022` owns deprecation, migration, sunset, versioned
  removal, or shim. A keyword scan hits only ADR-004/005/009/010/011 incidentally.
- OBSERVED — the only large-rename precedent in this repo is big-bang with no shim: commit
  `36bc12362` / PR #18 absorbed `pm-workflow` into `plan-marshall` in one commit, and a
  content search for `pm-workflow` returns zero hits across the inventoried tree today.
- HYPOTHESIS — a redirect at the shared resolver (ADR-016) is sufficient and no call site needs
  a shim of its own; confirm/refute at `marketplace_paths.py` § `resolve_main_anchored_path`
  and `file_ops.py` § `get_store_dir` against the enumerated call sites (verify-at-outline).
- HYPOTHESIS — the expiry trigger should be release-count-based (a `marshal.json`
  `system.retention` knob, mirroring `plugin_cache_keep_versions`) rather than date-based,
  because `system.provisioned_version` already gives a monotone anchor; confirm/refute at
  `marshall-steward/scripts/cache_retention.py` § `resolve_knobs` / `read_provisioned_version`
  (verify-at-outline).
- Verify-first clause: the sweep MUST NOT remove a redirect on marker-absence. Absence of a
  marker is not evidence the shim is dead — that inversion is exactly the archetype
  PLAN-TRUTH-003 warned against inside its own fix, and `cleanup-superseded`'s
  `skipped_no_tombstone[]` bucket is the shape that refuses it. Verify this refusal is actually
  implemented, not merely intended, before this plan is treated as done.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py`
- OBSERVED: `doc/adr/`
- OBSERVED: `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py`
- OBSERVED: `test/plan-marshall/marshall-steward/test_cache_retention.py`

## Dependencies and Sequencing

- Depends on: PLAN-01 (D6 consumes PLAN-01's landed resolver tier; both touch
  `marketplace_paths.py` — never run concurrently).
- Overlaps with: PLAN-04 (`plugin-doctor/references/rule-catalog.md` — not caught by the
  automated disjointness matcher; sequence rather than parallelize, see WS-02's charter).
- Adjacent to: PLAN-02 and PLAN-06 — no declared surface overlap with either; the one clean
  disjoint pair identified in this epic's corpus is PLAN-03/PLAN-06.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/orchestrator-refactor/plans/PLAN-03-self-terminating-layout-migration.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, across two
bundles. It creates and edits NO file under `.plan/local/orchestrator/` (or the migrated
tracked address, once PLAN-01 lands) other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism are
stated in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
