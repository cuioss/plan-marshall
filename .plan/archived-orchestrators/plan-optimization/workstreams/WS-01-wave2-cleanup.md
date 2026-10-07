# WS-01: Wave-2 Cleanup

epic: plan-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-wave2-cleanup.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Land the surface-disjoint correctness and cost defects that the wave-1 landings
(#906→#922) surfaced but did not fix. The core token-optimization roadmap and the P1–P9/SS
aggregated queue have already shipped; this workstream is the residual cleanup distilled from
their open defects (HANDOVER §4 "Startable now"). It closes when all four staged plans have
landed and their absorbed defects are retired from HANDOVER §5.

## Scope

- In scope: the four startable plans on their four disjoint surfaces — execution-manifest
  compose (`manage-execution-manifest.py`, `_manifest_rules.py`, phase-4 compose); phase-6
  finalize step scripts + bodies; `execution-context` dispatch topology; phase-6 SKILL/config
  prose + persona standards (docs contract). Each plan carries an `Absorbs`-as-contract list.
- Out of scope: parked/deferred follow-ups (WS-02); the plan-server epic's worktree-resolution
  hand-off items (tracked in `../plan-server/00-README.md`); anything already shipped in wave 1.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-manifest-compose-gaps | ✅ shipped (PR #926) | D1 wired `request_aspect` self-read; D2 found #897 gap already-closed + locked with regression test |
| PLAN-02-finalize-step-integrity | ✅ shipped (PR #927) | 4/4 deliverables; D4 added CWE-59 hardening; dogfooded own D1/D2 fixes live |
| PLAN-03-leaf-validator-yield | ✅ resolved (no-op audit) | Premise already shipped (#920/#493/q-gate); audit → lesson `2026-07-18-10-001`; saved ~1M tokens |
| PLAN-04-docs-contract-consistency | ✅ shipped (PR #930) | P7 shipped: `*_without_asking` truth-table, `auto_merge_after_ci`→`final_merge_without_asking`, Principle 8 diagnosis standard. Rebased over #929+#931. **Last WS-01 plan → WS-01 COMPLETE** |

## Sequencing and Surface Notes

- **Parallelism (HANDOVER §4):** MANIFEST (PLAN-01) ∥ EXEC-CONTEXT (PLAN-03) ∥ {FINALIZE (PLAN-02)
  or DOCS (PLAN-04)} run fully concurrently — three disjoint surfaces. Up to 3 concurrent cleanly.
- **PLAN-02 and PLAN-04 share the phase-6 surface** (FINALIZE edits step scripts, DOCS edits SKILL
  prose — small overlap): run them serially, or accept one rebase-revalidation for the second
  finisher. They are the SAME parallel group.
- No hard depends-on ordering among the four; disjointness, not dependency, governs pairing.
- **Absorbs-as-contract (2026-07-17):** each plan's `Absorbs` list is a commitment. An outline
  that drops an absorbed item must say so and re-home it — never silently (this is what created
  the P1/P2/P6 orphan pile).
