# Extension Point: Execution-Context Workflow

> **Type**: Workflow-Doc Extension (declarative, runtime-read) | **Declaration**: `implements:` frontmatter on workflow doc or SKILL.md | **Status**: Active

## Overview

The `ext-point-execution-context-workflow` extension point declares that a marketplace doc is dispatchable as a workflow by `plan-marshall:execution-context-{level}`. It is the consumer-side companion to `ext-point-dynamic-level-executor` (which governs the dispatcher agent itself).

When a workflow doc declares this extension point, it asserts conformance to the prompt-body input contract, the return-TOON output contract, and the addressing convention defined below. The execution-context dispatcher reads the `workflow` field in its prompt body as a `{bundle}:{skill}/workflow/{file}.md`, `{bundle}:{skill}/standards/{file}.md` or `{bundle}:{skill}/SKILL.md` notation, resolves it to a filesystem path through the `resolve-workflow` verb, and `Read`s the returned absolute path — implementors of this ext-point are the legal targets of that `Read`.

## Implementor Requirements

### Frontmatter Declaration

```yaml
---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---
```

### Addressing

The implementor MUST live at one of these paths:

| Notation | Resolves to |
|----------|-------------|
| `{bundle}:{skill}/SKILL.md` | `marketplace/bundles/{bundle}/skills/{skill}/SKILL.md` |
| `{bundle}:{skill}/workflow/{file}.md` | `marketplace/bundles/{bundle}/skills/{skill}/workflow/{file}.md` |

The `workflow/` directory (singular) is the marketplace convention for workflow docs. Reference / contract / configuration docs live under `standards/`; tool-loaded reference material lives under `references/`.

Every file under `workflow/` MUST be a `.md` markdown file. There is no orchestrator-exception: even top-level workflows the LLM follows directly in the main context (e.g., `plan-marshall/workflow/planning.md`, `recipe.md`, `execution.md`) declare the ext-point — their Output section is degenerate (a `status` + `display_detail` shape emitted when the workflow is wrapped in a `Task: execution-context-{level}` dispatch; interactive entry surfaces the same conceptual state via `manage-logging` records and the terminal user message).

A skill MAY hold zero, one, or many `workflow/*.md` files. A SKILL.md MAY itself implement the ext-point when the skill's primary deliverable is one workflow (e.g., the six phase-N skills). When both apply, SKILL.md typically describes the skill and points at one or more `workflow/*.md` implementors that carry the actual dispatch bodies.

**Cross-phase / multi-consumer placement rule**: when a workflow is consumed from multiple phases or from outside any phase (e.g., `triage`, `q-gate-validation`, `research-best-practices`, `enrich-module`), place it under `plan-marshall/skills/plan-marshall/workflow/` rather than under any single consumer phase. Single-phase workflows live under the consumer phase's `skill/workflow/`.

### Workflow-Resolution Root

The `workflow` field in a `Task:` prompt body is resolved by the single `resolve-workflow` verb
(`plan-marshall:extension-api:extension_api resolve-workflow --notation {N} --worktree {W}`), which
returns a verified absolute path in this order — stated here once, and nowhere else:

1. **The worktree source tree first.** `{WORKTREE}/marketplace/bundles/{bundle}/skills/{skill}/{path}`
   is returned when that file exists. A bundle-owning checkout — this meta-project and every other
   checkout that carries `marketplace/bundles` — therefore resolves to the code the worktree actually
   carries, so a dispatched leaf sees worktree edits without a cache sync.
2. **The installed copy second.** When the worktree probe misses, the verb resolves through the
   platform-runtime `layout bundle-cache-root` roots and
   `marketplace_bundles.resolve_bundle_path`, which already handles the nested versioned plugin cache
   (newest eligible version) and the flat OpenCode / Antigravity layout. A consumer repository has no
   `marketplace/bundles` tree, so this is the leg that serves it.

The verb is the ONLY resolution path. A dispatcher MUST NOT construct a workflow path by hand, and
MUST NOT map a notation only to `marketplace/bundles/`. When neither probe carries the file the verb
returns `error: workflow_not_found`, naming every probed path so a could-not-find is distinguishable
from a wrong path.

`WORKTREE` governs where the dispatched workflow's tool calls (Edit / Write / Read / `git -C`) act. It
now also anchors the first resolution probe; the installed copy is the fallback, never a competing
root for a checkout that owns the bundle.

**Consequence.** In a bundle-owning checkout a worktree edit is visible to the next dispatch
immediately, because the worktree probe wins. A consumer repository resolves the installed copy and
receives a changed body only after the harness install advances; consumer plans do not author the
bundles they load, so that is the intended direction.

