# WS-05: Detector and Derivation Integrity

epic: code-intelligence-substrate

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-detector-and-derivation-integrity.md` and is tracked in
> the epic `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Where WS-02 fixes derivation in the *substrate*, this workstream fixes derivation in the *planning
phases and detectors* that consume it: scope derived rather than asserted, detectors whose
population is derived rather than sampled, and gates that can distinguish real evidence from
test-authored evidence. It closes when a planning-phase claim is traceable to something derived, and
no detector's guard is vacuous.

All three plans are **inherited from `truthful-signals`** (2026-07-29 operator decision). The tier
architecture strengthens their rationale: the epic has now found the same "assert instead of derive"
archetype in the substrate itself (`enriched.internal_dependencies` consulted *before* the derivation
fallback), so these are no longer isolated planning-phase defects.

## Scope

- **In scope**: outline/plan scope derivation integrity, auditor detector integrity, and the
  freshness gate's inability to distinguish test-authored evidence.
- **Out of scope**: substrate derivation itself (WS-02); measurement integrity (WS-04).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-125-outline-plan-scope-derivation-integrity | staged | "Derived, not asserted." Archetype at n=7. D1 may split |
| PLAN-126-auditor-detector-integrity | staged | 6D, at the split guard — **do not add to it** |
| PLAN-127-freshness-gate-cannot-distinguish-test-authored-evidence | staged | ⚠ Low pairing compatibility — the test tree collides widely |

## Sequencing and Surface Notes

- ✅ **All three are mutually surface-disjoint** (`phase-3-outline`/`phase-4-plan`/`manage-tasks` ·
  the project-local auditor · the freshness gate and test tree) and MAY run concurrently, subject to
  the epic-wide `parallelization_scope` of 3.
- ⚠ **PLAN-127 pairs badly with almost anything** — the test tree it touches collides widely across
  the repo. Treat it as effectively serialized in practice even though it is nominally disjoint.
- ⚠ **PLAN-126 and PLAN-125 are both AT the six-deliverable split guard.** Neither may absorb
  additional scope; if the tier architecture suggests new work in their area, it becomes a new plan.
- ⚠ **STANDING CROSS-EPIC OBLIGATION**: `phase-3-outline`/`phase-4-plan` and the project-local
  auditor are surfaces `truthful-signals` also stages against. Check BOTH queues before emitting.
- ⭐ **Adjacency worth recording, not acting on**: PLAN-125's "derived not asserted" thesis is the
  same archetype as WS-02's resolver work. They do NOT share a surface and must not be merged, but a
  landing in either should be read as evidence for the other.
