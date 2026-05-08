# Role Variants — User Guide

> User-facing centralised guide to configuring per-role models for plan-marshall subagents.

## What This Does

By default, every subagent dispatched by plan-marshall inherits the model from the parent Claude Code session (typically Opus). Some roles benefit from higher capability (Q-Gate validation, automated review, retrospective analysis); most don't, costing tokens for no gain. The role-variants system lets you pick a model + effort tier per role, applied automatically at dispatch time.

You configure a small JSON block in `.plan/marshal.json`. The build target emits one variant agent file per (canonical agent × level) combination. Dispatch sites read your configuration and call the right variant by name. End result: the right model runs the right role, no per-dispatch overrides, no manual flag passing.

## The Level Palette

Five ordinal tiers plus a sentinel:

| Level | Model | Effort | When to use |
|-------|-------|--------|-------------|
| `low` | Haiku | (n/a) | Mechanical tasks: log scrubbing, simple lookups, deterministic transforms. |
| `medium` | Sonnet | medium | Default for routine work — most code edits, doc updates. |
| `high` | Sonnet | high | Analytical work: PR review, validation, multi-file reasoning. |
| `xhigh` | Opus | high | Heavy reasoning: complex refactors, deep root-cause analysis. |
| `xxhigh` | Opus | xhigh | Top tier (Opus-4.7-only). Research, novel problem decomposition. |
| `inherit` | (parent) | (parent) | Sentinel: dispatch the canonical, inheriting whatever the parent session uses. |

See [`model-levels.md`](model-levels.md) for the full level → `(model, effort)` primitive binding, alias rules, and the `xxhigh` build-time guard.

## The Role Registry

A **role** is a stable key naming a class of dispatch (e.g., `q_gate_validation`, `pr_creation`, `research`). The full registry — which roles exist, which canonical agent each binds to, and which roles are effective vs pending — lives in [`model-roles.md`](model-roles.md).

Highlights:

- **Effective roles** (have runtime effect today): `q_gate_validation`, `research`, `pr_creation`, `automated_review`, `sonar_roundtrip`, `lessons_capture`, `change_type_detection`, `phase_init`, `phase_plan`, `component_analysis`, `inventory_analysis`, `tool_coverage_analysis`.
- **Pending roles** (schema-validates but no runtime effect yet): `phase_refine`, `phase_outline`, `phase_execute`, `phase_finalize`, `retrospective`, `implementation`, `testing`, `build_runner`. Configuration is preserved across saves; activation lands in a future plan.

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
- Flags **pending** roles so you know configuration is preserved but not yet effective.
- Prints a **restart hint** after saving — Claude Code loads agent files at session start, so new variant routing applies only after you exit and re-enter.

### Option B: Edit `marshal.json` Directly

The schema lives at `.plan/marshal.json` under the `models` key:

```json
{
  "models": {
    "default": "medium",
    "roles": {
      "q_gate_validation": "high",
      "research": "xxhigh",
      "automated_review": "high",
      "lessons_capture": "low"
    }
  }
}
```

Resolution order for any role:

1. `models.roles.<role>` — explicit per-role override.
2. `models.default` — plan-wide default.
3. `inherit` — implicit fallback when neither is set.

Restart Claude Code after editing. The `models` block is **opt-in** — when absent entirely, behavior is unchanged from before this system existed (every subagent inherits the parent model).

### Recommended Starting Configuration

For most workflows, this gets you most of the value at modest cost:

```json
{
  "models": {
    "default": "medium",
    "roles": {
      "research": "xxhigh",
      "q_gate_validation": "high",
      "automated_review": "high",
      "sonar_roundtrip": "high"
    }
  }
}
```

## What Happens at Dispatch Time

When a dispatch site fires (e.g., phase-6-finalize calling the `pr_creation` agent):

1. The site calls `manage-config models read --role pr_creation` to resolve your level.
2. If level is `inherit` (or the resolver returned `inherit` as the implicit fallback), the dispatch targets the **canonical** no-suffix variant: `Task: plan-marshall:create-pr-agent`. The runtime inherits the parent's model.
3. Otherwise, the dispatch targets a **variant**: `Task: plan-marshall:create-pr-agent-{level}`. The variant has `model:` and `effort:` baked into its frontmatter, so Claude Code runs the subagent on those exact settings.

Variants are emitted at build time into `target/claude/{bundle}/agents/`, then synced into the plugin cache via `/sync-plugin-cache`. The canonical agent file you see in the marketplace source has neither `model:` nor `effort:` — those fields are forbidden on canonicals and the build target sets them on variants.

## Troubleshooting

### Symptom: My configured level isn't taking effect

**Check:**

1. Did you restart Claude Code after editing? Agent files load at session start; mid-session edits don't apply until restart. (The wizard prints this hint after every Models save.)
2. Is the role status `effective` in [`model-roles.md`](model-roles.md)? **pending** roles validate at save but produce no runtime effect.
3. Is the level spelled correctly (`high`, not `High` or `hi`)?
4. Is `target/claude/` regenerated? Run the `default:deploy-target` step (or `python3 marketplace/targets/generate.py --target claude --output target/claude`) to refresh emitted variants, then `/sync-plugin-cache` to push them into the plugin cache.

### Symptom: A role configured as `xxhigh` is not running on Opus

`xxhigh` resolves to `(opus, xhigh)`, which is currently Opus-4.7-only. The build target's guard refuses to emit the `xxhigh` variant when the canonical's resolved alias does not accept `effort: xhigh` — the dispatch falls back to the canonical, which inherits the parent's model. Check `.plan/logs/` for the build warning naming the canonical and the missing capability.

### Symptom: Set a level but it's not even visible to the resolver

`CLAUDE_CODE_SUBAGENT_MODEL` is an environment variable that overrides every subagent's pinned model at session start (per code.claude.com). When set, it beats the variant's `model:` declaration — including yours. Unset the env var or override it explicitly:

```bash
unset CLAUDE_CODE_SUBAGENT_MODEL
```

Restart Claude Code after the unset.

### Symptom: Wizard refuses my level value

Valid levels are `low`, `medium`, `high`, `xhigh`, `xxhigh`, `inherit`. The reserved keyword `max` is not yet supported (planned future-additive option for "the highest tier the runtime supports") — use `xxhigh` for the current top tier.

## Migration

If you previously relied on `research-best-practices-agent`'s implicit Opus pin (the agent used to declare `model: opus` directly), that pin has been removed as part of this system's rollout. Behaviour delta: with no `models` block, the research agent now inherits the parent session's model instead of forcing Opus.

To restore the previous behaviour, set:

```json
{
  "models": {
    "roles": {
      "research": "xxhigh"
    }
  }
}
```

(or `xhigh` if you don't need Opus-4.7's `xhigh` effort tier).

All other canonical agents had no `model:` line previously, so their dispatch behaviour is unchanged when no `models` block is configured.

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
