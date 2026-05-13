# Role Variants — User Guide

> User-facing centralised guide to configuring per-role models for plan-marshall subagents.

## What This Does

By default, every subagent dispatched by plan-marshall inherits the model from the parent Claude Code session (typically Opus). Some workflows benefit from higher capability (verification-feedback triage, research, retrospective analysis); most don't, costing tokens for no gain. The role-variants system lets you pick a model + effort tier per phase (and per workflow inside a phase), applied automatically at dispatch time.

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

See [`model-levels.md`](model-levels.md) for the full level → `(model, effort)` primitive binding, alias rules, and the `max` build-time guard.

## The Role Registry

A **role** is a stable key naming a class of dispatch (e.g., `phase-6.verification-feedback`, `phase-3.research`). The registry is phase-scoped (six groups: `phase-1` through `phase-6`, each carrying optional sub-keys). The full registry — which sub-keys exist on which phase, which workflow doc each binds to, and the accepted lookup forms — lives in [`model-roles.md`](model-roles.md).

## How to Configure

### Option A: The Wizard (Recommended)

Run the `marshall-steward` wizard and pick the **Models** submenu:

```
/marshall-steward
```

The wizard:

- Shows the current `models` block (or "(not configured — defaults apply)").
- Edits `models.default` via prompt — your plan-wide fallback level.
- Walks each phase, letting you set the phase default or override individual workflow sub-keys.
- Refuses invalid levels (e.g., typos) at save time.

### Option B: Edit `marshal.json` Directly

The schema lives at `.plan/marshal.json` under the `models` key:

```jsonc
{
  "models": {
    "default": "medium",
    "roles": {
      "phase-3": {
        "default": "high",
        "research": "max"
      },
      "phase-5": {
        "verification-feedback": "high"
      },
      "phase-6": {
        "verification-feedback": "high",
        "post-run-review": "xhigh"
      }
    }
  }
}
```

Resolution order for any role:

1. The deepest explicit sub-key override (e.g. `models.roles.phase-3.research`).
2. The group's `default` slot when the sub-key is unset or unspecified (`models.roles.phase-3.default`).
3. A plain-string value at the group (single-level shorthand applied to every workflow under that phase) — e.g. `"phase-2": "high"`.
4. `models.default` — plan-wide default.
5. `inherit` — implicit fallback when nothing else matches.

The `models` block is **opt-in** — when absent entirely, every subagent inherits the parent session's model. The dispatcher resolves the level at dispatch time via `manage-config models resolve-target --phase <phase> --role <subkey>`, so no Claude Code restart is required after editing.

### Recommended Starting Configuration

For most workflows, this gets you most of the value at modest cost:

```jsonc
{
  "models": {
    "default": "medium",
    "roles": {
      "phase-3": { "research": "max" },
      "phase-5": { "verification-feedback": "high" },
      "phase-6": { "verification-feedback": "high" }
    }
  }
}
```

Pre-built profiles cover the same ground:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config models apply-preset --preset balanced
```

Available presets: `economic`, `balanced`, `high-end`. See [`model-roles.md`](model-roles.md) and `model_presets.py` for the per-preset role tables.

## What Happens at Dispatch Time

When a dispatch site fires (e.g., phase-5-execute calling `verification-feedback` with `producer=build-runner`):

1. The site calls `manage-config models resolve-target --phase phase-5 --role verification-feedback`.
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

1. Is the role spelled correctly per the hierarchical registry in [`model-roles.md`](model-roles.md)? Keys are kebab-case (`phase-6.verification-feedback`, not `phase_6.verification_feedback`).
2. Is the level spelled correctly (`high`, not `High` or `hi`)?
3. Is `target/claude/` regenerated? Run the `project:finalize-step-deploy-target` step (or `python3 marketplace/targets/generate.py --target claude --output target/claude`) to refresh emitted variants, then `/sync-plugin-cache` to push them into the plugin cache.

### Symptom: I get a "role key is retired" error

You're reading a key from the pre-rewrite registry (`cross.*` or one of the retired `phase-6.*` sub-keys: `create-pr`, `pre-submission-self-review`, `lessons-capture`, `retrospective`, `pr-doctor`). The error message names the new target. Map common cases:

| Old key | New shape |
|---------|-----------|
| `cross.triage` | `--phase <caller-phase> --role verification-feedback` |
| `cross.research` | `--phase <caller-phase> --role research` (or `--default` for standalone `/research`) |
| `cross.q-gate-validation` | `--phase <caller-phase>` (no `--role` — q-gate-validation tracks the phase default) |
| `cross.plugin-doctor` | `--phase phase-6 --role verification-feedback` (with `producer=plugin-doctor`) |
| `phase-6.retrospective`, `phase-6.lessons-capture` | `--phase phase-6 --role post-run-review` |
| `phase-6.pr-doctor` | `--phase phase-6 --role verification-feedback` (with `producer=pr-state`) |
| `phase-6.create-pr`, `phase-6.pre-submission-self-review` | `--phase phase-6` (no `--role` — both track `phase-6.default`) |

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

## Recommended `research` Setting

The `research` workflow benefits from the most capable model — every other workflow stays at the user's chosen default. To set it on a per-phase basis where research most often fires (phase-2 / phase-3 / phase-4):

```jsonc
{
  "models": {
    "roles": {
      "phase-2": { "research": "max" },
      "phase-3": { "research": "max" },
      "phase-4": { "research": "max" }
    }
  }
}
```

(or `xxhigh` if you don't need Opus-4.7's `xhigh` effort tier — the `max` variant gracefully degrades to canonical when the alias does not accept `effort: xhigh`.)

## Cross-References

| Document | Content |
|----------|---------|
| [`model-levels.md`](model-levels.md) | Level → `(model, effort)` primitive binding. |
| [`model-roles.md`](model-roles.md) | Role registry — which dispatch sites consume which roles. |
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Agent-level extension point — variant emission contract. |
| `marshall-steward/standards/models-menu.md` | Wizard UX for the Models submenu. |
| `.claude/skills/finalize-step-deploy-target/` | Build-time variant emission step. |
| `.claude/skills/finalize-step-sync-plugin-cache/` | Plugin cache sync (project-local). |
