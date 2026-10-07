# WS-03: Live-client verification per entry kind

epic: model-provisioning

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the done-proof: live-client verification that each dispatch level resolves to the user's configured model (local model entry kind and provider-config entry kind such as Zen/Go), with the narrow-but-never-escalate posture enforced and verified red-first. Outcome that closes it: per-kind verification evidence plus the posture check.

## Scope

- In scope: live-client verification per entry kind, red-first posture checks, verification evidence and landing criteria.
- Out of scope: schema/slot decision (WS-01), steward/emitter implementation (WS-02).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-04-live-verification | staged | Live-client verification per entry kind, red-first |

## Sequencing and Surface Notes

- Depends on PLAN-02 and PLAN-03 landing first; runs last.
- Verification reads the built surfaces but changes no product surface itself — test/verification scripts only.
