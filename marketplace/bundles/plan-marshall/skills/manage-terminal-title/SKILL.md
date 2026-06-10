---
name: manage-terminal-title
description: Pure platform-agnostic terminal-title composition consumed by platform-runtime via PYTHONPATH
user-invocable: false
---

# Manage Terminal Title

Pure, platform-agnostic terminal-title composition. This is a **library skill**
with no user-facing workflow and no CLI entry point — its single module is
imported via PYTHONPATH by `platform-runtime`, mirroring how `script-shared`
modules are consumed.

`manage_terminal_title.py` owns the title-composition contract: the body-format
function, the `TITLE_TOKEN_GLYPHS` lock/build-state glyph map, the icon palette +
event→icon resolver, and the pure `compose(state_dict, event)` function. It is a
**leaf library** — it imports NEITHER `manage-status` NOR `platform-runtime`.
`platform-runtime` imports it one-directionally to render the title string after
it has read `status.json`.

## Enforcement

**Execution mode**: `script-deterministic` library — no LLM, no CLI dispatch.
The composer is a pure function imported and called by `platform-runtime`.

**Prohibited actions:**
- Do not perform filesystem or network I/O inside the composer — `compose` and
  its helpers operate solely on the passed `state_dict`. The caller
  (`platform-runtime`) owns all reads of `status.json` and all emission.
- Do not import `manage-status` or `platform-runtime` — the module is a leaf in
  the dependency graph; the only permitted direction is `platform-runtime` →
  `manage-terminal-title`.
- Do not add a CLI entry point or register a 3-part script notation — this skill
  is a library consumed by import, not by `execute-script.py`.

**Constraints:**
- The icon palette, glyph vocabulary, and body-format are owned here exclusively;
  consumers (e.g. `platform-runtime`) MUST consume them via import rather than
  re-declaring them.
- Strictly comply with all rules from `dev-agent-behavior-rules`.

## Composition Contract

`compose(state_dict, event, icon_override=None, tool_name=None) -> str | None`
composes `'{icon} {glyph} {body}'`. It is pure — no I/O. The three inputs are
independent:

### Body

`_compose_body(state_dict)` renders the body from `current_phase` and the
optional `short_description`:

| Condition | Body |
|-----------|------|
| Active phase, `short_description` present | `pm:{phase}:{short}` |
| Active phase, no `short_description` | `pm:{phase}` |
| Terminal phase (`complete` / `archived`), `short` present | `pm:Completed:{short}` |
| Terminal phase, no `short` | `pm:Completed` |
| `current_phase` empty / missing | `None` (true no-op) |

A terminal phase renders the Completed body — NOT `None` — so a finished plan
still shows in the title (with the ✅ override below).

### Glyph (`TITLE_TOKEN_GLYPHS`)

The `title_token` lock/build-state glyph, prepended when the field is set:

| State | Glyph |
|-------|-------|
| `lock-waiting` | ⏳ |
| `lock-owned` | 🔒 |
| `build-waiting` | 🕐 |
| `building` | 🔨 |

`manage-status` persists only the bare state string in the `title_token` field;
this map is the single owner of the state→glyph rendering. The glyph is omitted
(`'{icon} {body}'`) in two cases:

- No `title_token` is set in the plan state.
- `current_phase` is a terminal phase (`complete` / `archived`) — a finished
  plan holds no live lock/build state, so the glyph is suppressed regardless of
  any persisted `title_token` value. The suppression is token-agnostic: all four
  `TITLE_TOKEN_GLYPHS` states (⏳/🔒/🕐/🔨) are uniformly suppressed for a
  terminal plan.

### Icon (`resolve_icon` + terminal override)

`resolve_icon(event, tool_name=None)` maps the hook event to the process icon:

| Event | Icon |
|-------|------|
| `UserPromptSubmit` / `SessionStart` / `PostToolUse` (any tool) / default | ➤ active |
| `Notification` / `PreToolUse:AskUserQuestion` | ? waiting |
| `Stop` | ✓ done |

**Terminal-state override:** when `state_dict['current_phase']` is `complete` or
`archived`, `compose` forces the icon to ✅ (`_ICON_TERMINAL`, U+2705 — the thick
check-mark, distinct from the thin ✓ `_ICON_DONE`) regardless of the hook event
or `icon_override`. The process icons ➤ (active) and ? (waiting) MUST NOT appear
for a finished plan.

For non-terminal phases, `icon_override` (push-mode) supersedes the event-resolved
icon when provided.

## Library Consumption

The module is imported via PYTHONPATH the same way `script-shared` modules are
(the executor's PYTHONPATH generation scans immediate subdirectories of each
`scripts/` directory). `platform-runtime` imports it as:

```python
from manage_terminal_title import compose, resolve_icon, TITLE_TOKEN_GLYPHS
```

This skill is registered in `plugin.json` per the library-skill convention (same
as `script-shared`): `user-invocable: false`, context-loaded / library, no 3-part
script notation.

## Related Skills

- `plan-marshall:platform-runtime` — the one-directional consumer: resolves
  session→plan, reads `status.json`, calls `compose`, and emits per platform.
- `plan-marshall:script-shared` — the analogous PYTHONPATH-imported library skill.
