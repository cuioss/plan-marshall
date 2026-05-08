# OpenCode Body Transforms

This document is the authoritative spec for the line-level body
transforms applied by the OpenCode emitter. The implementation lives in
`body_transforms.py` (snake-case for Python import — see Note on
filename below). Adding a new transform is a deliberate spec change:
the emitter does not silently rewrite anything else.

## Note on filename

Cluster 02 plan.md and the wider design narrative refer to this module
as `body-transforms.py`. Python rejects hyphens in importable module
names, so the on-disk filename uses snake-case (`body_transforms.py`).
External documentation may use either form interchangeably; treat
`body-transforms.py` as the design name and `body_transforms.py` as the
filesystem name.

## Transform 1 — `Skill:` directive rewrite

Claude Code's runtime intercepts `Skill: {bundle}:{skill}` directives
and loads the named skill into context. OpenCode does not — its `skill`
tool is LLM-driven, not runtime-parsed. Without rewriting, the `Skill:`
line is just text the LLM may or may not act on.

| Match in source body | Rewrite in OpenCode body |
|----------------------|--------------------------|
| `^Skill:\s+{bundle}:{skill}\s*$` (full line) | `` Call the `skill` tool with `{ name: "{bundle}-{skill}" }` before continuing. `` |

The regex is anchored to a full line (`^...$`, MULTILINE) so inline
backtick references like `` `Skill: foo:bar` `` in prose are
unaffected. The replacement uses the same `{bundle}-{skill}`
namespacing the emitter produces for skill directories so the load
target always resolves.

**Idempotence:** The rewritten line does not match the source pattern,
so re-running the transform on already-transformed text is a no-op.

## Transform 2 — Slash-command rewrite

Claude Code skills with `user-invocable: true` are invoked as
`/skill-name`. On OpenCode, the dual-emit places them under
`command/{bundle}-{skill}.md`, invoked as `/{bundle}-{skill}`.
Cross-references in skill bodies and usage examples must be rewritten
to the namespaced form.

**Build-time lookup table.** The emitter walks every source skill with
`user-invocable: true` and builds a global map
`{skill-name → {bundle}-{skill-name}}` across all bundles, not
per-bundle. The lookup is provided by
`build_user_invocable_lookup(marketplace_dir)`.

**Body regex:**

```
(?<![\w-])/(?P<name>{any-known-skill-name})(?=\s|$|=)
```

* `(?<![\w-])` — lookbehind avoids matching inside paths
  (`path/to/foo`) or compound identifiers.
* `(?P<name>...)` — alternation over names from the lookup table.
* `(?=\s|$|=)` — lookahead permits the form `/skill action=...` used
  in usage examples.

The replacement is `/{bundle}-{skill-name}`. Names already in
namespaced form pass through unchanged because the regex only matches
the bare names listed in the lookup.

**Argument syntax stays as-is.** Both Claude and OpenCode pass the
post-command tail to the LLM as a string; the body's natural-language
`key=value` parsing is LLM-driven on both targets, so no further
transform is required.

**Idempotence:** Rewritten slashes are already namespaced; the regex
does not match them on a second pass.

## What is *not* transformed

The emitter does **not** rewrite:

* Tool-name mentions in prose (`AskUserQuestion`, `EnterPlanMode`,
  etc.) — addressed by source-side cleanup, not at emit time.
* `.claude/` paths or hook event names in prose.
* Argument syntax (`key=value` vs `$ARGUMENTS`) — neither runtime
  parses these; both pass them as a string to the LLM.

Body transforms are reserved for cases where the same source line has
different meaning on the two targets and the LLM cannot bridge the gap
by itself. Everything else is either source-cleaned or left alone.

## Public API

The module exposes:

| Symbol | Purpose |
|--------|---------|
| `rewrite_skill_directives(body)` | Apply Transform 1 only. |
| `rewrite_slash_commands(body, lookup)` | Apply Transform 2 with the supplied lookup. |
| `build_user_invocable_lookup(marketplace_dir)` | Scan source bundles for `user-invocable: true` skills. |
| `make_body_transformer(lookup)` | Compose Transform 1 + Transform 2 into a `BodyTransformer` callable matching the emitter's contract. |

The emitter is wired up via:

```python
from marketplace.targets.opencode.body_transforms import (
    build_user_invocable_lookup,
    make_body_transformer,
)
from marketplace.targets.opencode.emitter import emit_bundles

lookup = build_user_invocable_lookup(marketplace_dir)
transformer = make_body_transformer(lookup)
emit_bundles(marketplace_dir, output_dir, config_dir, body_transformer=transformer)
```
