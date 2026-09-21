# WS-02: Steward materialization and emitter re-enable

epic: model-provisioning

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the build side: the dedicated OpenCode marshall-steward step that materializes per-level pins from the local map, and the OpenCode emitter re-enable that writes per-variant model pins (with inherit fallback preserved). Outcome that closes it: steward step shipped plus variants carrying pins from the local map instead of inherit-only.

## Scope

- In scope: steward wizard step, pin materialization, OpenCode variant-emitter and frontmatter transform changes, mapping/model_map handling for local and provider-routed entries.
- Out of scope: schema/slot decision itself (WS-01), live-client verification per entry kind (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-02-steward-pin-materialization | staged | Steward step materializing per-level pins from the local map |
| PLAN-03-emitter-reenable | staged | OpenCode emitter re-enable: per-variant model pins with inherit fallback |

## Sequencing and Surface Notes

- PLAN-02 and PLAN-03 both depend on PLAN-01; PLAN-03 consumes PLAN-02's pin shape (sequenced, not parallel — scope is 1).
- PLAN-02 touches the steward skill surface; PLAN-03 touches the targets/opencode surface — adjacent but distinct.