### Input Contract — what the implementor can rely on

Every dispatch into the implementor delivers, via the parent dispatcher (`plan-marshall:execution-context-{level}`):

| Field | Always present | Description |
|-------|:--------------:|-------------|
| `plan_id` | Yes | Plan identifier; sentinel `none` for free-standing dispatches. |
| `WORKTREE` | Yes | Repo-relative working directory; `.` for main checkout. |
| `skills[]` | Yes | Caller-loaded skills, loaded before the workflow body runs. May be empty. |
| `plan-marshall:persona-plan-marshall-agent` | Yes (implicit) | Loaded by the dispatcher before any caller-specified skill. |

Workflow-specific runtime inputs (e.g., `finding_type`, `track`, `scope`) flow through additional prompt-body fields the implementor declares in its own input table.

### Output Contract — what the implementor MUST return

```toon
status: success | error | loop_back | blocked
display_detail: "<≤80 char ASCII summary, no trailing period>"
```

Plus any workflow-specific return fields the implementor declares. The `status` and `display_detail` fields are mandatory on every return — including error returns.

The `display_detail` field is the orchestrator-facing one-line summary surfaced by `manage-status mark-step-done`, the output-template renderer, and metrics. It MUST:

- be ≤ 80 characters;
- be ASCII-only;
- end without a trailing period.

These constraints are structural — the renderer truncates or rejects values that violate them. They live here as the single source of truth and are NOT redeclared per-workflow.

### Forbidden

The implementor MUST NOT carry inline prose stating "Dispatched via `Task: plan-marshall:execution-context-{level}` with this doc as `workflow`." That statement is the ext-point's job; the `implements:` declaration replaces it.

The implementor MUST NOT redeclare `persona-plan-marshall-agent` in its own steps — the dispatcher loads it implicitly.

## Phase-context propagation for phase-agnostic workflows

Subagents cannot sub-dispatch. A dispatched envelope is a leaf — all cross-envelope dispatch originates from the main-context orchestrator. See [`ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) for the canonical leaf/dispatch-topology contract.

The level resolver still needs the caller's phase to pin the right model/effort when the orchestrator dispatches a workflow that fires from **multiple phases**. Two mechanisms supply it:

1. **The `name:` field.** A dispatch's `name:` frontmatter (or its `workflow:` notation) usually encodes the phase without a separate `caller_phase:` field — **directly** when `name:` is itself a phase key, or **via the `workflow:` notation** when it is not:
   - `name: phase-2-refine` → caller phase is `phase-2-refine` (direct one-for-one match)
   - `name: verification-feedback` AND `workflow: …/phase-5-execute/…` → caller phase is `phase-5-execute` (encoded by the workflow path)

2. **The optional `caller_phase:` field (6th-field extension of the canonical 5-field contract).** When the dispatched workflow's `name:` does not naturally encode the phase — for example a phase-agnostic workflow such as `verification-feedback` or `q-gate-validation` that the orchestrator fires from more than one phase — the main-context orchestrator's prompt body MUST include `caller_phase: phase-N` explicitly so the level resolver tracks the caller's phase.

The 5-field contract (`name`, `plan_id`, `skills[]`, `workflow`, `WORKTREE`) is unchanged for top-level dispatches that have an unambiguous phase home. `caller_phase` is the optional 6th field the orchestrator passes when dispatching a phase-agnostic workflow; it is a top-level dispatch field, not a value forwarded across a sub-dispatch hop (there are no sub-dispatches).

The resolver already accepts `--phase <P>` from any caller — this is a documentation extension, not a runtime change.

## Plugin-Doctor Enforcement

The lint rule `workflow-doc-implements-contract` enforces every requirement in this document by filesystem glob plus frontmatter check: the `implements:` frontmatter is present, the Output section declares at minimum `status` and `display_detail`, and the Forbidden constraints above are honoured. Cheap enough to run as part of the marketplace quality gate.

## Cross-references

- [`ext-point-dynamic-level-executor`](ext-point-dynamic-level-executor.md) — companion ext-point for the agent side.
- [`agents/execution-context.md`](../../../agents/execution-context.md) — the dispatcher that loads workflow-doc implementors.
- [`ref-workflow-architecture/standards/dispatch-walkthrough.md`](../../ref-workflow-architecture/standards/dispatch-walkthrough.md) — worked end-to-end traces showing how the prompt-body fields and Output contract flow through three representative dispatches.
- [`dispatch-granularity.md`](dispatch-granularity.md) — granularity heuristics: when a step earns an `execution-context` dispatch envelope vs. running inline as a script.
