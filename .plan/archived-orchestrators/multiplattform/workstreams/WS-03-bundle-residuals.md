# WS-03: No bundle file states a Claude fact as a universal one

epic: multiplattform

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-bundle-residuals.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the Claude couplings that live in the marketplace bundles themselves — literals in general
scripts, runtime facts asserted as universal in prose, duplicated single-source tables, and emitted
command forms. The workstream closes when every Claude-specific statement in a bundle is either
routed through a runtime operation, sourced from its single source, or explicitly declared as
Claude-target material — and the coupling inventory's §B and §C sections are empty or hold only
recorded, justified exceptions.

## Scope

- **In scope:** `marketplace/bundles/**` scripts and prose outside `platform-runtime` and outside `marketplace/targets` — the plan-marshall bundle's own surfaces, the `pm-plugin-development` authoring toolchain, and the cross-bundle assistant-naming prose; plus their `test/` subtrees.
- **Out of scope:** the runtime seam's own scripts and contract (WS-01) — a plan here that needs a runtime-op addition records it and makes it minimally, never absorbs the seam; the build-target machinery (WS-02); `platform-runtime/SKILL.md`'s op table, which WS-01 PLAN-09 owns.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-claude-literal-residuals | landed | Permission grammar and layout render only in the runtime, across five named clusters. PR #1319. |
| PLAN-06-authoring-surface-target-awareness | staged | The `pm-plugin-development` authoring surface is target-aware and rule-pack-declared. |
| PLAN-07-runtime-fact-prose-and-single-sources | staged | The plan-marshall bundle states runtime facts through the runtime, and single sources stay single. |
| PLAN-10-layout-and-executor-residuals | staged | The unclaimed §B/§C layout, executor, constant, and IDE-launch couplings no other plan reaches. |
| PLAN-12-cross-bundle-assistant-prose | staged | "Claude as THE assistant" prose outside the plan-marshall bundle, the `/plan-marshall` emission sites, and the metrics doc vocabulary. |
| PLAN-13-chat-signal-transcript-boundary | staged | `plan-retrospective`'s raw-transcript-format recognition moves behind a runtime consumption boundary, mirroring the metrics-normalization precedent. |

## Sequencing and Surface Notes

- **PLAN-06 and PLAN-07 must not run together** — both conditionally touch `platform-runtime/standards/contract.md` when their runtime queries need a schema addition. Either order.
- PLAN-06 runs after PLAN-01 (landed): its D3 default-target fix consumes the single source PLAN-01 established.
- PLAN-07 runs after PLAN-01 and PLAN-03 (both landed): it shares the plan-marshall bundle's permission and platform-runtime surfaces with them.
- **PLAN-10 collides with PLAN-07** on `script-shared/scripts/marketplace_paths.py` — PLAN-07's D1 routes `get_base_path`'s `global`/`project` scopes, PLAN-10 closes the fallback-composer constants in the same file. Sequence PLAN-07 first; PLAN-10 then closes what remains and re-derives rather than assuming.
- **PLAN-12 collides with PLAN-05** (WS-02) across `pm-documents`, `pm-dev-frontend`, `pm-requirements`. Sequence PLAN-12 after PLAN-05.
- PLAN-13 is surface-disjoint from every other plan in the epic (`plan-retrospective/scripts/**` alone) and is a good concurrency partner for any WS-01 or WS-02 plan.
- **Standing constraint from the ingested epic README, and it still binds:** a plan never edits another plan's surface, even for an obvious adjacent fix — the neighbour may be running. Record the finding in the report instead. Two plans discovering a shared file this charter calls disjoint is a partition defect: halt and report it.
