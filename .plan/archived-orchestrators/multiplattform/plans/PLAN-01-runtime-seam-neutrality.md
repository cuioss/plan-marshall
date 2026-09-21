# PLAN-01: Runtime seam neutrality

epic: multiplattform
workstream: WS-01

> **HISTORICAL SPEC — this plan has LANDED.** It shipped in the standalone
> `doc/plans/multiplattform/` lane before this ledger existed, so it was never staged from this
> template. This file exists so the queue row has a spec and the corpus reconciles in both
> directions; it is a record, not a brief, and it MUST NOT be emitted.
>
> - Original plan: `archive/010-runtime-seam-neutrality/plan.md`
> - Run report: `archive/010-runtime-seam-neutrality/report-01.md`
> - Landing analysis (ground-truth verified at HEAD `2cd1a19c`): `landings/PLAN-01.md`

## Objective

Make the `Runtime` contract target-opaque and register targets in one place, so a third-target
implementer can read `runtime_base.py` alone and implement or decline every operation.

## Deliverables

1. D1 — Target-opaque `project install-hook` (ABC carries no hook-event names, no `CLAUDE_CODE_*`, no settings path; `overwrite` is a target-defined key set with reject-not-ignore).
2. D2 — Target-neutral ABC docstrings (zero `On Claude` / `On OpenCode` in `runtime_base.py`).
3. D3 — Registration consolidated behind `_DEFAULT_TARGET` / `_REGISTRY` / `_TARGET_BOOTSTRAP_LIBS` in one adjacent block, with a lockstep test.
4. D4 — Parameterized OpenCode subagent dispatch (no hardcoded `execution-context-level-3`).

## Claim Labels

- OBSERVED: all four deliverables landed as specified — re-derived at HEAD `2cd1a19c` from `runtime_base.py`, `platform_runtime.py`, `opencode_runtime.py`, `_claude_runtime_impl.py`, `marketplace_paths.py`, and `test_target_registration_lockstep.py`. See `landings/PLAN-01.md` for the per-deliverable evidence.
- OBSERVED: the `Runtime` ABC carries 24 `@abstractmethod` operations — re-derived by count at HEAD.
- OBSERVED: the plan's stated **Goal** is broader than D2's completion criteria; four operations still document no way to decline — read at `runtime_base.py` lines 155–157, 253–256, 277–282, 935–937. This gap is owned by PLAN-09, not by this record.

## Expected Surface

Historical. The surface actually touched is enumerated in `landings/PLAN-01.md`; it is recorded here
only so a disjointness check against a live plan can read it.

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-healthcheck.md`
- OBSERVED: `test/plan-marshall/platform-runtime/**`, `test/plan-marshall/script-shared/**`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-03 (both edited `claude_runtime.py` / `_claude_runtime_impl.py`); they ran sequentially, never together
- Adjacent to: `marketplace/targets/**` — untouched by this plan (WS-02's surface)

## Hand-Off Command

⛔ None. This plan has landed; there is no command to emit.

## Write-Boundary

Not applicable — historical record.
