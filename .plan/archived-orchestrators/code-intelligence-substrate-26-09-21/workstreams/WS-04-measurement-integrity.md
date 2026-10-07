# WS-04: Measurement Integrity

epic: code-intelligence-substrate

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-measurement-integrity.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The second half of the epic's own discriminator: **how the system counts**. Where WS-01 through
WS-03 fix what the system can find out, this workstream fixes the integrity of what it measures
about the codebase and about its own runs — footprint derivation, evidence emission, and cost
accounting. It closes when a measurement is either correct or explicitly reported as unmeasured,
never silently zero.

All five plans here are **inherited from `truthful-signals`** (2026-07-29 operator decision) and
predate the tier architecture. They remain valid as written; the tier model reorders their priority
relative to the new substrate work but does not reshape their content.

## Scope

- **In scope**: measurement taken outside the window in which the measurand exists; structural zeros
  summed as measurements; dispatch-evidence emission; aggregate cost against a per-call ceiling;
  provenance filtering of chat signals.
- **Out of scope**: the substrate's knowledge surfaces (WS-01 through WS-03); planning-phase detector
  and derivation integrity (WS-05).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-120-finalize-dispatch-evidence-is-missing | staged | ⛔ Run BEFORE PLAN-121 — PLAN-121 cannot measure its own divergence while the `shape_violation` audit is vacuous |
| PLAN-121-finalize-dispatch-manifest-observability | staged | Step-contract seam; carries `total_tokens=0` where the truth is *unmeasured* |
| PLAN-122-footprint-read-outside-its-window | staged | 6D at the split guard; archetype at n=3 |
| PLAN-123-chat-signal-provenance-filter-under-inclusive | staged | Volume-read-as-coverage instance |
| PLAN-124-aggregate-cost-invisible-to-per-call-ceiling | staged | Most HYPOTHESIS-heavy inherited spec; co-design with `truthful-signals` PLAN-99 |

## Sequencing and Surface Notes

- ⛔ **PLAN-120 → PLAN-121 is a hard order**, and they are a deliberate same-bundle split that must
  NEVER be paired.
- ⛔ **PLAN-122 collides with PLAN-120/PLAN-121** on `manage-execution-manifest` and with **PLAN-123**
  on `plan-retrospective`. It is the pinch point of this workstream.
- ⚠ **PLAN-124 must be co-designed with `truthful-signals` PLAN-99**, which stays in that epic. Only
  PLAN-99's *findings* are inputs here.
- ⚠ **STANDING CROSS-EPIC OBLIGATION**: every plan in this workstream touches a surface
  (`manage-execution-manifest`, `plan-retrospective`) that `truthful-signals` also stages against.
  Per-epic disjointness cannot see across the boundary — check BOTH queues before emitting any of
  these.
