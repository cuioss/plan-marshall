# Pin Provisioning — Steward Surface and Map Contract

> Standards doc naming the steward surface that owns per-level model configuration and the machine-local map contract it reads. Additive to the deterministic steward model; no behavioral surface changed.

## Owning Surface

The steward surface owning per-level model configuration is a Main Menu option on Page 2, sibling to Effort, not `apply-preset`.

- **Location**: Main Menu Page 2, alongside option 4 Effort. The option loads the pin-materialization flow.
- **Why not `apply-preset`**: `apply-preset` completely overwrites the per-phase effort configuration with the preset payload. Pin materialization tunes per-level model bindings without replacing the resolved levels, so it cannot ride the overwrite contract.
- **Precedent**: the wizard-flow seed-then-tune split. Init seeds per-phase `effort` keys; the Effort submenu tunes them afterwards. Pin setup follows the same shape: resolution seeds levels, the pin step tunes the model each level provisions.
- **Step shape**: a deterministic steward step that reads the machine-local map, resolves the level through `manage-config effort`, applies the pin through the harness provisioning seam, and verifies the `inherit` fallback. Operator flow lives in `references/menu-pins.md`; script logic lives in `scripts/effort_pins.py`.

## Map Read and Write Contract

The step reads the machine-local effort ladder at `.plan/local/effort-ladder.json` (or legacy `effort-pins.json`). The map is never version-controlled and never lives in project-shared configuration.

- **Location**: `.plan/local/effort-ladder.json` (resolved main-anchored via `marketplace_paths.resolve_main_anchored_path`).
- **Schema**: Option A multi-target schema (`targets.<target_name>.<level>`), with legacy PLAN-01 (`pins.<level>`) fallback. Each level entry specifies `model` and `effort` coordinates.
- **Entry kinds**: Both two-axis coordinates (`{"model": ..., "effort": ...}`) and legacy kinds (`local`, `provider`) are supported.
- **Writes & Seeding**: Running `/marshall-steward` seeds built-in default ladders for Antigravity (Option 1), Claude (canonical), and OpenCode (inherit). Users can edit `.plan/local/effort-ladder.json` directly to adjust model and effort mappings without changing git-controlled files.

## Inherit Preservation and Never-Escalate Guard

Resolution order is unchanged. The resolver walks the target-neutral chain to a single level keyword, and the provisioning seam consults the map for that exact level afterwards.

- **Unpinned level**: preserves the `inherit` fallback. A miss, or a resolved `inherit`, dispatches on the session model. Inherit-only remains the behavior everywhere the map is silent.
- **Narrow scope**: a map entry serves only its own level, never a neighboring one.
- **Never-escalate guard per ADR-021**: a provisioned model never exceeds the capability of the resolved rung. Provisioning may satisfy a level more cheaply or more locally, but it never silently upgrades the dispatch beyond what the resolved level requested. The seam enforces the guard; this doc states the requirement.

## Delegation Seam

Effort-level reads route through the existing `manage-config effort` verbs; per-level model pins are NOT persisted through them. The pin step adds no parallel resolver and no parallel writer.

- Read the resolved level through the standard effort resolution before consulting the map.
- Do NOT persist per-level pins through the standard effort write path — `effort set` validates `--level` against `ALLOWED_LEVELS` and cannot persist model references. Hand each emitted `level=model` pair to the harness provisioning seam instead: the PLAN-01 post-resolve slot per ADR-021 (`doc/adr/021-machine-local-effort-to-model-map-and-resolve-chain-slot.adoc`) and `plan-marshall/standards/effort-variants.md` § Local-Map Provisioning Slot, which consults the map for the exact resolved level after resolution. Project-shared configuration carries no new key for this hand-off.
- The Claude target fixed alias-palette flow is untouched. Pin materialization targets open-model-set harnesses only; the Claude build-time guard and alias-capability behavior are never modified.

## Resolution and Provisioning Grounding

The resolution-order clause is grounded in `plan-marshall/standards/effort-variants.md` and the level-to-primitive binding in `plan-marshall/standards/effort-levels.md`. Both docs are read-only context for this standard and are not restated here beyond what the sections above need.

- Levels are the ordinal palette plus the `inherit` sentinel.
- The five-step order ends at a level; what a provisioning target does with that level afterwards is the post-resolve decision governed by ADR-021.
- Local provisioning never alters the rungs themselves.

## Follow-Up

ADR-021 cites `doc/concepts/extension-architecture.adoc` as the extension-architecture home of the target-local file-plus-manage-skill definition. That definition is recorded here as a follow-up, not silently assumed: the steward-side implementation in this repository is locally verifiable, and conformance of repeated target-local shapes to the extension-architecture definition is tracked outside this standard.

## Cross-References

| Document | Content |
|----------|---------|
| `plan-marshall/standards/effort-levels.md` | Level-to-primitive binding and alias-capability guard |
| `plan-marshall/standards/effort-variants.md` | Resolver contract and resolution order |
| `standards/effort-menu.md` | Wizard preset-picker UX contract this step sits beside |
| `references/menu-pins.md` | Operator-facing pin flow |
| `scripts/effort_pins.py` | Deterministic pin-materialization script |
| `doc/adr/021-machine-local-effort-to-model-map-and-resolve-chain-slot.adoc` | Provisioning slot, entry-kind discriminator, never-escalate rule |
