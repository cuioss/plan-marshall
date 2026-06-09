# Extension Point: Dynamic-Level Executor

> **Type**: Agent Extension (declarative, build-time variant emission) | **Declaration**: `implements:` frontmatter on agent file | **Implementations**: 2 (`execution-context`, `execution-context-reader`) | **Status**: Active

## Overview

The `ext-point-dynamic-level-executor` extension point declares that a marketplace agent participates in role-based variant emission. It is the only extension point in the `ext-point-*` family whose consumer is an **agent file** (not a skill); the implementor is the agent's frontmatter, and the producer is the build target (`marketplace/targets/claude/`).

When an agent declares this extension point, the build target emits one variant agent file per ordinal level (`low`, `medium`, `high`, `xhigh`, `xxhigh`) into `target/claude/{bundle}/agents/`, each variant pinned to a specific `(model, effort)` primitive. The canonical no-suffix file is also emitted (with `implements:` and `levels:` stripped) so the `inherit` resolution case dispatches the user-configured-or-default model. Dispatch sites resolve the role's level via `manage-config effort resolve-target --role <key>` (which returns the canonical name when level is `inherit`/empty, otherwise the per-level variant `execution-context-{level}`) and call the matching variant by name.

The marketplace ships exactly one implementor — `plan-marshall:execution-context` — the single generic dispatcher that drives every plan-marshall `Task:` invocation. Arbitrary workflow bodies are dispatched through the six emitted variants via the companion workflow-doc ext-point (`ext-point-execution-context-workflow`).

The end-to-end trace:

```
.plan/marshal.json              models.roles.<role> = "high"
        │
        ▼
manage-config effort read       resolver returns "high"
        │
        ▼
dispatch site                   target = {base}-high
        │
        ▼
target/claude/{bundle}/agents/  build-emitted variant {base}-high.md
                                (model: opus, effort: high)
        │
        ▼
Claude Code runtime             subagent runs on Opus, effort=high
```

## Implementor Requirements

### Frontmatter Declaration

The canonical agent file (`marketplace/bundles/{bundle}/agents/{name}.md`) MUST declare:

```yaml
---
name: {agent-name}
description: ...
implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor
levels: [high, xxhigh]   # OPTIONAL — restricts emitted variants to a subset
---
```

| Field | Required | Description |
|-------|----------|-------------|
| `implements` | Yes | Fully-qualified ext-point reference: `plan-marshall:extension-api/standards/ext-point-dynamic-level-executor`. Single switch that turns variant emission on for this agent. |
| `levels` | No | Whitelist of ordinal levels to emit. When omitted, the build target emits all five (`low`, `medium`, `high`, `xhigh`, `xxhigh`). When present, only listed levels are emitted. The canonical (`inherit`) is always emitted regardless of `levels`. |

### Forbidden Fields

The canonical agent file MUST NOT declare `model:` or `effort:` when `implements:` is present. These fields are set by the build target on the emitted variants — declaring them on the canonical creates silent shadowing and violates the single-source-of-truth invariant.

The plugin-doctor `hardcoded-model-on-canonical` rule (see `pm-plugin-development:plugin-doctor/standards/doctor-marketplace.md`) enforces this at lint time:

- Canonical with `model:` or `effort:` AND no `implements:` → error (use `implements:` to opt into the system, or remove the model pin).
- Canonical with `implements:` AND `model:` or `effort:` → error (the build target sets these; do not author them).

### Level → Primitive Binding

The level → `(model, effort)` mapping is documented in [`plan-marshall:plan-marshall/standards/effort-levels.md`](../../plan-marshall/standards/effort-levels.md). Agent authors do NOT redeclare the binding — it is read once by the build target. See that document for the canonical table and the `xxhigh` Opus-4.8-only build-time guard.

### Role Registry

Agents declare the extension point structurally; **roles** map dispatch sites to canonical agents. The role registry lives in [`plan-marshall:plan-marshall/standards/effort-roles.md`](../../plan-marshall/standards/effort-roles.md). Adding a new role-eligible agent requires both:

1. The `implements:` declaration on the agent file (this contract).
2. A row in `effort-roles.md` linking a role key to the agent file.

