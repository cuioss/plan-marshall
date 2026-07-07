# Terminal-Title Architecture

Single canonical reference for the terminal-title feature: how a plan's phase,
short description, lock-coordination state, and orchestration-busy state reach
the terminal title bar. The architecture is a **three-way split** across
`status.json` (the single source of persisted title state) and three skills, each
owning exactly one concern:

- **`manage-status` (state)** — persists the title state into `status.json`:
  `current_phase`, `short_description`, and the bare `title_token` field. It
  performs **no rendering** — it writes the state string only.
- **`manage-terminal-title` (composer)** — a pure, platform-agnostic library
  that owns the `compose(state, event)` function plus the glyph / icon / body
  vocabulary (including the ✅ terminal override). It performs **no I/O** — it is
  a pure function of the passed state dict and hook event.
- **`platform-runtime` (resolve + emit)** — resolves session → plan, reads
  `status.json` (live first, worktree next, archived fallback), calls
  `compose()`, and **emits**
  the result per platform (OSC sequence / statusLine / web-desktop sessionTitle,
  plus a direct `/dev/tty` push). The OpenCode runtime is a no-op.

`status.json` is the **only** persisted contract between the writer side and the
read+emit side. There is no `title-body.txt` artifact — the title state lives
inline in `status.json` and is composed on demand by the reader.

## Component Map

```text
STATE (manage-status)            COMPOSER (manage-terminal-title)   RESOLVE+EMIT (platform-runtime)
┌──────────────────────────┐     ┌──────────────────────────────┐  ┌────────────────────────────────────┐
│ title-token set {state}  │     │ compose(state, event, …)     │  │ session render-title                 │
│ title-token clear        │     │  1. _compose_body(state)     │  │  1. $CLAUDE_CODE_SESSION_ID          │
│   writes status.title_   │     │     pm:{phase}[:{short}]     │  │  2. session cache → plan_id          │
│   token (NO rendering)    │     │     pm:Completed[:{short}]   │  │  3. _read_title_state(plan_id):      │
└────────────┬─────────────┘     │  2. TITLE_TOKEN_GLYPHS[token]│  │     live → worktree → archived     │
             │ writes            │     ⏳/🔒 (active phase)      │  │     status.json (first hit wins)   │
             ▼                   │  3. resolve_icon(event,tool) │  │  4. compose(state, event)  ──────────┤
   status.json                  │     ➤/?/⚙/✓, ✅ terminal     │  │  5. emit per platform:               │
   (current_phase,              │        override               │  │     OSC terminalSequence (every event)│
    short_description,  ────────►│  → '{icon} {glyph} {body}'   ──►│     + sessionTitle (UI, gated)        │
    title_token)                │     or None (no-op)          │  │     statusLine: plain '{icon} {body}' │
             │                   └──────────────────────────────┘  │                                      │
   cmd_archive moves the         (pure; imports neither side)      │ session push-title-token:            │
   whole plan dir →                                                │  compose(state, None, icon_override) │
   archived-plans/{date}-                                          │  → /dev/tty OSC push                  │
   {plan_id}/status.json                                           │ (OpenCode runtime: no-op)            │
                                                                   └────────────────────────────────────┘
```

## State — `manage-status`

`manage-status` is the writer of persisted title state. It writes three fields
into `status.json` and performs **no title rendering** — that responsibility
belongs entirely to the composer.

| Field | Written by | Role |
|-------|------------|------|
| `current_phase` | the plan lifecycle commands (`transition`, etc.) | The active phase name (`5-execute`, `complete`, `archived`, …) |
| `short_description` | plan metadata setters | The optional short title-body name token |
| `title_token` | `manage-status title-token set\|clear` | The bare lock-coordination (`lock-waiting`/`lock-owned`) or orchestration-busy (`build-busy`) state string (no glyph/icon) |

### The `title-token` verb

The `title-token` subcommand is the single writer of the `title_token` field:

- `title-token set --plan-id {id} --state {state}` writes `status.title_token`
  to the bare state string. `{state}` is validated against `TITLE_TOKEN_STATES`
  = `{lock-waiting, lock-owned, build-busy}`.
