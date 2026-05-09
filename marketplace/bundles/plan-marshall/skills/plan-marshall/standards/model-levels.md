# Model Levels — Level → Primitive Binding

> Single source of truth for the ordinal level → `(model, effort)` primitive binding consumed by the variant generator and by anyone reading the schema.

## Overview

The variant emission system ([`ext-point-dynamic-level-executor`](../../extension-api/standards/ext-point-dynamic-level-executor.md)) uses a fixed five-tier ordinal scale to select model + effort combinations per role. Authors configure roles by level keyword (e.g., `models.roles.q_gate_validation = "high"`); the build target translates levels into concrete `(model, effort)` primitives via the table below.

The level palette is intentionally small and ordinal — `low → medium → high → xhigh → xxhigh` represents increasing capability and cost. The `inherit` sentinel is the only non-ordinal value; it instructs the dispatch site to use the canonical no-suffix variant (which inherits the parent session's model).

## Level Table

| Level | Model | Effort | Notes |
|-------|-------|--------|-------|
| `low` | `haiku` | (omitted) | Haiku does not accept the `effort` field; build target omits it on emitted variants. |
| `medium` | `sonnet` | `medium` | Default Sonnet effort. |
| `high` | `sonnet` | `high` | High-effort Sonnet — preferred default for analytical tasks. |
| `xhigh` | `opus` | `high` | Opus with high effort. |
| `xxhigh` | `opus` | `xhigh` | **Opus-4.7-only.** Build-time guard refuses emission when the resolved canonical alias does not accept `effort: xhigh`. |
| `inherit` | (unset) | (unset) | Sentinel: dispatch the canonical no-suffix variant; runtime inherits the parent session's model. |

The model column lists **aliases** (`opus`, `sonnet`, `haiku`), not version-pinned IDs. See [Aliases, not IDs](#aliases-not-ids) below for rationale.

## Aliases, not IDs

The level table maps to model **aliases** (`opus`, `sonnet`, `haiku`) rather than version-pinned IDs (e.g., `claude-opus-4-7`). Rationale:

- **Resilience to model rotation**: code.claude.com rotates the alias targets at the runtime; pinning to an ID in the schema would force a marketplace-wide edit on every model release.
- **User override compatibility**: the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable accepts aliases and overrides the variant's pinned model at session start. Authors authoring against aliases get the same override semantics users expect.
- **Single point of mapping**: the alias → ID resolution lives in `marketplace/targets/opencode/mapping.json` (`model_map`) and is reused by the Claude target for the `xxhigh` model-support guard. Adding a new model means editing one file.

The only place pinned IDs are written is the build-time guard for `xxhigh`: the mapping file flags whether the resolved ID accepts `effort: xhigh`. Authors and users never see the IDs.

## The `xxhigh` Guard

`xxhigh` resolves to `(opus, xhigh)`. The `xhigh` effort value is currently only accepted by Opus 4.7. When a user configures a role to `xxhigh` AND the resolved alias does not accept `xhigh`, the build target:

1. **Refuses to emit** the `{name}-xxhigh.md` variant.
2. **Emits a build warning** naming the canonical, the requested level, and the missing capability.
3. **Continues building** the other variants — the missing variant is a per-agent / per-level skip, not a fatal build error.

Dispatch sites that resolve to a missing variant fall back to the canonical (`inherit`) at runtime, so the user gets a degraded but functional dispatch instead of a runtime error. The decision log records the fallback for auditability.

## The `max` Reservation (Future-Additive)

`max` is reserved as a future-additive option meaning "the highest level the runtime currently supports". It is **not** in the current level palette. The reservation exists so a future model release can introduce a new top tier without forcing every author to re-configure roles — `max` would track the new top tier automatically.

Until `max` is added to the palette, configuring a role to `max` is rejected by both the resolver (`manage-config models read --role`) and the wizard (`marshall-steward` Models submenu). The `xxhigh` tier is the current effective top.

## Default Resolution Order

The resolver (`manage-config models read --role <name>`) walks this order:

1. `models.roles.<role>` — explicit per-role override.
2. `models.default` — plan-wide default (when set).
3. `inherit` — implicit fallback when neither is configured.

The resolver returns a single level keyword. Dispatch sites compute the agent target as:

- `inherit` or empty → canonical no-suffix variant: `Task: {bundle}:{base}`.
- any other level → variant: `Task: {bundle}:{base}-{level}`.

## Validation Rules

The resolver and the wizard both enforce:

| Rule | Failure Mode |
|------|--------------|
| Configured value is one of `low`, `medium`, `high`, `xhigh`, `xxhigh`, `inherit` | Hard error on read; refused at wizard save. |
| `max` is recognized but not yet supported | Hard error: "level `max` reserved; use `xxhigh` for the current top tier". |
| Role key is registered in [`model-roles.md`](model-roles.md) | Warning (not error): unknown roles resolve to `models.default` / `inherit` so the registry can rename without breaking saved configs. |

## Cross-References

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Variant emission contract — how levels are consumed at build time. |
| [`model-roles.md`](model-roles.md) | Role registry — which dispatch sites consume which roles. |
| [`role-variants.md`](role-variants.md) | User-facing centralised doc — how to configure `models.roles.<name>`. |
| `marketplace/targets/opencode/mapping.json` | `model_map` — alias → ID resolution and effort-support flags. |
