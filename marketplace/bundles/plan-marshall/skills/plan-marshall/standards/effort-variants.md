# Role Variants — User Guide

> User-facing centralised guide to configuring per-role models for plan-marshall subagents.

## What This Does

By default, every subagent dispatched by plan-marshall inherits the model from the parent Claude Code session (typically Opus). Some workflows benefit from higher capability (verification-feedback triage, retrospective analysis); most don't, costing tokens for no gain. The role-variants system lets you pick a model + effort tier per phase (and per workflow inside a phase), applied automatically at dispatch time.

You configure a small JSON block in `.plan/marshal.json`. The build target emits one variant agent file per (canonical agent × level) combination. Dispatch sites read your configuration and call the right variant by name. End result: the right model runs the right role, no per-dispatch overrides, no manual flag passing.

## The Level Palette

Six ordinal tiers plus a sentinel:

| Level | Model | Effort | When to use |
|-------|-------|--------|-------------|
| `low` | Haiku | (n/a) | Mechanical tasks: log scrubbing, simple lookups, deterministic transforms. |
| `medium` | Sonnet | medium | Default for routine work — most code edits, doc updates. |
| `high` | Sonnet | high | Analytical work: triage, validation, multi-file reasoning. |
| `xhigh` | Opus | medium | Opus reasoning without max thinking — fills the Sonnet-high → Opus-high cost/quality gap. |
| `xxhigh` | Opus | high | High-effort Opus — today's standard Opus top tier. |
| `max` | Opus | xhigh | Top tier (Opus-4.7-only). Research, novel problem decomposition; build-time guard skips emission when the alias does not accept `effort: xhigh`. |
| `inherit` | (parent) | (parent) | Sentinel: dispatch the canonical, inheriting whatever the parent session uses. |

See [`effort-levels.md`](effort-levels.md) for the full level → `(model, effort)` primitive binding, alias rules, and the `max` build-time guard.

## The Role Registry

A **role** is a stable key naming a class of dispatch (e.g., `phase-6-finalize.verification-feedback`, `phase-3-outline`). The registry is phase-scoped (six groups, named after the SKILL.md they identify: `phase-1-init`, `phase-2-refine`, `phase-3-outline`, `phase-4-plan`, `phase-5-execute`, `phase-6-finalize`). The full registry — which sub-keys exist on which phase, which workflow doc each binds to, and the accepted lookup forms — lives in [`effort-roles.md`](effort-roles.md).

## How to Configure

### Option A: The Wizard (Recommended)

Run the `marshall-steward` wizard and pick the **Models** submenu:

```
/marshall-steward
```

The wizard:

- Shows the current per-phase `effort` configuration (or "(not configured — defaults apply)").
- Edits `plan.effort` via prompt — your plan-wide fallback level.
- Walks each phase, letting you set the phase default or override individual workflow sub-keys.
- Refuses invalid levels (e.g., typos) at save time.

### Option B: Edit `marshal.json` Directly

The schema lives at `.plan/marshal.json` under the `plan` key:

```jsonc
{
  "plan": {
    "effort": "medium",
    "phase-3-outline": { "effort": "high" },
    "phase-5-execute": {
      "effort": { "verification-feedback": "high" }
    },
    "phase-6-finalize": {
      "effort": {
        "verification-feedback": "high",
        "post-run-review": "xhigh"
      }
    }
  }
}
```

Resolution order for any role:

1. The deepest explicit sub-key override (e.g. `plan.phase-6-finalize.effort.verification-feedback`).
2. The group's `default` slot when the sub-key is unset or unspecified (`plan.phase-6-finalize.effort.default`).
3. A plain-string value at the phase entry (single-level shorthand applied to every workflow under that phase) — e.g. `"phase-3-outline": { "effort": "high" }`.
4. `plan.effort` — plan-wide default.
5. `inherit` — implicit fallback when nothing else matches.

The per-phase `effort` attributes are **opt-in** — when absent entirely, every subagent inherits the parent session's model. The dispatcher resolves the level at dispatch time via `manage-config effort resolve-target --phase <phase> --role <subkey>`, so no Claude Code restart is required after editing.

### Recommended Starting Configuration

For most workflows, this gets you most of the value at modest cost. The example below mirrors the on-disk shape that `apply-preset --preset balanced` writes after `_expand_phase_effort` — every `KNOWN_ROLES` phase carries an explicit entry so the wizard's deep-equality match recognises the preset:

```jsonc
{
  "plan": {
    "effort": "high",
    "phase-1-init": { "effort": "high" },
    "phase-2-refine": { "effort": "high" },
    "phase-3-outline": { "effort": "xhigh" },
    "phase-4-plan": { "effort": "high" },
    "phase-5-execute": {
      "effort": {
        "default": "xhigh",
        "verification-feedback": "high"
      }
    },
    "phase-6-finalize": {
      "effort": {
        "default": "high",
        "verification-feedback": "high",
        "post-run-review": "xhigh"
      }
    }
  }
}
```