## Variant Generation Contract

### Input → Output Mapping

Given a canonical agent at `marketplace/bundles/{bundle}/agents/{name}.md` with `implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor`, the build target emits:

| Output File | Frontmatter Modification |
|-------------|--------------------------|
| `target/claude/{bundle}/agents/{name}.md` | Canonical: `implements:` and `levels:` **stripped**. All other fields preserved. Serves the `inherit` resolution. |
| `target/claude/{bundle}/agents/{name}-low.md` | Variant: `name: {name}-low`, `model: haiku`, no `effort:` (haiku does not accept effort). `implements:`/`levels:` stripped. |
| `target/claude/{bundle}/agents/{name}-medium.md` | Variant: `name: {name}-medium`, `model: sonnet`, `effort: medium`. |
| `target/claude/{bundle}/agents/{name}-high.md` | Variant: `name: {name}-high`, `model: sonnet`, `effort: high`. |
| `target/claude/{bundle}/agents/{name}-xhigh.md` | Variant: `name: {name}-xhigh`, `model: opus`, `effort: high`. |
| `target/claude/{bundle}/agents/{name}-xxhigh.md` | Variant: `name: {name}-xxhigh`, `model: opus`, `effort: xhigh`. **Refused at build time** when canonical's resolved model alias does not accept `effort: xhigh` (Opus-4.8-only guard). |

When the canonical declares `levels: [high, xxhigh]`, only `{name}.md`, `{name}-high.md`, and `{name}-xxhigh.md` are emitted.

The exact level → primitive table is the single source of truth in `effort-levels.md`; this contract pins the **shape** of variant emission, not the table values.

### Session Restart Required After Variant Emission

> **CRITICAL — Restart Claude Code session before dispatching against newly-emitted variants.** Claude Code's agent registry is **session-pinned at session start**: it scans the plugin cache exactly once when the session boots and never re-scans mid-session. Variants newly emitted by the build target — for example `execution-context-{level}` files added mid-session via `/sync-plugin-cache` or the `project:finalize-step-deploy-target` finalize step — are written to disk in real time, but the already-running session has no visibility into them. A `Task: plan-marshall:execution-context-{level}` dispatch against a freshly emitted variant fails with `Agent type 'plan-marshall:execution-context-{level}' not found` even though the file is present in the cache. The operational guardrails sit at `/sync-plugin-cache` (post-rsync warning), `/marshall-steward` (executor-regenerated / agent-set-changed warning), and `variant_emitter.py` (module docstring) — all converge on the same WHY: the registry is session-pinned at startup, so newly-emitted variants are only visible after a session restart.

### plugin.json Expansion

When the build target generates per-bundle `plugin.json`, each role-eligible agent expands into N entries — one per emitted variant plus the canonical for `inherit`. Non-eligible agents emit a single entry as before. See `marketplace/targets/claude/plugin_json_gen.py` for the implementation.

### Equality / Drift Detection

`marketplace/targets/claude/equality_check.py` is variant-aware: for each canonical declaring this extension point, it asserts the emitted variant set matches the canonical's `levels:` whitelist (or the default level set when `levels:` is omitted). Variants outside the expected set are flagged as drift; missing variants are flagged as orphans. The existing structural drift logic continues to apply.

## Validation Rules

The build target enforces these rules at emission time:

| Rule | Scope | Failure Mode |
|------|-------|--------------|
| `implements:` value is the canonical fully-qualified ext-point reference | Per-agent | Build error: unrecognized `implements:` target |
| Canonical does not declare `model:` or `effort:` | Per-agent | Build error: forbidden field on canonical |
| `levels:` (when present) contains only known ordinal level keys | Per-agent | Build error: unknown level |
| `xxhigh` variant only emitted when the resolved canonical model accepts `effort: xhigh` | Per-variant | Variant skipped + build warning |
| Variant `name:` matches `{canonical-name}-{level}` exactly | Per-variant | Build error: variant name mismatch |
| Canonical no-suffix file always emitted (regardless of `levels:`) | Per-agent | Build error: canonical missing |

