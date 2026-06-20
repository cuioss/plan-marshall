# 06 — Execution-Context Cross-Target Mapping

## Objective

Document the known divergences between the Claude Code and OpenCode targets for the
execution-context agent — what is correct, what differs by design, and what are known
emitter gaps — so that future workstreams (02 validation, 05 documentation) have a
single reference for the current state.

## Status

All items are **known and triaged** — no action required before 02 validation begins.
This document is a reference, not a task list.

---

## One Generic Dispatcher

Both targets emit a single `execution-context.md` agent file. The OpenCode frontmatter
uses `mode: subagent` with a `permission:` block (per-tool allow/deny) instead of
Claude's `tools:` comma list and `forwards_tool_capabilities: true`. The prompt-body
contract (five fields + workflow-specific inputs) and the six-step dispatch sequence
are identical on both targets.

**Status**: Correct — no change needed.

## Level Variants (OpenCode: Deferred to Runtime)

The Claude target emits 6-7 level-suffixed variant agent files (`execution-context-level-1`
through `level-7`) with `model:` baked into frontmatter. The resolver picks which variant
to dispatch based on `marshal.json` effort settings.

The OpenCode target **does not** emit level variants. OpenCode has no `model:` field in
agent frontmatter and no established level-variant dispatch mechanism. Model selection is
deferred to OpenCode's native runtime — the same single `execution-context.md` agent is
dispatched regardless of effort level. If OpenCode's runtime later gains a model-pinning
equivalent, the emitter can be extended to produce variants at that point.

This means the `manage-config effort resolve-target` resolver still works (it is a
shared script), but on OpenCode it always returns the canonical agent name; the
orchestrator dispatches `execution-context.md` unconditionally.

**Status**: Deferred to runtime — known divergence, accepted.

## Skill Loading (Known Emitter Gap)

Step 2 of the dispatch sequence (Load Foundational Practices) is correctly transformed
to the OpenCode `skill` tool syntax:

```
Call the `skill` tool with `{ name: "plan-marshall-dev-agent-behavior-rules" }` before continuing.
```

Step 3 (Load Caller-Specified Skills) still uses Claude's `Skill:` directive, which is
not a valid OpenCode construct:

```
Skill: <entry>
```

This is a known emitter gap in `marketplace/targets/opencode/body_transforms.py` — the
`Skill:` directive transformer only handles isolated directives, not the loop-body
pattern used in agent files.

**Status**: Known emitter gap — the loop-body pattern needs a dedicated transform rule.

## `Task:` vs `task` Tool References (Known Emitter Gap)

The leaf constraint in Step 5, the enforcement section, and the dispatch lifecycle
description reference `Task:` dispatch — the Claude Code tool name. OpenCode's
equivalent is the `task` tool. The agent body text in the OpenCode target should use
`task` instead of `Task:`. This is a known emitter gap — the body transformer does not
rewrite `Task:` references.

**Status**: Known emitter gap — a `Task:` → `task` rewrite rule needs to be added to
the body transformer.

## Permissions vs Tools List

Claude frontmatter:
```yaml
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill
forwards_tool_capabilities: true
```

OpenCode frontmatter (correct):
```yaml
mode: subagent
permission:
  bash: allow
  edit: allow
  glob: allow
  grep: allow
  question: allow
  read: allow
  skill: allow
```

The OpenCode `permission:` block covers all tools the dispatcher needs. Missing tools
(e.g., `Write` is covered by `edit: allow`) are equivalent.

**Status**: Correct — no change needed.

## Summary

| Aspect | Claude | OpenCode | Status |
|--------|--------|----------|--------|
| Agent format | `tools:` + `forwards_tool_capabilities` | `mode: subagent` + `permission:` | Correct |
| Level variants | 6-7 model-pinned files | Single file, no model pinning | Deferred to runtime |
| Skill load (step 2) | `Skill:` directive | `skill` tool | Correct |
| Skill load (step 3) | `Skill: <entry>` | `Skill: <entry>` (not transformed) | Emitter gap |
| `Task:` references | Correct | `Task:` not rewritten to `task` | Emitter gap |
| Prompt-body contract | 5 fields + extras | 5 fields + extras | Correct |
| TOON return contract | Same | Same | Correct |
| `resolve-target` | Returns level variant name | Returns canonical name | Works, always canonical |

## Related

- [02 — Validate the OpenCode runtime](02-validate-opencode-runtime.md) — live validation of these divergences
- [05 — OpenCode documentation](05-opencode-documentation.md) — user-facing docs for the OpenCode target
- `marketplace/targets/opencode/` — emitter and transforms
- `marketplace/bundles/plan-marshall/agents/execution-context.md` — canonical source agent
