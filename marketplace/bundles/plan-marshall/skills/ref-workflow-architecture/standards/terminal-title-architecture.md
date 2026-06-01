# Terminal-Title Architecture

Single canonical reference for the terminal-title feature: how a plan's phase and
short description reach the terminal title bar. The feature is a **writer/reader
split** across two skills — `manage-status` (the writer) publishes a plaintext
title-body artifact on every state mutation, and `platform-runtime` (the reader)
resolves that artifact for the active session and emits the platform-appropriate
title. Neither side imports the other; the `{plan_dir}/title-body.txt` file is the
only contract between them.

## Component Map

```
WRITER (manage-status)                          READER (platform-runtime claude_runtime.py)
┌─────────────────────────────┐                 ┌────────────────────────────────────────────┐
│ _render_title_body          │                 │ session_render_title                         │
│  pm:{phase}[:{short}]        │                 │  1. $CLAUDE_CODE_SESSION_ID                  │
│  (None → delete on terminal) │                 │  2. session cache → active-plan → plan_id    │
└──────────────┬──────────────┘                 │  3. read title-body.txt:                     │
               │ writes                          │     a. live  {plan_dir}/title-body.txt       │
               ▼                                 │     b. fallback                              │
   {plan_dir}/title-body.txt ───────────────────┤        archived-plans/{date}-{plan_id}/...    │
               │                                 │  4. _resolve_icon(hook_event) → {icon}        │
   cmd_archive (Completed body):                 │  5. emit terminalSequence (all events)       │
                                                 │     + sessionTitle (web/desktop, gated)      │
     write pm:Completed:{short} ────────────────►│                                              │
     then shutil.move →                          └────────────────────────────────────────────┘
     archived-plans/{date}-{plan_id}/title-body.txt
```

## Writer — `manage-status`

The writer lives in `manage-status/scripts/_status_core.py` and is invoked from the
plan lifecycle commands in `_cmd_lifecycle.py`. It publishes the title-body artifact
on every state mutation; no re-read of `status.json` is involved — the in-memory
status dict drives the render.

| Element | Location | Role |
|---------|----------|------|
| `_render_title_body(status_data)` | `_status_core.py` | Renders the body string from the in-memory status dict |
| `_publish_title_body(plan_dir, status_data)` | `_status_core.py` | Atomically writes (or deletes) `{plan_dir}/title-body.txt` |
| `TITLE_BODY_FILENAME` | `_status_core.py` | The artifact filename — `title-body.txt` |
| `TITLE_BODY_TERMINAL_PHASES` | `_status_core.py` | `frozenset({'complete', 'archived'})` — phases that delete the artifact |

### Body format

`_render_title_body` returns:

- `pm:{current_phase}:{short_description}` when a `short_description` is present.
- `pm:{current_phase}` when no `short_description` is present.
- `None` when `current_phase` is empty or in `TITLE_BODY_TERMINAL_PHASES` — callers
  treat `None` as the delete-the-file signal.

`_publish_title_body` writes the rendered string atomically (the writer appends
exactly one terminating `\n`) or unlinks the artifact when the render is `None`.
Failures are swallowed silently: the next successful mutation self-heals, and a
missing file is harmless on the read path.

## Title-Body Lifecycle

1. **Active phases** (every phase before terminal): each state mutation calls
   `_publish_title_body`, which rewrites `{plan_dir}/title-body.txt` to
   `pm:{phase}[:{short}]`.
2. **Terminal phases** (`complete` / `archived`): `_render_title_body` returns
   `None`, so the standard mutation path deletes the artifact — "file absent → no
   plan-title to render" is the reader's only conditional.
3. **Archive interaction** (`cmd_archive` in `_cmd_lifecycle.py`): archiving marks
   the active phase done, sets `current_phase = 'complete'` when every phase is done,
   then moves the plan directory to
   `.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/` via `shutil.move`. The
   archive name is built from `date_prefix = now_utc_iso()[:10]` and
   `archive_name = f'{date_prefix}-{plan_id}'`.

### Completed terminal body

The Completed terminal body is the one body that must survive into the archive. To
publish it, `cmd_archive` writes `pm:Completed:{short_description}` to the live
`{plan_dir}/title-body.txt` **before** the `shutil.move`, so the body travels into
`.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/title-body.txt` with the moved
directory. `short_description` is the same title-body name token used by the active
`pm:{phase}:{short}` format. The Completed body is treated as a non-deletable
terminal body so the standard `TITLE_BODY_TERMINAL_PHASES` deletion path does not
erase it before the move.

## Reader — `platform-runtime`

The reader lives in `platform-runtime/scripts/claude_runtime.py` as
`session_render_title`. It performs a five-step resolve-and-emit:

1. **Read `$CLAUDE_CODE_SESSION_ID`** — the session identifier supplied by the
   Claude Code hook environment. Empty → no-op (return nothing).
2. **Resolve session → plan** via the session cache (see Session-Plan Binding
   below). Empty → no-op.
3. **Read the title body** from `title-body.txt`:
   a. Live path: `.plan/local/plans/{plan_id}/title-body.txt`.
   b. Archived-path fallback: when the live path is absent, glob
      `.plan/local/archived-plans/*-{plan_id}/title-body.txt` (archive naming
      `{YYYY-MM-DD}-{plan_id}`) and read the Completed body from there. An empty or
      absent body → no-op.
