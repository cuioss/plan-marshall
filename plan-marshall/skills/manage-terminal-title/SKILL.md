---
name: manage-terminal-title
description: Pure platform-agnostic terminal-title composition consumed by platform-runtime via PYTHONPATH — plan-scoped pm:{phase} bodies and orchestrator Orchestrator-{SlugName} bodies
user-invocable: false
mode: knowledge
---

# Manage Terminal Title

Pure, platform-agnostic terminal-title composition. This is a **library skill**
with no user-facing workflow and no CLI entry point — its single module is
imported via PYTHONPATH by `platform-runtime`, mirroring how `script-shared`
modules are consumed.

`manage_terminal_title.py` owns the title-composition contract: the body-format
function, the `TITLE_TOKEN_GLYPHS` lock-state glyph map, the icon palette +
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
- Strictly comply with all rules from `persona-plan-marshall-agent`.

## Composition Contract

`compose(state_dict, event, icon_override=None, tool_name=None) -> str | None`
composes `'{icon} {glyph} {body}'`. It is pure — no I/O. The three inputs are
independent:

### Body

`_compose_body(state_dict)` renders the body from `current_phase` and the
optional `short_description` — or, when the state carries `kind: orchestrator`,
the orchestrator body from the state's `slug`:

| Condition | Body |
|-----------|------|
| Active phase, `short_description` present | `pm:{phase}:{short}` |
| Active phase, no `short_description` | `pm:{phase}` |
| Terminal phase (`complete` / `archived`), `short` present | `pm:Completed:{short}` |
| Terminal phase, no `short` | `pm:Completed` |
| `current_phase` empty / missing | `None` (true no-op) |
| `kind: orchestrator`, `slug` present | `Orchestrator-{SlugName}` |
| `kind: orchestrator`, `slug` empty / missing | `None` (true no-op) |

A terminal phase renders the Completed body — NOT `None` — so a finished plan
still shows in the title (with the ✅ override below).

**Orchestrator body:** when the passed state dict carries `kind: orchestrator`,
the body is `Orchestrator-{SlugName}` (slug from the state's `slug` field)
instead of the plan-scoped `pm:{phase}[:{short}]` form — e.g.
`Orchestrator-token-optimization`. Icon and glyph slots keep their existing
semantics (process icon, `build-busy` 🔨 icon-slot override); only the body
composition branches on the kind, and the composer stays a pure leaf function.
The orchestrator state is read by `platform-runtime`'s `session
push-title-token --store orchestrator --slug {slug}` seam, which resolves the
epic's `status.json` via `get_store_dir('orchestrator', slug)`.

### Glyph (`TITLE_TOKEN_GLYPHS`)

The `title_token` lock-state glyph, prepended when the field is set:

| State | Glyph |
|-------|-------|
| `lock-waiting` | ⏳ |
| `lock-owned` | 🔒 |

`manage-status` persists only the bare state string in the `title_token` field;
this map is the single owner of the state→glyph rendering. The glyph is omitted
(`'{icon} {body}'`) in two cases:

- No `title_token` is set in the plan state.
- `current_phase` is a terminal phase (`complete` / `archived`) — a finished
  plan holds no live lock state, so the glyph is suppressed regardless of
  any persisted `title_token` value. The suppression is token-agnostic: both
  `TITLE_TOKEN_GLYPHS` states (⏳/🔒) are uniformly suppressed for a terminal
  plan.

The `build-busy` title-token is **deliberately absent** from `TITLE_TOKEN_GLYPHS`:
it is rendered as a 🔨 icon-slot override (see Icon below), NOT as a prepended
glyph. Its absence from the map makes glyph suppression automatic —
`TITLE_TOKEN_GLYPHS.get('build-busy')` is `None`, so the glyph-prepend block emits
no glyph segment for it, and an active `build-busy` plan renders `🔨 pm:{phase}`
(icon-slot override, no glyph).

### Icon (`resolve_icon` + terminal override)

`resolve_icon(event, tool_name=None)` maps the hook event to the process icon:

| Event | Icon |
|-------|------|
| `UserPromptSubmit` / `SessionStart` / `PostToolUse` (any tool) / default | ➤ active |
| `Notification` / `PreToolUse:AskUserQuestion` | ? waiting |
| `PreToolUse:Bash` | ⚙ busy |
| `Stop` | ✓ done |

`PreToolUse:Bash` resolves to the ⚙ busy icon (`_ICON_BUSY`, U+2699) — surfaced
while a long-running Bash tool call executes. `PreToolUse:Bash` and
`PostToolUse:Bash` bracket the busy window: the title switches to ⚙ on enter and
falls back to ➤ active on exit (`PostToolUse` for any tool resolves to ➤). The ⚙
busy icon is deliberately distinct from ➤ active, ? waiting, and the two
`TITLE_TOKEN_GLYPHS` lock-state values (⏳ / 🔒).

**Terminal-state override:** when `state_dict['current_phase']` is `complete` or
`archived`, `compose` forces the icon to ✅ (`_ICON_TERMINAL`, U+2705 — the thick
check-mark, distinct from the thin ✓ `_ICON_DONE`) regardless of the hook event
or `icon_override`. The process icons ➤ (active) and ? (waiting) MUST NOT appear
for a finished plan.

**`build-busy` icon-slot override:** when `state_dict['title_token']` is
`build-busy` on an **active** (non-terminal) phase, `compose` forces the icon to
🔨 (`_ICON_BUILD`, U+1F528) — a token-keyed **icon-slot override** (NOT a glyph)
that supersedes both `icon_override` and the resolved process icon for the
duration of the orchestration call, rendering `🔨 pm:{phase}`. The 🔨 build symbol
is deliberately distinct from the ⚙ busy icon: ⚙ is the momentary per-tool busy
state, whereas 🔨 is the persistent orchestration-busy state held for the whole
blocking window. The full icon precedence is **terminal ✅ > build-busy 🔨 >
`icon_override` > process icon** — the terminal ✅ override still wins, so 🔨 never
appears for a finished plan. `build-busy` is set/cleared by the orchestration
layer; see [`persona-plan-marshall-agent`](../persona-plan-marshall-agent/SKILL.md)
for the normative orchestration requirement (when the state is set/cleared and the
live-push mechanics).

For non-terminal phases without a `build-busy` token, `icon_override` (push-mode)
supersedes the event-resolved icon when provided.

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
  session→plan, reads `status.json`, calls `compose`, and emits per platform. It
  owns the single canonical **repaint seam** (`session push-title-token`,
  `--icon` optional) and the relocated **session→plan binding** (`session bind`
  last-driven-wins / `session resolve-plan` / `session doctor`, in
  `session_binding.py`). See
  [`standards/terminal-title-architecture.md`](standards/terminal-title-architecture.md)
  for the full state / compose / emit split, the drive seam, and the binding
  policy.
- `plan-marshall:manage-status` — fires the repaint + bind drive seam
  (`_surface_drive`) after every persisted `current_phase` write, so a phase
  change repaints the title live instead of freezing.
- `plan-marshall:manage-locks` — `merge_lock.py` drives the SAME repaint seam for
  the ⏳/🔒 lock-state surface and a plain icon-less repaint on the release/clear
  path.
- `plan-marshall:script-shared` — the analogous PYTHONPATH-imported library skill.