- `title-token clear --plan-id {id}` removes the `title_token` field
  (idempotent).

`manage-status` persists **only the bare state string** — it never renders the
glyph or icon. The state → display rendering is owned exclusively by the composer:
`lock-waiting`/`lock-owned` map to ⏳/🔒 glyphs via the `TITLE_TOKEN_GLYPHS` map,
and `build-busy` maps to the 🔨 icon-slot override (see Composer below).
`build-busy` is deliberately absent from `TITLE_TOKEN_GLYPHS` — it is an
icon-slot override, not a glyph. This keeps `manage-status` free of any display
vocabulary. `build-busy` is set/cleared by the orchestration layer to bracket a
long-running call — see
[`persona-plan-marshall-agent`](../../persona-plan-marshall-agent/SKILL.md) for
the normative orchestration requirement.

### Archive interaction

`cmd_archive` (in `manage-status`) performs three mutations to `status.json`
before moving the plan directory:

1. Marks the active phase `done`.
2. Sets `current_phase = 'complete'` when every phase is done.
3. Pops the `title_token` field (`status.pop('title_token', None)`) — an
   archived plan has no live session driving its terminal title, so any
   in-flight token (`lock-waiting` / `lock-owned` / `build-busy`) left behind
   would persist a stale glyph or icon-slot override in the archived snapshot.
   The pop is token-agnostic: it covers every `TITLE_TOKEN_STATES` value with a
   single operation.

After writing the mutated `status.json` back to the live plan directory,
`cmd_archive` moves the **entire plan directory** to
`.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/` via `shutil.move`.
Because `status.json` is the single source of title state and it travels
inside the moved directory, the archived `status.json` carries the terminal
`current_phase` and the cleared `title_token` state into the archive with no
separate body artifact to preserve. The archive name is built from
`date_prefix = now_utc_iso()[:10]` and `archive_name = f'{date_prefix}-{plan_id}'`.

## Composer — `manage-terminal-title`

The composer lives in
`manage-terminal-title/scripts/manage_terminal_title.py`. It is a **pure leaf
library**: it imports neither `manage-status` nor `platform-runtime`, and it
performs no filesystem or network I/O. `platform-runtime` imports it
one-directionally via PYTHONPATH (the same mechanism `script-shared` modules use)
and calls `compose` after it has read `status.json`.

The composition contract — the body-format rules, the `TITLE_TOKEN_GLYPHS` map,
the icon palette + event→icon resolver, and the ✅ terminal override — is owned
exclusively by `manage-terminal-title`. See
[`manage-terminal-title/SKILL.md`](../../manage-terminal-title/SKILL.md) for the
authoritative `compose` signature, the body-format table, the glyph vocabulary,
and the icon-resolution table — those tables are not duplicated here.

### Composition summary

`compose(state_dict, event, icon_override=None, tool_name=None) -> str | None`
composes `'{icon} {glyph} {body}'` from three independent inputs:

- **Body** — `pm:{phase}[:{short}]` for active phases; `pm:Completed[:{short}]`
  for terminal phases (`complete` / `archived`); `None` only when `current_phase`
  is empty/missing (the true no-op). A terminal phase renders the Completed body,
  not `None`, so a finished plan still shows in the title.
- **Glyph** — the `title_token` lock-state glyph (⏳ `lock-waiting`,
  🔒 `lock-owned`), prepended when the field is set for an active phase; omitted
  when no `title_token` is present, and also omitted for terminal phases
  (`complete` / `archived`) regardless of the persisted token — a finished plan
  holds no live lock state. The `build-busy` token carries NO glyph (it is an
  icon-slot override, see below).
