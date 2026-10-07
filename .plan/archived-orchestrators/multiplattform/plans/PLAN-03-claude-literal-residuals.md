# PLAN-03: Claude-literal residuals

epic: multiplattform
workstream: WS-03

> **HISTORICAL SPEC — this plan has LANDED.** It shipped in the standalone
> `doc/plans/multiplattform/` lane before this ledger existed. This file exists so the queue row has
> a spec and the corpus reconciles in both directions; it is a record, not a brief, and it MUST NOT
> be emitted.
>
> - Original plan: `archive/030-claude-literal-residuals/plan.md`
> - Run report: `archive/030-claude-literal-residuals/report-01.md`
> - Landing analysis (ground-truth verified at HEAD `2cd1a19c`, including an independent tree-wide
>   Claude-literal sweep): `landings/PLAN-03.md`

## Objective

Render the Claude permission grammar and the Claude layout only inside the runtime, so the general
scripts that drive permission and layout work exchange normalized values with the runtime instead of
Claude-shaped strings.

## Deliverables

1. D1 — Default permissions render in the runtime.
2. D2 — Settings-path reads delegate to the runtime.
3. D3 — Credential deny rules render in the runtime (via `permission fix --operation protect-path`).
4. D4 — The implementor scan routes through layout resolution.
5. D5 — Display/filter strings stop naming `.claude/`.

## Claim Labels

- OBSERVED: all five deliverables landed; D5 shipped-modified (half was already closed by earlier work, named in the report as finding F22 rather than papered over). Re-derived at HEAD `2cd1a19c`. See `landings/PLAN-03.md`.
- ⛔ OBSERVED: **"zero Claude literals outside the sanctioned homes" was never this plan's landed claim.** The landed claim is narrower — zero literals in five *named clusters*. Every literal found beyond them was registered as open work in the coupling inventory. Independent re-derivation confirms that registry is accurate. A reader must not carry the epic-level slogan onto this plan's record.
- OBSERVED: `permission_common.py` (32–41) and `permission_doctor.py` (27) still carry `from claude_runtime import …` — a direct name import, not a registry route. This is the residue PLAN-08 exists to close, and PLAN-08's framing of it is accurate rather than overstated.
- OBSERVED: report-01's "pinned three rules" prose is stale at HEAD for a reason **external** to this plan — `_default_permission_rules()` now returns two rules, `plan-dir-write` having been retired by the later unrelated commit `2cd1a19c` (#1337). Normal drift, not a landing defect.

## Expected Surface

Historical; recorded for disjointness reads only.

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/_cred_ensure_denied.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`, `_claude_runtime_impl.py`
- OBSERVED: the corresponding `test/` subtrees

## Dependencies and Sequencing

- Depends on: none (ran after PLAN-01 by preference, not by requirement)
- Overlaps with: PLAN-01 and PLAN-08 (all three edit `claude_runtime.py` / `_claude_runtime_impl.py`) — strictly sequential
- Adjacent to: the plugin-doctor analyzers, deliberately untouched — PLAN-06's surface

## Hand-Off Command

⛔ None. This plan has landed.

## Write-Boundary

Not applicable — historical record.
