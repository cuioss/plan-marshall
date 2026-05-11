# Extension Point: Execution-Context Workflow

> **Type**: Workflow-Doc Extension (declarative, runtime-read) | **Declaration**: `implements:` frontmatter on workflow standards doc or SKILL.md | **Status**: Active

## Overview

The `ext-point-execution-context-workflow` extension point declares that a marketplace doc is dispatchable as a workflow by `plan-marshall:execution-context-{level}`. It is the consumer-side companion to `ext-point-dynamic-level-executor` (which governs the dispatcher agent itself).

When a workflow doc declares this extension point, it asserts conformance to the prompt-body input contract, the return-TOON output contract, and the addressing convention defined below. The execution-context dispatcher reads the `workflow` field in its prompt body as a `{bundle}:{skill}/workflow/{file}.md` or `{bundle}:{skill}/SKILL.md` notation, resolves it to a filesystem path, and `Read`s the file — implementors of this ext-point are the legal targets of that `Read`.

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

**Every** file under `workflow/` (markdown or AsciiDoc) MUST declare `implements:` and conform to the input/output contract below. There is no orchestrator-exception: even top-level workflows the LLM follows directly in the main context (e.g., `plan-marshall/workflow/planning.md`, `recipe.md`, `execution.md`) declare the ext-point — their Output section is degenerate (a `status` + `display_detail` shape emitted when the workflow is wrapped in a `Task: execution-context-{level}` dispatch; interactive entry surfaces the same conceptual state via `manage-logging` records and the terminal user message).

Two doc-format conventions:
- **Markdown workflows** declare `implements:` in YAML frontmatter (`---` block) and document the Output section as `## Output`.
- **AsciiDoc workflows** (`.md` extension, AsciiDoc body) declare `:implements:` as an AsciiDoc attribute at the top of the file and document the Output section as `== Output`.

A skill MAY hold zero, one, or many `workflow/*.md` files. A SKILL.md MAY itself implement the ext-point when the skill's primary deliverable is one workflow (e.g., the six phase-N skills). When both apply, SKILL.md typically describes the skill and points at one or more `workflow/*.md` implementors that carry the actual dispatch bodies.

**Cross-phase / multi-consumer placement rule**: when a workflow is consumed from multiple phases or from outside any phase (e.g., `triage`, `q-gate-validation`, `research-best-practices`, `enrich-module`), place it under `plan-marshall/skills/plan-marshall/workflow/` rather than under any single consumer phase. Single-phase workflows live under the consumer phase's `skill/workflow/`.

### Input Contract — what the implementor can rely on

Every dispatch into the implementor delivers, via the parent dispatcher (`plan-marshall:execution-context-{level}`):

| Field | Always present | Description |
|-------|:--------------:|-------------|
| `plan_id` | Yes | Plan identifier; sentinel `none` for free-standing dispatches. |
| `WORKTREE` | Yes | Repo-relative working directory; `.` for main checkout. |
| `skills[]` | Yes | Caller-loaded skills, loaded before the workflow body runs. May be empty. |
| `plan-marshall:dev-general-practices` | Yes (implicit) | Loaded by the dispatcher before any caller-specified skill. |

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

The implementor MUST NOT redeclare `dev-general-practices` in its own steps — the dispatcher loads it implicitly.

## Plugin-Doctor Enforcement

Lint rule `workflow-doc-implements-contract`:

- Every file whose frontmatter declares `implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow` MUST also declare an Output section containing at minimum the `status` and `display_detail` fields.
- Implementors MUST NOT carry the redundant "Dispatched via Task:…" prose anywhere in their body.
- Files under `*/workflow/*.md` that do NOT carry the `implements:` declaration are presumed to be orchestrator / reference workflows; the rule does not require conformance from them, but the marketplace inventory surfaces them separately so the distinction is visible.

The rule is enumerable via filesystem glob plus a single frontmatter check, making it cheap to run as part of the marketplace quality gate.

## Cross-references

- [`ext-point-dynamic-level-executor`](ext-point-dynamic-level-executor.md) — companion ext-point for the agent side.
- [`agents/execution-context.md`](../../../agents/execution-context.md) — the dispatcher that loads workflow-doc implementors.
