# WS-01: Local-map schema and resolve-chain slot

epic: model-provisioning

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the machine-local effort-to-model map schema (with the local vs provider-routed entry-kind discriminator) and its settled slot in the effort resolve chain. Outcome that closes it: a schema decision plus a resolve-seam contract where inherit-only remains the fallback and the local map re-enables per-level pins on top — no behavior change lands here, only the settled decision the steward step builds on.

## Scope

- In scope: local-map schema shape, entry-kind discriminator, resolve-chain slot decision, narrow-but-never-escalate posture statement, fallback semantics (inherit stays).
- Out of scope: steward-step implementation (WS-02), OpenCode emitter changes (WS-02), live-client verification (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-schema-resolve-slot | staged | Local-map schema decision + resolve-chain slot contract |

## Sequencing and Surface Notes

- PLAN-01 lands first; WS-02 plans depend on its settled schema and slot.
- Surface is docs/schema plus the resolver contract; no overlap with WS-02 emit surfaces (emitter + wizard) or WS-03 verification scripts.
