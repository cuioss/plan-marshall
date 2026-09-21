# PLAN-02: Steward step materializing per-level pins

epic: model-provisioning
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Build the dedicated OpenCode marshall-steward step that materializes per-level pins from the machine-local effort-to-model map (PLAN-01's schema). It covers both entry kinds — local models and provider-routed configs such as Zen/Go — preserves inherit as the fallback when no pin exists, and answers the operator's question directly: this is the analysis and implementation of the steward extension for model configuration. Scope: open-model-set harnesses only (opencode et al) — the Claude target keeps its fixed alias-palette flow and gets no pin-selection UI.

## Deliverables

1. Steward extension analysis: which steward surface owns model configuration (wizard/menu option, step shape) and how it reads/writes the local map — scoped to open-model-set harnesses (opencode et al); Claude target explicitly out of scope.
2. Steward step implementation: per-level pin materialization from the local map for both entry kinds, with inherit fallback when unpinned.
3. Wizard/menu wiring: operator-facing flow to inspect and set per-level pins without hand-editing JSON.
4. Tests for pin materialization including the unpinned-falls-back-to-inherit case.

## Claim Labels

- OBSERVED: The steward exposes wizard and menu flows with delegated scripts and a dedicated Effort submenu that applies presets via manage-config — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` § `Interactive Menu`
- OBSERVED: The Effort submenu is a preset-picker delegating to manage-config effort apply-preset, with per-role payloads from the EffortPresets constant-class — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/effort-menu.md` § `Workflow`
- OBSERVED: Named presets (economic/balanced/high-end) carry per-phase payloads with summed-level spreads 30/36/41 — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` § `EffortPresets`
- OBSERVED: Project and orchestrator defaults (including the empty orchestrator effort block that falls through to plan.effort) are seeded in config defaults — read at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` § `DEFAULT_ORCHESTRATOR`
- HYPOTHESIS: The per-level pin materialization belongs as a steward submenu/step sibling to the Effort submenu rather than inside apply-preset — confirm/refute at `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md` § `wizard steps` (verify-at-outline)
  - verdict: corroborated | checked_at: fb8aadc9 | by: model-provisioning/cleanup | rescoped: n/a | evidence: effort-menu.md still a single preset-picker delegating to apply-preset with overwrite semantics and no per-role editing; a pin-materialization step mirrors that submenu shape rather than entering apply-preset
- Verify-first clause: The consuming outline phase must settle the HYPOTHESIS against the steward implementing source (wizard/menu structure) before scoping the step — refutation re-scopes the step placement.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` — wizard/menu wiring surface
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/effort-menu.md` — effort submenu contract to extend or mirror
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — defaults seeding surface
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` — preset payload surface (adjacent, not rewritten)

## Dependencies and Sequencing

- Depends on: PLAN-01-schema-resolve-slot (schema + slot contract)
- Overlaps with: none (PLAN-03 consumes the pin shape produced here; sequenced after)
- Adjacent to: targets/opencode emitter surface (PLAN-03, untouched here)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/model-provisioning/plans/PLAN-02-steward-pin-materialization.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