4. **Pick the icon** via `_resolve_icon(hook_event_name, tool_name)` over the
   canonical palette (see Icon Palette below). statusLine mode receives no hook
   stdin payload and keeps the static active icon; hook mode parses the JSON payload
   Claude Code writes to stdin (best-effort — missing/malformed input defaults to
   the active icon and never raises).
5. **Emit the title** on the appropriate output channel (see Output Channels). Hook
   mode emits a JSON envelope carrying the OSC `terminalSequence` for every event,
   plus a conditional web/desktop `sessionTitle` channel; statusLine mode emits plain
   `{icon} {body}` text.

### Session-Plan Binding

The session identifier is bound to a plan through a filesystem cache rooted at
`_SESSION_CACHE_BASE` (`~/.cache/plan-marshall/sessions`):

```
~/.cache/plan-marshall/sessions/{session_id}/active-plan   →   plan_id
```

`_read_active_plan(session_id)` reads `{_SESSION_CACHE_BASE}/{session_id}/active-plan`
and returns the contained `plan_id` (or `None`). The `session_id` originates from an
external hook payload and is validated against the canonical UUID format before any
filesystem use, to prevent path traversal and glob injection.

### Icon Palette

The canonical 3-icon palette is defined by the `_ICON_*` constants and the
`_resolve_icon` mapping in `claude_runtime.py`. There is no idle state — every hook
event maps to one of exactly three glyphs:

| Glyph | Constant | Meaning | Source event(s) |
|-------|----------|---------|-----------------|
| ➤ (U+27A4) | `_ICON_ACTIVE` | active / in-progress | `UserPromptSubmit`, `SessionStart`, `PostToolUse` (any tool, incl. `Bash` and `AskUserQuestion`), unknown/missing event (defensive default) |
| ? | `_ICON_WAITING` | waiting on user input | `Notification`, `PreToolUse` with `tool_name == "AskUserQuestion"` |
| ✓ | `_ICON_DONE` | done | `Stop` |

The ✓ icon pairs with the Completed body through the existing `Stop`-event
`_resolve_icon` path — surfacing the Completed body requires no icon-logic change.

### Output Channels

`session_render_title` serves both Claude Code title channels from one body source,
distinguished by the `--statusline` flag:

| Mode | Flag | Output on success |
|------|------|-------------------|
| OSC hook | _(none)_ | JSON envelope `{"terminalSequence": "\x1b]0;{icon} {body}\x07"}` written to stdout, optionally augmented with the conditional `sessionTitle` channel below |
| statusLine | `--statusline` | plain `{icon} {body}` written to stdout |

Both modes share one stdout contract: stdout carries exactly the bytes the host
parser consumes and **nothing else**. The no-op path writes nothing to stdout (never
a TOON noop row); observability TOON rows go to stderr only.

#### Hook-mode dual channel — `terminalSequence` and `sessionTitle`

The hook-mode JSON envelope carries up to two reader channels, distinct surfaces fed
from the one `title-body.txt` body:

- **`terminalSequence`** — the OSC-0 escape that drives the OS terminal tab title.
  Emitted for **every** render event, byte-for-byte identical regardless of the
  second channel. Carries the live `{icon}` glyph.
- **`hookSpecificOutput.sessionTitle`** — the Claude Code web (claude.ai/code) and
  desktop session-picker title, equivalent to `/rename` and **UI-only**. The host
  supports this field on only two events, so the reader gates the emit accordingly:
  - `UserPromptSubmit`; and
  - `SessionStart` when `source ∈ {startup, resume}` (the `clear` and `compact`
    sources do **not** support it).

  For every other event (`Notification`, `Stop`, `PreToolUse`, `PostToolUse`,
  `PostToolUse:Bash`) the envelope stays exactly `{"terminalSequence": ...}` and never
  carries a stray `sessionTitle`. The `sessionTitle` value is the bare `title_body`
  (`pm:{phase}[:{short}]`) **without** the icon glyph — the web title channel is
  static per-prompt text and cannot carry the live ➤/?/✓ status icon. The full
  envelope on a supporting event is:

  ```json
  {"terminalSequence": "]0;{icon} {body}",
   "hookSpecificOutput": {"hookEventName": "{event}", "sessionTitle": "{body}"}}
  ```

The `sessionTitle` field is purely additive: older Claude Code hosts that do not
recognise it ignore the unknown field, so the terminal title keeps working with no
host-version probe. A missing or malformed `hook_event_name` / `source` omits
`sessionTitle` and still emits `terminalSequence` (best-effort/no-raise contract).
statusLine mode has no session-title channel and is unaffected.

## Platform Abstraction

`session render-title` is a platform-runtime operation: it answers "Would this differ
between Claude Code and OpenCode?" with yes. The Claude Code implementation
(`claude_runtime.py`) emits the OSC sequence / statusLine text described above. The
OpenCode implementation is a no-op — OpenCode has no equivalent terminal-title
channel, so the operation returns without emitting. The writer side (`manage-status`)
is platform-agnostic: it publishes the same plaintext `title-body.txt` regardless of
target, and only the reader differs per platform.
