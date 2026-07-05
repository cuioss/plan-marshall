# OpenCode Body Transforms

This document is the authoritative spec for the line-level body
transforms applied to OpenCode-emitted bodies. All three transforms are
**data-driven**: the applier is the target-shared engine
`marketplace/targets/body_transform_engine.py`, and every per-target
rewrite *template* / disposition lives as data in this target's
`mapping.json`. Adding a new transform is a deliberate spec change: the
engine does not silently rewrite anything the rule data does not
declare.

## The shared engine and its data

The engine owns the **matchers** — the "Claude source vocabulary": how
each source idiom is found (`SKILL_DIRECTIVE_RE`, the slash-command
regex, the inline-backtick registered-idiom form). Each target's
`mapping.json` supplies only the replacement *data*:

| `mapping.json` key | Transform | Data supplied |
|--------------------|-----------|---------------|
| `directive_rewrites.skill_directive.template` | 1 | `Skill:`-directive rewrite string (`{bundle}` / `{skill}` placeholders) |
| `slash_rewrites.slash_command.template` | 2 | slash-command rewrite string (`{name}` placeholder) |
| `body_idiom_rewrites` | 3 | registered-idiom dispositions |

A target that declares **none** of these is *verbatim* — the engine
applies no transform and the emitted body is byte-identical to source.
The canonical Claude target is verbatim by construction (it has no
`mapping.json`), which keeps its output independently
equality-validatable. A **new target supplies only this data** — no
transform code. See
[07 — Target Extensibility](../../../doc/refactor/07-target-extensibility.md)
§ structural item 3.

## Transform 1 — `Skill:` directive rewrite

Claude Code's runtime intercepts `Skill: {bundle}:{skill}` directives
and loads the named skill into context. OpenCode does not — its `skill`
tool is LLM-driven, not runtime-parsed. Without rewriting, the `Skill:`
line is just text the LLM may or may not act on.

| Match in source body (engine-owned matcher) | Rewrite template (`mapping.json::directive_rewrites`) |
|----------------------------------------------|-------------------------------------------------------|
| `^Skill:\s+{bundle}:{skill}\s*$` (full line) | `` Call the `skill` tool with `{ name: "{bundle}-{skill}" }` before continuing. `` |

The regex is anchored to a full line (`^...$`, MULTILINE) so inline
backtick references like `` `Skill: foo:bar` `` in prose are
unaffected. The template's `{bundle}` / `{skill}` placeholders are
substituted from the matched directive; the `{bundle}-{skill}`
namespacing matches the skill directories the emitter produces so the
load target always resolves.

**Idempotence:** The rewritten line does not match the source pattern,
so re-running the transform on already-transformed text is a no-op.

## Transform 2 — Slash-command rewrite

Claude Code skills with `user-invocable: true` are invoked as
`/skill-name`. On OpenCode, the dual-emit places them under
`command/{bundle}-{skill}.md`, invoked as `/{bundle}-{skill}`.
Cross-references in skill bodies and usage examples must be rewritten
to the namespaced form.

**Build-time lookup table.** The engine walks every source skill with
`user-invocable: true` and builds a global map
`{skill-name → {bundle}-{skill-name}}` across all bundles, not
per-bundle. The lookup is provided by
`build_user_invocable_lookup(marketplace_dir)`.

**Body regex (engine-owned matcher):**

```
(?<![\w-])/(?P<name>{any-known-skill-name})(?=\s|$|=)
```

* `(?<![\w-])` — lookbehind avoids matching inside paths
  (`path/to/foo`) or compound identifiers.
* `(?P<name>...)` — alternation over names from the lookup table.
* `(?=\s|$|=)` — lookahead permits the form `/skill action=...` used
  in usage examples.

The rewrite *template* lives in
`mapping.json::slash_rewrites.slash_command.template` (`/{name}`); its
`{name}` placeholder is substituted with the resolved namespaced form
`{bundle}-{skill-name}` from the lookup. Names already in namespaced
form pass through unchanged because the regex only matches the bare
names listed in the lookup. A target using a different invocation form
declares a different template (e.g. `#{name}`) — no code change.

**Argument syntax stays as-is.** Both Claude and OpenCode pass the
post-command tail to the LLM as a string; the body's natural-language
`key=value` parsing is LLM-driven on both targets, so no further
transform is required.

**Idempotence:** Rewritten slashes are already namespaced; the regex
does not match them on a second pass.

## Transform 3 — Registered-idiom rewrite (data-driven)

The source stays Claude-native. Claude-native tool idioms that diverge
on OpenCode are registered as per-target rewrite **data** in
`mapping.json::body_idiom_rewrites`, and the shared engine
(`rewrite_registered_idioms`) applies each idiom's *disposition*. This
keeps the divergence in one declarative place rather than scattered
inline string replaces, and lets the build **fail closed** when a new
Claude idiom is registered without an engine-handled disposition.

**Registry shape** (`mapping.json::body_idiom_rewrites`):

```json
{
  "AskUserQuestion": { "disposition": "rewrite_inline_code", "opencode_tool": "question" },
  "Task:":           { "disposition": "preserve" },
  "Skill: <entry>":  { "disposition": "source_fix" }
}
```