Pre-built profiles cover the same ground:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort apply-preset --preset balanced
```

Available presets: `economic`, `balanced`, `high-end`. See [`effort-roles.md`](effort-roles.md) and `effort_presets.py` for the per-preset role tables.

## What Happens at Dispatch Time

When a dispatch site fires (e.g., phase-5-execute calling `verification-feedback` with `producer=build-runner`):

1. The site calls `manage-config effort resolve-target --phase phase-5-execute --role verification-feedback`.
2. If the level is `inherit` (or the resolver returned `inherit` as the implicit fallback), the target is the **canonical** no-suffix variant: `Task: plan-marshall:execution-context`. The runtime inherits the parent's model.
3. Otherwise, the target is a **variant**: `Task: plan-marshall:execution-context-{level}`. The variant has `model:` and `effort:` baked into its frontmatter, so Claude Code runs the subagent on those exact settings.

The dispatched `execution-context` agent reads the caller-supplied `workflow` (the doc path inside the prompt body) and executes it. One agent + one set of seven emitted variants (canonical + six levels) drives every plan-marshall `Task:` invocation in the marketplace. Variants are emitted at build time into `target/claude/plan-marshall/agents/`, then synced into the plugin cache via `/sync-plugin-cache`.

## Migration Note — `xhigh` / `xxhigh` rebind

Plan-marshall is pre-1.0. The recent palette expansion — inserting `xhigh = opus-medium` and promoting `max` to live — rebinds the existing `xhigh` and `xxhigh` keywords to **weaker** primitives than they previously resolved to:

| Level | Previous binding | New binding |
|-------|------------------|-------------|
| `xhigh` | `opus, high` | `opus, medium` |
| `xxhigh` | `opus, xhigh` | `opus, high` |
| `max` | (reserved — not accepted by resolver) | `opus, xhigh` (Opus-4.7-only) |

There is no auto-migration. **User-side action** for any consumer `marshal.json` that was already opted in to per-role levels:

- If you previously wanted *Opus, high* under `xhigh` → now point at `xxhigh`.
- If you previously wanted *Opus, xhigh* under `xxhigh` → now point at `max`.

Configs that did not opt in to per-role levels (or that only used `low`/`medium`/`high`) are unaffected.

## Troubleshooting

### Symptom: My configured level isn't taking effect

**Check:**

1. Is the role spelled correctly per the hierarchical registry in [`effort-roles.md`](effort-roles.md)? Keys are kebab-case and match the SKILL.md name (`phase-6-finalize.verification-feedback`, not `phase_6.verification_feedback` and not the bare `phase-6-finalize`).
2. Is the level spelled correctly (`high`, not `High` or `hi`)?
3. Is `target/claude/` regenerated? Run the `project:finalize-step-deploy-target` step (or `python3 marketplace/targets/generate.py --target claude --output target/claude`) to refresh emitted variants, then `/sync-plugin-cache` to push them into the plugin cache.

### Symptom: A role configured as `max` is not running on Opus

`max` resolves to `(opus, xhigh)`, which is currently Opus-4.7-only. The build target's guard refuses to emit the `max` variant when the canonical's resolved alias does not accept `effort: xhigh` — the dispatch falls back to the canonical, which inherits the parent's model. Check `.plan/logs/` for the build warning naming the canonical and the missing capability.

### Symptom: Set a level but it's not even visible to the resolver

`CLAUDE_CODE_SUBAGENT_MODEL` is an environment variable that overrides every subagent's pinned model at session start (per code.claude.com). When set, it beats the variant's `model:` declaration — including yours. Unset the env var or override it explicitly:

```bash
unset CLAUDE_CODE_SUBAGENT_MODEL
```

Restart Claude Code after the unset.

### Symptom: Wizard refuses my level value

Valid levels are `low`, `medium`, `high`, `xhigh`, `xxhigh`, `max`, `inherit`. There are currently no reserved-future keywords; future palette expansion may add to the reserved set with a clear error message.

## Recommended Research Setting

The `research` workflow benefits from the most capable model — it inherits the calling phase's default level, so the simplest tuning is to bump whichever phase fires research most often. The `balanced` preset already sets `phase-3-outline.effort = xhigh` (Opus, medium); push the same slot to `max` when you want Opus-4.7's `xhigh` effort tier for novel decomposition:

```jsonc
{
  "plan": {
    "phase-3-outline": { "effort": "max" }
  }
}
```

(The `max` variant gracefully degrades to canonical when the alias does not accept `effort: xhigh`. Keep the `balanced` anchor at `xhigh` when Opus-4.7 reasoning is sufficient.)

For standalone `/research` outside any plan, the dispatch resolves via `--default` (`plan.effort` → `inherit`); bump `plan.effort` if you want every standalone research run at a higher tier.

## Cross-References

| Document | Content |
|----------|---------|
| [`effort-levels.md`](effort-levels.md) | Level → `(model, effort)` primitive binding. |
| [`effort-roles.md`](effort-roles.md) | Role registry — which dispatch sites consume which roles. |
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Agent-level extension point — variant emission contract. |
| `marshall-steward/standards/effort-menu.md` | Wizard UX for the Effort submenu. |
| `.claude/skills/finalize-step-deploy-target/` | Build-time variant emission step. |
| `.claude/skills/finalize-step-sync-plugin-cache/` | Plugin cache sync (project-local). |
