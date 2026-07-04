# 06 — Execution-Context Cross-Target Mapping

## Objective

Record how the `execution-context` dispatcher maps across the Claude Code and OpenCode
targets — what is already correct, what diverges by design, and what is an unbuilt
**emitter gap** (work the OpenCode target could do but does not yet). This is a reference
for workstreams [01](01-finish-portability.md) and [02](02-validate-opencode-runtime.md);
it also carries two concrete open tasks (the OpenCode variant emitter and the step-3
skill-load prose rewording).

The single source agent is `marketplace/bundles/plan-marshall/agents/execution-context.md`.
Both targets derive their output from it.

---

## One generic dispatcher

Both targets emit a single `execution-context` agent. The prompt-body contract (five
required fields plus workflow-specific inputs) and the six-step dispatch sequence are
identical on both. The frontmatter differs by target: Claude uses a `tools:` comma list
plus `forwards_tool_capabilities: true`; OpenCode uses `mode: subagent` with a
per-tool `permission:` block.

**Correct — no change needed.**

## Permissions vs. tools list

Claude frontmatter:

```yaml
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill
forwards_tool_capabilities: true
```

OpenCode frontmatter, produced by `transform_agent_frontmatter`
(`marketplace/targets/opencode/frontmatter.py`) via `mapping.json::tool_permissions`:

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

`Write` maps to `edit`, so the set is equivalent. **Correct — no change needed.**

## Level variants and model pinning (emitter gap, not a platform limitation)

This is the section that was previously wrong and is the reason this document exists.

**What Claude does.** The canonical agent declares
`implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor`
and carries **no** `model:`/`effort:` (a canonical with those fields is rejected by
`validate_canonical` in `marketplace/targets/claude/variant_emitter.py`). At build time the
Claude variant emitter walks `LEVEL_TABLE` and writes the canonical plus seven
`execution-context-level-1 … level-7` files, injecting `model:` and `effort:` per level:

| Level | model | effort |
|-------|-------|--------|
| level-1 | haiku | — |
| level-2 | sonnet | medium |
| level-3 | sonnet | high |
| level-4 | opus | medium |
| level-5 | opus | high |
| level-6 | opus | xhigh |
| level-7 | fable | max |

The resolver (`manage-config effort resolve-target`) picks which variant the orchestrator
dispatches based on `marshal.json` effort settings.

**What OpenCode does.** The OpenCode emitter (`marketplace/targets/opencode/emitter.py`,
`_emit_agent`) writes **one** agent file per canonical source. It does not run any
variant emitter — there is no OpenCode counterpart to `variant_emitter.py`. Because the
canonical source carries no `model:`, the emitted OpenCode `execution-context` ends up
with no model pinning either.

**Why the previous "OpenCode has no `model:` field / deferred to runtime" framing was
wrong.** OpenCode agents *do* support a `model:` field (`model: provider/model-id`, e.g.
`anthropic/claude-opus-4-8`), and plan-marshall's OpenCode frontmatter transformer
**already emits it**: `transform_agent_frontmatter` resolves a source `model` alias
through `mapping.json::model_map` and writes `model: anthropic/<id>`
(`frontmatter.py`, the `model_value` / `_resolve_model` path). `mapping.json::model_map`
already lists the concrete ids (`opus → claude-opus-4-8`, `sonnet → claude-sonnet-4-6`,
`haiku → claude-haiku-4-5-20251001`, `fable → claude-fable-5`) with a `supports_effort`
array per alias. The user-invocable command wrapper emits a model the same way. The
missing piece is therefore the **variant emission step on the OpenCode side**, not any
OpenCode capability.

**Configurable model-per-level is possible today.** The two tables needed already exist:
`LEVEL_TABLE` (level → model alias + effort) and `mapping.json::model_map`
(alias → concrete `provider/id` + `supports_effort`). An OpenCode variant emitter would
iterate `LEVEL_TABLE`, resolve each alias through `model_map`, and emit
`execution-context-level-N` files with a concrete `model:` line — reusing the same
build-time tables the Claude target already uses. The model dimension is fully mappable.

**The one real fidelity caveat is effort, not model.** `LEVEL_TABLE` distinguishes
level-4/5/6 *only* by effort (all three are `opus`). OpenCode has no first-class `effort:`
field, but it forwards unrecognised frontmatter keys to the provider, so a level's effort
can be carried as a provider-passthrough option (`reasoningEffort`, or the Claude
`thinking` / `budgetTokens` shape). Levels that differ by **model** (haiku / sonnet / opus /
fable) are distinguishable from the model line alone; the opus-effort tiers need the
passthrough option to stay distinct, or they collapse to a single agent.

**Emitter gap with a bounded fix — see "Open work" below.**

## Skill loading

Step 2 of the dispatch sequence (load `persona-plan-marshall-agent`) uses a concrete
`Skill: plan-marshall:persona-plan-marshall-agent` directive. The OpenCode body transform
(`rewrite_skill_directives` in `marketplace/targets/opencode/body_transforms.py`) rewrites
it to:

```text
Call the `skill` tool with `{ name: "plan-marshall-persona-plan-marshall-agent" }` before continuing.
```

**Step 2: correct.**

Step 3 (load caller-specified skills) iterates `skills[]` and shows `Skill: <entry>`. This
line is **not** rewritten. The reason is precise: the body transform is a per-line regex
(`SKILL_DIRECTIVE_RE`) that matches a concrete `bundle:skill` identifier; `<entry>` is a
runtime placeholder, not an identifier, so it cannot match — and even a matching transform
would leave the surrounding "For each entry in `skills[]` …" prose Claude-specific. The fix
is to reword that instructional prose so it reads target-neutrally (e.g. "load each entry
with the platform's skill-loading mechanism"), **not** to add a regex rule for a
placeholder.

**Step 3: divergence — fix is prose, not a transform rule.**

## `Task:` vs `task` tool references

The dispatcher body references `Task:` (the Claude tool name) in its leaf constraint, its
enforcement section, and its lifecycle description. OpenCode's equivalent tool is `task`.

A blanket `Task:` → `task` rewrite is **risky for this specific agent**: its entire purpose
is that it is a leaf that must *not* dispatch ("no `Task:` dispatch", "every plan-marshall
`Task:` invocation"). These are descriptive references, and a careless substitution
corrupts them.

This is now a **settled, recorded decision**: the idiom registry
(`mapping.json::body_idiom_rewrites`, applied by `rewrite_registered_idioms` in
`body_transforms.py`) declares `Task:` with the `preserve` disposition — the references are
deliberately left intact on OpenCode, with the leaf-aware rationale recorded in
`transforms.md`. The same registry rewrites `AskUserQuestion` → `question`
(`rewrite_inline_code`) and marks `Skill: <entry>` as `source_fix` (item 2 below).

**Settled — `preserve` disposition in the idiom registry.**

## Summary

| Aspect | Claude | OpenCode | State |
|--------|--------|----------|-------|
| Agent format | `tools:` + `forwards_tool_capabilities` | `mode: subagent` + `permission:` | Correct |
| Permissions | tools list | `permission:` block (`Write`→`edit`) | Correct |
| Level variants | 7 model+effort-pinned files via `variant_emitter.py` | single file, no variant emitter | Emitter gap (open) |
| Model pinning | `model:` per variant | `model:` supported and already emitted *when present*; canonical carries none | Emitter gap (open) |
| Effort pinning | `effort:` per variant | no native field; provider-passthrough only | Fidelity caveat |
| Skill load (step 2) | `Skill:` directive | rewritten to `skill` tool | Correct |
| Skill load (step 3) | `Skill: <entry>` placeholder + loop prose | `source_fix` disposition recorded; source not yet reworded | Prose fix (open) |
| `Task:` references | native tool name | `preserve` disposition in the idiom registry | Settled |
| Prompt-body / TOON contract | 5 fields + extras | identical | Correct |
| `resolve-target` | returns level-variant name | returns canonical name (no variants emitted) | Follows the emitter gap |

## Open work

1. **OpenCode variant emitter.** Add an OpenCode counterpart to
   `marketplace/targets/claude/variant_emitter.py` that, for any agent declaring
   `implements: …ext-point-dynamic-level-executor`, emits `execution-context-level-N`
   agent files with a concrete `model:` resolved from `LEVEL_TABLE` + `mapping.json::model_map`.
   Decide how to express each level's effort (provider-passthrough `reasoningEffort` /
   `thinking` budget) or document that opus-effort tiers collapse on OpenCode. This is the
   prerequisite for verification check 2.2d in
   [02-verification-protocol.md](02-verification-protocol.md) ("`level-N` variant
   resolution").

2. **Step-3 skill-load prose.** Reword the "For each entry in `skills[]` … `Skill: <entry>`"
   block in `agents/execution-context.md` so the OpenCode body transform is unnecessary and
   the instruction is target-neutral. The idiom registry already records the `source_fix`
   disposition for this placeholder; the source rewording itself is the open piece.
   (Source-side change; folds into [01](01-finish-portability.md) prose cleanup.)

(The former third item — deciding the `Task:` treatment — is resolved: the registry's
`preserve` disposition with leaf-aware rationale, see the `Task:` section above.)

## Related

- [01 — Finish portability gaps](01-finish-portability.md) — source-side prose items (2, 3)
- [02 — Validate the OpenCode runtime](02-validate-opencode-runtime.md) and its
  [verification protocol](02-verification-protocol.md) — live confirmation of the
  `task`-dispatch and variant-resolution behaviour
- `marketplace/targets/claude/variant_emitter.py` — the Claude variant emitter to mirror
- `marketplace/targets/opencode/frontmatter.py`, `emitter.py`, `mapping.json` — the
  OpenCode transform, emitter, and model map
- `marketplace/bundles/plan-marshall/agents/execution-context.md` — the canonical source agent