**Dispositions** (the closed set the engine honours):

| Disposition | Engine behaviour |
|-------------|------------------|
| `rewrite_inline_code` | Rewrite the backtick-wrapped tool reference `` `{idiom}` `` → `` `{opencode_tool}` ``. Bare prose mentions of the concept are left alone. |
| `preserve` | A deliberate non-rewrite — the body is unchanged. |
| `source_fix` | The divergence is fixed in the source, not at emit time — the body is unchanged. |

**Fail-closed.** `load_transform_rules` validates the registry up-front
via `assert_dispositions_known`: any registered idiom whose `disposition`
is missing or not one of the three above raises `UnmappedIdiomError` at
build time. A new Claude idiom therefore cannot be added to the registry
(or emitted) without an explicit, engine-handled disposition.

**Idempotence.** A `rewrite_inline_code` whose replacement is already
present does not re-match — the source idiom name no longer appears in
that backtick span.

### Disposition of the three registered idioms

| Idiom | Disposition | Rationale |
|-------|-------------|-----------|
| `AskUserQuestion` (313× across bodies) | `rewrite_inline_code` → `` `question` `` | OpenCode's escalation tool is `question`/`ask`. Only the backtick-wrapped tool reference is rewritten; bare prose mentions of the escalation *mechanism* stay as the concept name (a blanket rewrite would corrupt prose). |
| `Task:` | `preserve` | **Leaf-aware** (doc 06 item 3). The dispatcher's leaf-constraint prose — "no `Task:` dispatch", "every plan-marshall `Task:` invocation" — is descriptive, and a blanket `Task:` → `task` rewrite corrupts it. The divergence is real terminology drift, dispositioned here as a deliberate non-rewrite rather than a naive substitution. |
| `Skill: <entry>` | `source_fix` | The `<entry>` is a runtime placeholder, not an identifier (doc 06 item 2). The one true source change — the placeholder-loop prose (the step-3 skill-load loop in `agents/execution-context.md`) is reworded target-neutrally, so no emit-time rewrite is needed. |

## What is *not* transformed

The emitter does **not** rewrite:

* Bare prose mentions of tool names (`AskUserQuestion`, `EnterPlanMode`,
  etc.) outside a backtick tool reference — only the registered
  `rewrite_inline_code` backtick form is rewritten (Transform 3);
  everything else is source-side cleanup or a deliberate `preserve` /
  `source_fix` disposition.
* `.claude/` paths or hook event names in prose.
* Argument syntax (`key=value` vs `$ARGUMENTS`) — neither runtime
  parses these; both pass them as a string to the LLM.

Body transforms are reserved for cases where the same source line has
different meaning on the two targets and the LLM cannot bridge the gap
by itself. Everything else is either source-cleaned or left alone.

## Fail-closed on an unmapped structural source idiom

Transforms 1 and 2 rewrite the two *structural* source idioms
(`skill_directive`, `slash_command`). The engine registers these as its
Claude source vocabulary and, for any **non-verbatim** target (one that
declares at least one rewrite category), requires a non-empty template
for each — `assert_source_vocabulary_mapped` raises `UnmappedIdiomError`
when one is missing. This is the same fail-closed discipline as
`UnmappedToolError` for frontmatter tools and `assert_dispositions_known`
for Transform 3: a target cannot partially opt into rewriting and
silently leave a known Claude source idiom un-rewritten. A verbatim
target (no rewrite category — the canonical Claude target) is exempt and
emits source bytes unchanged.

## Public API

The shared engine (`marketplace/targets/body_transform_engine.py`)
exposes:

| Symbol | Purpose |
|--------|---------|
| `rewrite_skill_directives(body, template)` | Apply Transform 1 with the supplied `directive_rewrites` template. |
| `rewrite_slash_commands(body, lookup, template)` | Apply Transform 2 with the supplied lookup and `slash_rewrites` template. |
| `rewrite_registered_idioms(body, registry)` | Apply Transform 3 with the supplied idiom registry. |
| `load_transform_rules(mapping_path)` | Load + fail-closed-validate all three rule categories into a `TransformRules`. |
| `assert_dispositions_known(registry)` | Fail-closed guard: raise `UnmappedIdiomError` on any unknown Transform-3 disposition. |
| `assert_source_vocabulary_mapped(rules)` | Fail-closed guard: raise `UnmappedIdiomError` when a non-verbatim target omits a structural template. |
| `build_user_invocable_lookup(marketplace_dir)` | Scan source bundles for `user-invocable: true` skills. |
| `make_body_transformer(lookup, rules)` | Compose Transforms 1 + 2 + 3 into a `BodyTransformer` callable matching the emitter's contract; a verbatim `rules` yields an identity transform. |

The target is wired up via:

```python
from marketplace.targets.body_transform_engine import (
    build_user_invocable_lookup,
    load_transform_rules,
    make_body_transformer,
)
from marketplace.targets.opencode.emitter import emit_bundles

rules = load_transform_rules(config_dir / 'mapping.json')
lookup = build_user_invocable_lookup(marketplace_dir)
transformer = make_body_transformer(lookup, rules)
emit_bundles(marketplace_dir, output_dir, config_dir, body_transformer=transformer)
```
