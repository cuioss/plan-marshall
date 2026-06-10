# Model Levels — Level → Primitive Binding

> Single source of truth for the ordinal level → `(model, effort)` primitive binding consumed by the variant generator and by anyone reading the schema.

## Overview

The variant emission system ([`ext-point-dynamic-level-executor`](../../extension-api/standards/ext-point-dynamic-level-executor.md)) uses a fixed seven-tier ordinal scale to select model + effort combinations per role. Authors configure roles by level keyword (e.g., `plan.phase-3-outline.effort.research = "level-7"`); the build target translates levels into concrete `(model, effort)` primitives via the table below.

The level palette is intentionally small and ordinal — `level-1 → level-2 → level-3 → level-4 → level-5 → level-6 → level-7` represents increasing capability and cost. The `inherit` sentinel is the only non-ordinal value; it instructs the dispatch site to use the canonical no-suffix variant (which inherits the parent session's model).

## Level Table

| Level | Model | Effort | Notes |
|-------|-------|--------|-------|
| `level-1` | `haiku` | (omitted) | Haiku does not accept the `effort` field; build target omits it on emitted variants. |
| `level-2` | `sonnet` | `medium` | Default Sonnet effort. |
| `level-3` | `sonnet` | `high` | High-effort Sonnet — Sonnet's top tier. |
| `level-4` | `opus` | `medium` | Opus with medium effort — fills the Sonnet-high → Opus-high cost/quality gap for tasks that need Opus-class reasoning but not maximum thinking. |
| `level-5` | `opus` | `high` | High-effort Opus — Opus's standard top tier. |
| `level-6` | `opus` | `xhigh` | Extra-high-effort Opus. Alias-capability-gated: build target refuses emission when the resolved Opus alias does not accept `effort: xhigh`. |
| `level-7` | `fable` | `max` | The absolute capability ceiling. Alias-capability-gated: build target refuses emission when the resolved alias does not accept `effort: max`. |
| `inherit` | (unset) | (unset) | Sentinel: dispatch the canonical no-suffix variant; runtime inherits the parent session's model. |

The model column lists **aliases** (`fable`, `opus`, `sonnet`, `haiku`), not version-pinned IDs. See [Aliases, not IDs](#aliases-not-ids) below for rationale.

## Aliases, not IDs

The level table maps to model **aliases** (`fable`, `opus`, `sonnet`, `haiku`) rather than version-pinned IDs (e.g., `claude-opus-4-8`). Rationale:

- **Resilience to model rotation**: code.claude.com rotates the alias targets at the runtime; pinning to an ID in the schema would force a marketplace-wide edit on every model release.
- **User override compatibility**: the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable accepts aliases and overrides the variant's pinned model at session start. Authors authoring against aliases get the same override semantics users expect.
- **Single point of mapping**: the alias → ID resolution lives in `marketplace/targets/opencode/mapping.json` (`model_map`) and is reused by the Claude target for the alias-capability guard. Adding a new model means editing one file.

The only place pinned IDs are written is the build-time guard for the alias-capability-gated levels (`level-6`, `level-7`): the mapping file flags whether the resolved ID accepts the requested effort. Authors and users never see the IDs.

## The Alias-Capability Guard

The two top tiers resolve to alias-capability-gated efforts — `level-6` resolves to `(opus, xhigh)` and `level-7` resolves to `(fable, max)`. The `xhigh` and `max` effort values are accepted only by specific aliases. When a user configures a role to one of these levels AND the resolved alias does not accept the level's effort, the build target:

1. **Refuses to emit** the `{name}-level-6.md` / `{name}-level-7.md` variant.
2. **Emits a build warning** naming the canonical, the requested level, and the missing capability.
3. **Continues building** the other variants — the missing variant is a per-agent / per-level skip, not a fatal build error.

Dispatch sites that resolve to a missing variant fall back to the canonical (`inherit`) at runtime, so the user gets a degraded but functional dispatch instead of a runtime error. The decision log records the fallback for auditability.

## Default Resolution Order

The resolver (`manage-config effort read --role <name>`) walks this order:

1. `models.roles.<role>` — explicit per-role override.
2. `effort` — plan-wide default (when set).
3. `inherit` — implicit fallback when neither is configured.

The resolver returns a single level keyword. Dispatch sites compute the agent target as:

- `inherit` or empty → canonical no-suffix variant: `Task: {bundle}:{base}`.
- any other level → variant: `Task: {bundle}:{base}-{level}`.

Use `manage-config effort resolve-target --role <name>` for a single helper invocation that returns the variant target name directly.

## Validation Rules

The resolver and the wizard both enforce:

| Rule | Failure Mode |
|------|--------------|
| Configured value is one of `level-1`, `level-2`, `level-3`, `level-4`, `level-5`, `level-6`, `level-7`, `inherit` | Hard error on read; refused at wizard save. |
| `level-6` / `level-7` resolves but the resolved alias lacks the level's effort support (`xhigh` / `max`) | Build-time warning + per-level skip; runtime falls back to canonical. |
| Role key is registered in [`effort-roles.md`](effort-roles.md) | Warning (not error): unknown roles resolve to `effort` / `inherit` so the registry can rename without breaking saved configs. |

## Cross-References

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Variant emission contract — how levels are consumed at build time. |
| [`effort-roles.md`](effort-roles.md) | Role registry — which dispatch sites consume which roles. |
| [`effort-variants.md`](effort-variants.md) | User-facing centralised doc — how to configure `models.roles.<name>`. |
| `marketplace/targets/opencode/mapping.json` | `model_map` — alias → ID resolution and effort-support flags. |
