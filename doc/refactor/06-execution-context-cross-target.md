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
`_emit_agent`) writes the canonical no-suffix agent file (which, because the source carries
no `model:`, correctly has no model pinning — the `inherit` behaviour) **and** now routes
role-eligible canonicals through `marketplace/targets/opencode/variant_emitter.py`, the
counterpart to the Claude `variant_emitter.py`. That emitter writes the seven
`execution-context-level-N` files with a concrete `model: anthropic/<id>` per level. See
"Open work" item 1 below for the full contract, including the effort passthrough.

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
level-2/3 (both `sonnet`) and level-4/5/6 (all `opus`) *only* by effort. OpenCode has no
first-class `effort:` field, but it forwards unrecognised frontmatter keys to the provider,
so the emitter carries each level's effort as a provider-passthrough `reasoningEffort:
<effort>` key. Levels that differ by **model** (haiku / sonnet / opus / fable) are
distinguishable from the model line alone; the same-model tiers rely on the passthrough to
stay distinct (without it they would collapse to byte-identical files). The passthrough is
unvalidated on a live runtime — see "Open work" item 1 for the decision and caveat.

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
| Level variants | 7 model+effort-pinned files via `variant_emitter.py` | 7 model-pinned files via `opencode/variant_emitter.py` (mirrors the Claude emitter, reuses `LEVEL_TABLE`) | Resolved |
| Model pinning | `model:` per variant | `model: anthropic/<id>` per variant, resolved through `mapping.json::model_map` | Resolved |
| Effort pinning | `effort:` per variant | `reasoningEffort: <effort>` provider-passthrough per variant (keeps same-model tiers distinct); unvalidated on a live runtime | Passthrough (fidelity caveat) |
| Skill load (step 2) | `Skill:` directive | rewritten to `skill` tool | Correct |
| Skill load (step 3) | `Skill: <entry>` placeholder + loop prose | `source_fix` disposition recorded; source reworded target-neutrally | Resolved |
| `Task:` references | native tool name | `preserve` disposition in the idiom registry | Settled |
| Prompt-body / TOON contract | 5 fields + extras | identical | Correct |
| `resolve-target` | returns level-variant name | returns canonical name (no variants emitted) | Follows the emitter gap |

## Open work

(All items below are resolved; the section is retained as an implementation record.)

1. **OpenCode variant emitter — done.** `marketplace/targets/opencode/variant_emitter.py`
   mirrors the Claude emitter: for any agent declaring
   `implements: …ext-point-dynamic-level-executor` it emits `execution-context-level-N`
   agent files with a concrete `model: anthropic/<id>` resolved from `LEVEL_TABLE` +
   `mapping.json::model_map`. `LEVEL_TABLE` and `ALIAS_GATED_EFFORTS` are *imported* from the
   Claude emitter (not copied) so the two targets cannot drift; the `xhigh`/`max` alias-
   capability gate is the same `supports_effort` check. The emitter is wired into
   `opencode/emitter.py::_emit_agent` and registers each variant in `opencode.json`.
   **Effort decision:** each level's effort is carried as a provider-passthrough
   `reasoningEffort: <effort>` frontmatter key rather than letting the tiers collapse —
   without it the same-model tiers (`level-2`/`level-3` sonnet; `level-4`/`level-5`/`level-6`
   opus) would emit byte-identical files. `level-1` (haiku) carries no effort key. The
   passthrough is unvalidated on a live OpenCode runtime (only Claude Code is a tested
   runtime); if a downstream stack ignores it the same-model tiers degrade to equivalent
   behaviour, but the emitted files stay distinct and independently resolvable — satisfying
   verification check 2.2d in
   [02-verification-protocol.md](02-verification-protocol.md) ("`level-N` variant
   resolution"). Lockstep + emission tests live under
   `test/marketplace/targets/opencode/`.

2. **Step-3 skill-load prose — done.** The "For each entry in `skills[]` … `Skill: <entry>`"
   block in `agents/execution-context.md` now reads target-neutrally ("load that skill into
   context using the platform's skill-loading mechanism"), so no OpenCode body transform is
   needed. The idiom registry already recorded the `source_fix` disposition for this
   placeholder.

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
