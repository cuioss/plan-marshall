# Model Levels — Ordinal Scale & Two-Axis Effort Model

> Single source of truth for the target-neutral ordinal level scale (`level-1` through `level-7`, plus `inherit`) and the Two-Axis Effort Model.

## Overview

The variant emission system ([`ext-point-dynamic-level-executor`](../../extension-api/standards/ext-point-dynamic-level-executor.md)) uses a fixed seven-tier ordinal scale to express cognitive complexity and compute demand across subagent roles. Authors configure roles by target-neutral level keywords in `.plan/marshal.json` (e.g., `plan.phase-3-outline.effort.research = "level-7"`).

The level scale is strictly ordinal — `level-1 → level-2 → level-3 → level-4 → level-5 → level-6 → level-7` represents increasing reasoning depth, context synthesis capability, and compute expenditure:

* `level-1` — Mechanical work: log scrubbing, simple file/data transforms, deterministic lookups.
* `level-2` — Routine tasks: scoped code edits, unit test adjustments, formatting, simple documentation updates.
* `level-3` — Analytical tasks: triage, verification feedback analysis, multi-file inspection, standard review.
* `level-4` — Advanced reasoning: architectural outline, solution formulation, moderate refactoring across components.
* `level-5` — Complex reasoning: deep codebase exploration, multi-module dependency analysis, comprehensive verification.
* `level-6` — Heavy reasoning: cross-cutting architectural synthesis, subtle race condition/concurrency analysis, high-depth review.
* `level-7` — Maximum capability ceiling: epic decomposition, high-stakes security analysis, definitive architectural decisions.
* `inherit` — Sentinel: dispatches the canonical unadorned subagent variant, cleanly inheriting the parent session's active model.

## The Two-Axis Model

Model capability and reasoning intensity are orthogonal dimensions. Plan Marshall models each level as a coordinate in a two-axis space:

$$\text{Level} = (\text{Model Axis}, \text{Effort Axis})$$

1. **Model Axis (Capacity)**: Selects the underlying foundation model class or engine (e.g., fast/efficient lightweight models vs. massive frontier reasoning models).
2. **Effort Axis (Reasoning Intensity)**: Controls the thinking budget, reasoning tokens, or search depth allocated to the model (e.g., `low`, `medium`, `high`, `max`).

Different target platforms realize this coordinate space using their own native primitives.

## Target Realization & Default Ladders

Each target platform (`marketplace/targets/{target}/`) implements a default ladder translating the 7 ordinal rungs into its specific runtime capabilities. These defaults are realized and locally customizable via `.plan/local/effort-ladder.json`:

### Google Antigravity Ladder (Option 1 Default)

Antigravity operates with **Gemini Flash 3.8** (supporting `low`, `medium`, `high` effort) and **Gemini Pro 3.1** (supporting `low`, `high` effort):

| Level | Model | Effort | Cognitive Role |
|-------|-------|--------|----------------|
| `level-1` | `flash` | `low` | Fast mechanical transforms |
| `level-2` | `flash` | `low` | Scoped code updates |
| `level-3` | `flash` | `medium` | Analytical triage & validation |
| `level-4` | `flash` | `medium` | Advanced solution planning |
| `level-5` | `flash` | `high` | Deep investigation & test suite analysis |
| `level-6` | `pro` | `low` | Complex cross-component reasoning |
| `level-7` | `pro` | `high` | Maximum architectural synthesis |
| `inherit` | (parent) | (parent) | Inherits active session model |

### Claude Code Ladder (Canonical Default)

Claude Code maps rungs onto Anthropic model aliases and effort keywords:

| Level | Model | Effort | Cognitive Role |
|-------|-------|--------|----------------|
| `level-1` | `haiku` | (omitted) | Fast mechanical transforms (effort unsupported on Haiku) |
| `level-2` | `sonnet` | `medium` | Routine code edits and doc maintenance |
| `level-3` | `sonnet` | `high` | Analytical triage and multi-file reasoning |
| `level-4` | `opus` | `medium` | Opus reasoning with moderate thinking budget |
| `level-5` | `opus` | `high` | Full analytical Opus reasoning |
| `level-6` | `opus` | `xhigh` | Extra-high-effort Opus (alias-capability-gated) |
| `level-7` | `fable` | `max` | Maximum capability ceiling (alias-capability-gated) |
| `inherit` | (parent) | (parent) | Inherits active session model |

### OpenCode Ladder (Inherit Default)

In OpenCode, subagent definitions are static markdown files deployed under `~/.config/opencode/agent/`. Because OpenCode lacks a built-in in-place file re-emitter or universal model provider, all 7 level variants default to unpinned (`model: null`, `effort: null`), cleanly falling back to `inherit` (disagreeing with neither local nor remote model configurations). Users can configure custom ladders in `.plan/local/effort-ladder.json` for future rewriter integrations.

## Machine-Local Customization (`.plan/local/effort-ladder.json`)

Project repository configuration (`marshal.json`) expresses only the target-neutral intent (`level-1` .. `level-7`). The machine-local mapping is stored in the git-ignored file `.plan/local/effort-ladder.json`:

```json
{
  "targets": {
    "antigravity": {
      "level-1": { "model": "flash", "effort": "low" },
      "level-2": { "model": "flash", "effort": "low" },
      "level-3": { "model": "flash", "effort": "medium" },
      "level-4": { "model": "flash", "effort": "medium" },
      "level-5": { "model": "flash", "effort": "high" },
      "level-6": { "model": "pro", "effort": "low" },
      "level-7": { "model": "pro", "effort": "high" }
    },
    "claude": {
      "level-1": { "model": "haiku", "effort": null },
      "level-2": { "model": "sonnet", "effort": "medium" },
      "level-3": { "model": "sonnet", "effort": "high" },
      "level-4": { "model": "opus", "effort": "medium" },
      "level-5": { "model": "opus", "effort": "high" },
      "level-6": { "model": "opus", "effort": "xhigh" },
      "level-7": { "model": "fable", "effort": "max" }
    },
    "opencode": {
      "level-1": { "model": null, "effort": null },
      "level-2": { "model": null, "effort": null },
      "level-3": { "model": null, "effort": null },
      "level-4": { "model": null, "effort": null },
      "level-5": { "model": null, "effort": null },
      "level-6": { "model": null, "effort": null },
      "level-7": { "model": null, "effort": null }
    }
  }
}
```

* **Steward initialization**: Running `/marshall-steward` automatically seeds default ladders for Antigravity (Option 1), Claude (canonical), and OpenCode (inherit).
* **Unconfigured fallback**: If the local file is absent or a target is unconfigured, all rungs fall back to `inherit` and a warning is surfaced.

## Default Resolution Order

The resolver (`manage-config effort read --role <name>`) walks this order:

1. `plan.<phase>.effort.<role>` — explicit per-role override.
2. `plan.<phase>.effort.default` — phase-level default.
3. `plan.<phase>.effort` — string shorthand for the phase.
4. `plan.effort` — plan-wide fallback (when set).
5. `inherit` — implicit fallback when none is configured.

The resolver returns a single level keyword. Dispatch sites compute the agent target as:

* `inherit` or empty → canonical no-suffix variant: `Task: {bundle}:{base}`.
* any other level → variant: `Task: {bundle}:{base}-{level}`.

Use `manage-config effort resolve-target --role <name>` for a single helper invocation that returns the variant target name directly.

## Cross-References

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Variant emission contract — how levels are consumed at build time. |
| [`effort-roles.md`](effort-roles.md) | Role registry — which dispatch sites consume which roles. |
| [`effort-variants.md`](effort-variants.md) | User-facing centralised doc — how to configure `models.roles.<name>`. |
| `doc/concepts/execution-context.adoc` | Architectural concept for execution context and variant dispatch. |
| `doc/developer/effort-ladders.adoc` | Developer guide for integrating effort ladders on new platforms. |