- **Icon** — the process icon from the hook event (➤ active / ? waiting /
  ⚙ busy / ✓ done), with two token/phase-keyed overrides layered on top by
  `compose`. (1) A **terminal-state override to ✅** (`_ICON_TERMINAL`, U+2705)
  for `complete` / `archived` phases regardless of the event or `icon_override`;
  the thick ✅ is deliberately distinct from the thin ✓ `_ICON_DONE` used per
  turn. (2) A **`build-busy` icon-slot override to 🔨** (`_ICON_BUILD`, U+1F528)
  for an active phase whose `title_token` is `build-busy` — forced into the icon
  slot for the whole orchestration call, rendering `🔨 pm:{phase}`, and
  deliberately distinct from the ⚙ momentary-busy icon. The full icon precedence
  is **terminal ✅ > build-busy 🔨 > `icon_override` > process icon** — the
  terminal ✅ override still wins, so 🔨 never appears for a finished plan. The ⚙
  busy icon (`_ICON_BUSY`, U+2699) is surfaced on the `PreToolUse:Bash` render
  trigger while a long-running Bash tool call executes; `PreToolUse:Bash` and
  `PostToolUse:Bash` bracket the busy window (busy on enter, back to ➤ active on
  exit). The process icons ➤ and ? MUST NOT appear for a finished plan. The
  `build-busy` state is set/cleared by the orchestration layer — see
  [`persona-plan-marshall-agent`](../../persona-plan-marshall-agent/SKILL.md) for
  the normative orchestration requirement.

## Resolve + Emit — `platform-runtime`

`session render-title` is a platform-runtime operation: it answers "Would this
differ between Claude Code and OpenCode?" with yes. The reader lives in
`platform-runtime/scripts/claude_runtime.py` as `session_render_title`, and is
the resolve + read + emit layer only — it owns neither the icon palette nor the
body format (both live in the composer it imports).

### `session render-title` — resolve, read, compose, emit

1. **Read `$CLAUDE_CODE_SESSION_ID`** — the session identifier supplied by the
   Claude Code hook environment. Empty → no-op (write nothing, return `""`).
2. **Resolve session → plan** via the session cache (see Session-Plan Binding
   below). Empty → no-op.
3. **Read the title state from `status.json`** via `_read_title_state(plan_id)`,
   resolving three locations in order (first hit wins):
   a. Live path: `.plan/local/plans/{plan_id}/status.json`.
   b. Worktree path (`_resolve_worktree_status_json`): when the live path is
      absent,
      `.plan/local/worktrees/{plan_id}/.plan/local/plans/{plan_id}/status.json`.
      This is the phase-5+ location: once the plan dir is moved into its
      isolated worktree (ADR-002) the main-live path misses, so the reader
      checks the worktree copy before falling back to the archive — without it
      the title freezes at its last-rendered state through phases 5-6.
   c. Archived fallback: when both the live and worktree paths are absent, glob
      `.plan/local/archived-plans/*-{plan_id}/status.json` (archive naming
      `{YYYY-MM-DD}-{plan_id}`, with the parent-name suffix checked to avoid a
      prefix collision) and read the terminal state from there. Absent/unreadable
      → no-op. The returned state dict is `{current_phase, short_description,
      title_token}` — exactly the inputs `compose` consumes.
4. **Compose** via `compose(state, hook_event_name, tool_name=tool_name)`.
   statusLine mode receives no hook stdin payload and composes with `event=None`
   (the composer applies the active icon for non-terminal phases and the ✅
   override for terminal ones); hook mode parses the JSON payload Claude Code
   writes to stdin (best-effort — missing/malformed input yields `event=None`
   and never raises).
5. **Emit the title** on the appropriate output channel (see Output Channels).
   `None`/empty composed string → no-op.

### `session push-title-token` — direct `/dev/tty` push

`session_push_title_token(plan_id, icon)` is the live-push path used by the lock
coordination machinery. It reads the plan's title state from
`status.json` via `_read_title_state`, composes via `compose(state, None,
icon_override=icon)`, and writes the OSC escape (`\x1b]0;{composed}\x07`) directly
to `/dev/tty`. It is best-effort — a silent no-op (`pushed: false`) when the
state is absent / unrenderable or when `/dev/tty` is not openable (CI,
background, no controlling terminal), and it never raises.

### Session-Plan Binding

The session identifier is bound to a plan through a filesystem cache rooted at
`_SESSION_CACHE_BASE` (`~/.cache/plan-marshall/sessions`):

```text
~/.cache/plan-marshall/sessions/{session_id}/active-plan   →   plan_id
```

`_read_active_plan(session_id)` reads `{_SESSION_CACHE_BASE}/{session_id}/active-plan`
and returns the contained `plan_id` (or `None`). The `session_id` originates from
an external hook payload and is validated against the canonical UUID format
before any filesystem use, to prevent path traversal and glob injection.

