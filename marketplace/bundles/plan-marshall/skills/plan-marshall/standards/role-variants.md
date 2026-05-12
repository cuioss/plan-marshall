# Role Variants — User Guide

> User-facing centralised guide to configuring per-role models for plan-marshall subagents.

## What This Does

By default, every subagent dispatched by plan-marshall inherits the model from the parent Claude Code session (typically Opus). Some roles benefit from higher capability (Q-Gate validation, automated review, retrospective analysis); most don't, costing tokens for no gain. The role-variants system lets you pick a model + effort tier per role, applied automatically at dispatch time.

You configure a small JSON block in `.plan/marshal.json`. The build target emits one variant agent file per (canonical agent × level) combination. Dispatch sites read your configuration and call the right variant by name. End result: the right model runs the right role, no per-dispatch overrides, no manual flag passing.

## The Level Palette

Six ordinal tiers plus a sentinel:

| Level | Model | Effort | When to use |
|-------|-------|--------|-------------|
| `low` | Haiku | (n/a) | Mechanical tasks: log scrubbing, simple lookups, deterministic transforms. |
| `medium` | Sonnet | medium | Default for routine work — most code edits, doc updates. |
| `high` | Sonnet | high | Analytical work: PR review, validation, multi-file reasoning. |
| `xhigh` | Opus | medium | Opus reasoning without max thinking — fills the Sonnet-high → Opus-high cost/quality gap. |
| `xxhigh` | Opus | high | High-effort Opus — today's standard Opus top tier. |
| `max` | Opus | xhigh | Top tier (Opus-4.7-only). Research, novel problem decomposition; build-time guard skips emission when the alias does not accept `effort: xhigh`. |
| `inherit` | (parent) | (parent) | Sentinel: dispatch the canonical, inheriting whatever the parent session uses. |

See [`model-levels.md`](model-levels.md) for the full level → `(model, effort)` primitive binding, alias rules, and the `max` build-time guard.

## The Role Registry

A **role** is a stable key naming a class of dispatch (e.g., `cross.q-gate-validation`, `phase-6.create-pr`, `cross.research`). The registry is hierarchical (kebab-case, 15 keys across 7 groups: `phase-1` through `phase-6`, plus `cross`). The full registry — which roles exist, which workflow doc each binds to, and the three accepted lookup forms (`--role phase-1`, `--role phase-6.create-pr`, `--phase phase-6 --role create-pr`) — lives in [`model-roles.md`](model-roles.md).

## How to Configure

### Option A: The Wizard (Recommended)

Run the `marshall-steward` wizard and pick the **Models** submenu:

```
/marshall-steward
```

The wizard:

- Shows the current `models` block (or "(not configured — defaults apply)").
- Edits `models.default` via prompt — your plan-wide fallback level.
- Walks the role registry, letting you set each role to a specific level or leave it on `default`.
- Refuses invalid levels (e.g., typos) at save time.

### Option B: Edit `marshal.json` Directly

The schema lives at `.plan/marshal.json` under the `models` key:

```json
{
  "models": {
    "default": "medium",
    "roles": {
      "cross": {
        "research": "max",
        "q-gate-validation": "high",
        "triage": "high"
      },
      "phase-6": {
        "create-pr": "medium",
        "lessons-capture": "low"
      }
    }
  }
}
```

Resolution order for any role:

1. The deepest explicit per-role override (e.g. `models.roles.cross.research`).
2. The parent group's plain-string value (e.g. `models.roles.phase-2: "high"` applies to every workflow under phase-2).
3. `models.default` — plan-wide default.
4. `inherit` — implicit fallback when neither is set.

The `models` block is **opt-in** — when absent entirely, every subagent inherits the parent session's model. The dispatcher resolves the level at dispatch time via `manage-config models resolve-target --role <key>`, so no Claude Code restart is required after editing.

### Recommended Starting Configuration

For most workflows, this gets you most of the value at modest cost:

```json
{
  "models": {
    "default": "medium",
    "roles": {
      "cross": {
        "research": "max",
        "q-gate-validation": "high",
        "triage": "high"
      }
    }
  }
}
```

## What Happens at Dispatch Time

When a dispatch site fires (e.g., phase-6-finalize dispatching the `phase-6.create-pr` workflow):

1. The site calls `manage-config models resolve-target --role phase-6.create-pr` to resolve the dispatch target directly.
2. If level is `inherit` (or the resolver returned `inherit` as the implicit fallback), the target is the **canonical** no-suffix variant: `Task: plan-marshall:execution-context`. The runtime inherits the parent's model.
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

1. Is the role spelled correctly per the hierarchical registry in [`model-roles.md`](model-roles.md)? Keys are kebab-case (`cross.q-gate-validation`, not `q_gate_validation`).
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

## Recommended `cross.research` Setting

The `research` workflow benefits from the most capable model — every other workflow stays at the user's chosen default. To set:

```json
{
  "models": {
    "roles": {
      "cross": {
        "research": "max"
      }
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
| `doc/refactor/02-build-system/plan.md` § Variant Emission | Cluster-02 contributor doc. |
| `.claude/skills/finalize-step-deploy-target/` | Build-time variant emission step. |
| `.claude/skills/finalize-step-sync-plugin-cache/` | Plugin cache sync (project-local). |
