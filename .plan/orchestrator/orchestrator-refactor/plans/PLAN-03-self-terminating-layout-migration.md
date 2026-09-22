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

> **Re-grounded 2026-09-21: PLAN-01 has LANDED (#1557/#1558/#1561) without a redirect, and
> the gap this plan exists to fill is no longer theoretical — it is now reproduced, live,
> breakage.** `_orchestrator_inbox.py`'s `_SOURCE_ID_RE` hardcodes the NEW
> `.plan/orchestrator/` prefix with no acceptance of the pre-migration
> `.plan/local/orchestrator/` form, so `inbox detect` now returns `unrecognised_id` for every
> plan whose `source_id` was captured before PLAN-01 merged — including PLAN-01's own. See
> Claim Labels for the reproduced evidence and the affected-population risk.

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
   its successor once, for every caller, per ADR-016. ⚠ Re-grounded 2026-09-22: this is
   necessary but NOT sufficient — see the refuted HYPOTHESIS in Claim Labels. A resolver-level
   redirect only reaches call sites that RESOLVE a filesystem path; a call site that MATCHES a
   path-shaped string persisted elsewhere (the `_orchestrator_inbox.py` `_SOURCE_ID_RE`
   pattern is the reproduced instance) is untouched by it and needs its own explicit class in
   this deliverable's design, not a generic redirect assumption.
5. **D4 — the retention knob** in `marshal.json` `system.retention`, alongside the eight that
   are already there.
6. **D5 — an ADR**, because the tree has none governing this and the next migration will need
   the decision rather than this plan's code.
7. **D6 — the orchestrator store migration as the first consumer**, marked with the new
   grammar, proving the mechanism end to end. ⚠ PLAN-01 landed WITHOUT this shim — D6 is now
   a RETROFIT (a redirect added after the fact) rather than a shim built alongside the move,
   and its most urgent instance is the `_SOURCE_ID_RE` detection-seam gap in Claim Labels,
   not only the store resolver `get_store_dir` HYPOTHESIS already covered D3's design against.

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
- ⚠ REFUTED AT HEAD (was HYPOTHESIS) — a redirect at the shared resolver is NOT sufficient on
  two independent grounds, and D3's design must account for both. (1) **Categorical**: the
  reproduced `_orchestrator_inbox.py` `_SOURCE_ID_RE` failure (below) is a regex matching a
  path-shaped STRING persisted in a plan's `request.md` — no filesystem resolution happens at
  that call site at all, so a `get_store_dir`-level redirect literally cannot reach it; some
  call sites need their OWN accommodation by construction, not merely in this one instance.
  (2) **Precedent**: PLAN-01 already landed the orchestrator store's own move WITHOUT any
  redirect, and **ADR-024** (Proposed) formalises that as the decision — "no compatibility
  shim or read-fallback to the retired address is provided because every existing tree is
  relocated in the same change." The mechanism this plan builds must therefore not assume a
  shared-resolver redirect is the general answer; D3 needs an explicit class for
  string-matching call sites, and D6 (the orchestrator move as first consumer) can no longer
  demonstrate "the mechanism end to end" via a redirect, since none was built for it — D6
  stays a retrofit, per the Objective's own re-grounding note above. The four-condition
  shim-or-not checklist this plan already defers to at outline (see Non-Goals) is UNCHANGED
  by this — it still decides case by case; what changes is that "redirect, generically
  sufficient" is no longer an assumption D3 may start from.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: refuted on two grounds: (1) _orchestrator_inbox.py _SOURCE_ID_RE matches a persisted STRING, not a resolved filesystem path, so a resolver-level redirect cannot reach it - reproduced live: inbox detect --source-id with the old prefix still returns unrecognised_id at HEAD; (2) ADR-024 (Proposed) formalises PLAN-01's own no-shim landing as the decision, ruling out a redirect as the general answer. Re-scoped in place: the HYPOTHESIS bullet and D3 now both flag that string-matching call sites need explicit handling, not a generic redirect assumption.
- HYPOTHESIS — the expiry trigger should be release-count-based (a `marshal.json`
  `system.retention` knob, mirroring `plugin_cache_keep_versions`) rather than date-based,
  because `system.provisioned_version` already gives a monotone anchor; confirm/refute at
  `marshall-steward/scripts/cache_retention.py` § `resolve_knobs` / `read_provisioned_version`
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: cache_retention.py carries resolve_knobs/read_provisioned_version/plugin_cache_keep_versions/provisioned_version; _config_defaults.py holds the system.retention knob family; but no expiry grammar exists to evaluate release-count-vs-date against. shim-remove-when has no reader beyond _analyze_shim_marker.py's presence/well-formedness check. Design judgment with no ground truth at HEAD.
- Verify-first clause: the sweep MUST NOT remove a redirect on marker-absence. Absence of a
  marker is not evidence the shim is dead — that inversion is exactly the archetype
  PLAN-TRUTH-003 warned against inside its own fix, and `cleanup-superseded`'s
  `skipped_no_tombstone[]` bucket is the shape that refuses it. Verify this refusal is actually
  implemented, not merely intended, before this plan is treated as done.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: premise holds and remains unimplemented, so it is a live requirement. Precedent shape survives: cleanup-superseded's skipped_no_tombstone[] bucket lives in manage-lessons/_lessons_retention.py + manage-lessons.py, pinned by test_cleanup_superseded.py. No sweep exists to carry the refusal: shim-remove-when now appears across 21 source files (up from recorded 18), _analyze_shim_marker.py the only reader, validating well-formedness only.
- OBSERVED (added 2026-09-21, reproduced first-party by this epic's own `analyze` verb) —
  `_orchestrator_inbox.py`'s `_SOURCE_ID_RE = re.compile(r'^\.plan/orchestrator/(?P<slug>[^/]+)/plans/' + PLAN_ID_SEGMENT + r'[^/]*\.md$')`
  requires the literal `.plan/orchestrator/` prefix. Direct reproduction:
  `inbox detect --source-id ".plan/local/orchestrator/orchestrator-refactor/plans/PLAN-01-tracked-orchestrator-store-resolver.md"`
  (PLAN-01's own actual, correctly-written `source_id`) → `orchestrated: false`,
  `detection: unrecognised_id`. The identical id with only the prefix changed to
  `.plan/orchestrator/...` → `orchestrated: true`. Isolates the cause to the path prefix, NOT
  to the digit-suffix grammar (`PLAN-01-tracked-orchestrator-store-resolver.md` parses fine
  once the prefix matches — the earlier HYPOTHESIS in `PLAN-06` about a naming-grammar cause
  was itself refuted by this test).
- HYPOTHESIS (added 2026-09-21) — other currently-in-flight plans across other epics whose
  `source_id` was captured before PLAN-01's merge (`8c8c7bbf`/`6728b738`) carry the same
  old-prefix form and will hit the identical `unrecognised_id` failure at their own finalize.
  `truthful-signals` PLAN-TRUTH-144 (confirmed `running` as of this epic's own `cleanup`
  pass, 2026-09-21) is a plausible affected instance; confirm/refute by reading its
  `request.md` `source_id` directly once it is reachable (verify-at-outline — it is a
  running plan and must not be touched before then).
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: the mechanism half reproduces (see claim 9), but the named instance PLAN-TRUTH-144 shipped as PR #1560, is gone from the truthful-signals queue (44 rows, no -144), manage-status list reports only the NO_PLAN sentinel - no in-flight plan survives to check. Population is empty, not merely unreached.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py`
- OBSERVED (added by the 2026-09-21 fold): `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `doc/adr/`
- OBSERVED: `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py`
- OBSERVED: `test/plan-marshall/marshall-steward/test_cache_retention.py`
- OBSERVED (added by the 2026-09-21 fold): `test/plan-marshall/plan-orchestrator/**`

## Dependencies and Sequencing

- Depends on: PLAN-01 — **LANDED** 2026-09-21 (#1557/#1558/#1561). D6 consumes its resolver
  tier; both touch `marketplace_paths.py`, now sequential rather than concurrent by
  construction. ⚠ Landed WITHOUT a redirect — D6 is a retrofit, and its most urgent
  sub-target is `_orchestrator_inbox.py`'s detection-seam prefix gap (see Claim Labels), which
  is actively breaking orchestration routing for any plan spanning the cutover right now.
- Overlaps with: PLAN-04 (`plugin-doctor/references/rule-catalog.md` — not caught by the
  automated disjointness matcher; sequence rather than parallelize, see WS-02's charter).
- Adjacent to: PLAN-02 and PLAN-06 — no declared surface overlap with either; the one clean
  disjoint pair identified in this epic's corpus is PLAN-03/PLAN-06.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-03-self-terminating-layout-migration.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, across two
bundles. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism are
stated in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