#### Binding ownership — bind-on-entry, protect-active, stale-reclaim

The **writer** of the `active-plan` binding is the executor
(`tools-script-executor`'s generated `execute-script.py`), which calls
`_write_active_plan(plan_id)` on every plan-scoped invocation — any call carrying
`--plan-id` / `--audit-plan-id`. The write follows a **no-overwrite-with-stale-reclaim**
policy so a read-only inspection call can never steal an active session's binding:

- **Bind on entry** — when the session has no `active-plan` slot yet, the first
  plan-scoped invocation binds it.
- **Idempotent re-bind** — a call naming the plan already bound rewrites the same
  value.
- **Protect the active binding** — a call naming a *different* plan is a no-op
  while the bound plan's live plan dir (`.plan/local/plans/{bound}/`) still
  exists. Read-only inspection calls that name another plan therefore no longer
  overwrite the binding, so the main orchestration tab keeps rendering its own
  plan's title.
- **Stale reclaim** — a call naming a different plan whose live plan dir is gone
  (archived or deleted) reclaims the slot. This delivers release-on-exit
  implicitly: once a plan is archived its slot becomes reclaimable by the next
  differing-plan invocation, so no separate `session release` verb is needed.

The write is fully fire-and-forget — every error path is swallowed and the
executor's exit code, stdout, and stderr are unaffected by cache-write outcomes.

### Output Channels

`session_render_title` serves both Claude Code title channels from one composed
string, distinguished by the `--statusline` flag:

| Mode | Flag | Output on success |
|------|------|-------------------|
| OSC hook | _(none)_ | JSON envelope `{"terminalSequence": "\x1b]0;{composed}\x07"}` written to stdout, optionally augmented with the conditional `sessionTitle` channel below |
| statusLine | `--statusline` | plain `{composed}` written to stdout |

Both modes share one stdout contract: stdout carries exactly the bytes the host
parser consumes and **nothing else**. The no-op path writes nothing to stdout
(never a TOON noop row); observability TOON rows go to stderr only. Every return
is the empty string so the wrapper `main()` (which skips `print()` on empty
results) cannot append a TOON tail.

#### Hook-mode dual channel — `terminalSequence` and `sessionTitle`

The hook-mode JSON envelope carries up to two reader channels, distinct surfaces
fed from the one composed title:

- **`terminalSequence`** — the OSC-0 escape that drives the OS terminal tab
  title. Emitted for **every** render event, carrying the live `{icon}` glyph.
- **`hookSpecificOutput.sessionTitle`** — the Claude Code web (claude.ai/code)
  and desktop session-picker title, equivalent to `/rename` and **UI-only**. The
  host supports this field on only two events, so the reader gates the emit:
  - `UserPromptSubmit`; and
  - `SessionStart` when `source ∈ {startup, resume}` (the `clear` and `compact`
    sources do **not** support it).

  For every other event the envelope stays exactly `{"terminalSequence": ...}`
  and never carries a stray `sessionTitle`. The `sessionTitle` value is the bare
  `pm:{phase}[:{short}]` body (via `_compose_body`) **without** the icon glyph —
  the web title channel is static per-prompt text and cannot carry the live
  ➤/?/✓ status icon. A missing or malformed `hook_event_name` / `source` omits
  `sessionTitle` and still emits `terminalSequence` (best-effort/no-raise). The
  field is purely additive: older Claude Code hosts ignore the unknown field, so
  the terminal title keeps working with no host-version probe. statusLine mode
  has no session-title channel and is unaffected.

## Platform Abstraction

The Claude Code implementation (`claude_runtime.py`) emits the OSC sequence /
statusLine text / sessionTitle described above and performs the `/dev/tty` push.
The OpenCode implementation is a **no-op** — OpenCode has no equivalent
terminal-title channel, so the operation returns without emitting. The state side
(`manage-status`) and the composer (`manage-terminal-title`) are
platform-agnostic: `manage-status` persists the same `status.json` fields
regardless of target, the composer is a pure function, and only the
`platform-runtime` emit layer differs per platform.