The plugin-doctor `hardcoded-model-on-canonical` lint rule enforces the first two rules at edit time, before the build target runs.

## Worked Example

### Canonical agent (input)

`marketplace/bundles/plan-marshall/agents/execution-context.md`:

```yaml
---
name: execution-context
description: Generic dispatcher for every plan-marshall Task: invocation
implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill
---

# Execution Context

...agent body...
```

### Emitted files (output)

The build target produces:

```
target/claude/plan-marshall/agents/
├── execution-context.md          # canonical, implements/levels stripped
├── execution-context-low.md      # model: haiku
├── execution-context-medium.md   # model: sonnet, effort: medium
├── execution-context-high.md     # model: sonnet, effort: high
├── execution-context-xhigh.md    # model: opus, effort: high
└── execution-context-xxhigh.md   # model: opus, effort: xhigh (Opus-4.8-only)
```

`target/claude/plan-marshall/.claude-plugin/plugin.json` registers six agent entries for the canonical (the canonical + five variants).

### Dispatch site

Every dispatch site computes the target via the role resolver and dispatches the matching `execution-context` variant with the 5-field prompt body (`name`, `plan_id`, `skills[]`, `workflow`, `WORKTREE`):

```bash
# Resolve the dispatch target for the verification-feedback workflow under phase-6-finalize
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize --role verification-feedback
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch below.

```
# Dispatch
Task: plan-marshall:{target}
  prompt: |
    name: verification-feedback
    plan_id: {plan_id}
    skills[N]:
    - <workflow-required skills>
    workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md
    WORKTREE: {worktree_path}
    producer: pr-comment
    caller_phase: phase-6-finalize
```

The `resolve-target` subcommand returns `execution-context` when the level is `inherit`/empty, and `execution-context-{level}` otherwise. The dispatched variant runs the caller-specified `workflow` doc against the resolved `(model, effort)` primitive baked into the variant's frontmatter.

## Cross-References

| Document | Content |
|----------|---------|
| [`effort-levels.md`](../../plan-marshall/standards/effort-levels.md) | Level → `(model, effort)` primitive binding; alias rules; `max` guard rationale |
| [`dispatch-granularity.md`](dispatch-granularity.md) | Granularity heuristics — when a step earns a dispatch envelope vs. running inline. Sibling extension-point doc. |
| [`effort-roles.md`](../../plan-marshall/standards/effort-roles.md) | Role registry mapping role keys to canonical agents |
| [`effort-variants.md`](../../plan-marshall/standards/effort-variants.md) | User-facing centralised doc for configuring `models.roles.<name>` |
| `marketplace/targets/claude/emitter.py` | Variant emission implementation |
| `marketplace/targets/claude/plugin_json_gen.py` | `plugin.json` expansion for role-eligible agents |
| `marketplace/targets/claude/equality_check.py` | Variant-aware drift detection |
| `pm-plugin-development:plugin-doctor/standards/doctor-marketplace.md` | `hardcoded-model-on-canonical` lint rule |

## Current Implementations

| Bundle | Agent | `levels:` whitelist | Lever |
|--------|-------|---------------------|-------|
| plan-marshall | execution-context | (default — all five) | level/effort lever — write-capable dispatcher |
| plan-marshall | execution-context-reader | (default — all five) | read-only tool-surface lever — untrusted-content ingestion |

`execution-context` is the generic write-capable dispatcher whose body is parameterised by the `workflow` field in its prompt-body contract (see [`ext-point-execution-context-workflow`](ext-point-execution-context-workflow.md) for the workflow-doc side of the contract). Any number of workflow docs across the marketplace can be dispatched through its emitted variants.

`execution-context-reader` is the read-only ingestion dispatcher for untrusted external content (see `plan-marshall:untrusted-ingestion`). It rides the same variant-emission machinery but supplies a **restricted, read-only tool surface** (`WebSearch, WebFetch, Read, Grep` — no Write/Edit/Bash/Skill); its candidate output is untrusted until the deterministic `untrusted-ingestion:validate_struct` script certifies it. The read-only tool surface is a distinct lever from the level/effort lever both implementors ride — see ADR-003.
