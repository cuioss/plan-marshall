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

**Two delivery channels, one primary.** The hook-mode `terminalSequence` envelope
is the **PRIMARY** delivery channel: Claude Code itself writes those bytes to the
terminal, so it needs no tty ownership and works from any process the hook fires
in. The direct `/dev/tty` push is a labelled **FALLBACK** for the blocking windows
no hook event spans (a long build, a CI wait, a lock hold); off a controlling
terminal it cannot land, and that non-delivery is now **reported**
(`pushed: false`, `reason: no_controlling_tty`, `delivery: dev_tty_fallback`)
rather than silently swallowed.

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
   cmd_archive moves the         (pure; imports neither side)      │ session push-title-token (FALLBACK): │
   whole plan dir →                                                │  compose(state, None, icon_override) │
   archived-plans/{date}-                                          │  → /dev/tty OSC push                  │
   {plan_id}/status.json                                           │ session teardown (activation-gated): │
   then fires session teardown                                     │  → OSC-0 reset + session unbind      │
                                                                   │ (OpenCode runtime: no-op)            │
                                                                   └────────────────────────────────────┘
```

Render triggers wired by `project install-hook`: `SessionStart` (ONE matcher-less
entry — no separate `matcher: "clear"` render entry; the renderer branches on
`source == "clear"` and performs a session teardown instead), `UserPromptSubmit`,
`Notification`, `Stop`, `PreToolUse:AskUserQuestion`, `PreToolUse:Bash`, and
`PostToolUse` (ONE matcher-less entry, so the title refreshes after **every** tool
call at the same cadence as the statusLine footer). Seven render-trigger labels in
total, plus `statusLine`.

## State — `manage-status`

`manage-status` is the writer of persisted title state. It writes three fields
into `status.json` and performs **no title rendering** — that responsibility
belongs entirely to the composer.

| Field | Written by | Role |
|-------|------------|------|
| `current_phase` | the plan lifecycle commands (`transition`, etc.) | The active phase name (`5-execute`, `complete`, `archived`, …) |
| `short_description` | plan metadata setters | The optional short title-body name token |
| `title_token` | `manage-status title-token set\|clear` (the explicit writer); `transition`/`set-phase` additionally pop a stale `build-busy` token and `archive` pops any token before persisting | The bare lock-coordination (`lock-waiting`/`lock-owned`) or orchestration-busy (`build-busy`) state string (no glyph/icon) |

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

### Persisted-title-state-write drive seam

Every persisted `current_phase` write fires a single best-effort **drive seam**
immediately after `write_status`, so the title reflects a phase change the moment
it is persisted instead of freezing at the last-rendered phase. The three phase
writers — `cmd_create` (first-phase seed), `cmd_transition` (phase advance), and
`cmd_set_phase` — call one shared `_surface_drive(plan_id)` helper that fires two
fire-and-forget delegations to `platform-runtime` through the executor subprocess
channel (the same channel `manage-locks/merge_lock.py` uses):

- a **repaint** — `session push-title-token --plan-id {id}` with no icon, a plain
  re-render of the freshly composed title; and
- a **bind** — `session bind --plan-id {id}`, the last-driven-wins session→plan
  binding (see Session-Plan Binding below).

The seam is fully exception-swallowing: a delegation failure never changes the
status-write outcome or the command's exit code. `manage-status` still composes
and emits nothing itself — it delegates the repaint and the bind to
`platform-runtime`, preserving the state-layer's render-free contract (exactly as
`merge_lock.py` delegates its own title-token surface).

Additionally, `cmd_transition` and `cmd_set_phase` call `drop_stale_build_busy(status)`
**before** `write_status` — the phase-boundary safety-net that clears a stale
`build-busy` token (left behind by an interrupted long-running orchestration call)
so it cannot leak the 🔨 hammer icon across the phase change. The clear is scoped
to `build-busy` only; the live lock-coordination tokens (`lock-waiting` /
`lock-owned`) are left untouched. `cmd_create` performs no such clear (a freshly
seeded plan holds no in-flight token).

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
   single operation. This is distinct from the `transition` / `set-phase`
   phase-writer clear (`drop_stale_build_busy`, see Persisted-title-state-write
   drive seam above), which is scoped to `build-busy` **only** and leaves the
   live lock tokens intact — `archive` unconditionally clears every token because
   the plan is going dormant, whereas the phase writers preserve a live lock
   state that is still meaningful on the ongoing plan.

After writing the mutated `status.json` back to the live plan directory,
`cmd_archive` moves the **entire plan directory** to
`.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/` via `shutil.move`.
Because `status.json` is the single source of title state and it travels
inside the moved directory, the archived `status.json` carries the terminal
`current_phase` and the cleared `title_token` state into the archive with no
separate body artifact to preserve. The archive name is built from
`date_prefix = now_utc_iso()[:10]` and `archive_name = f'{date_prefix}-{plan_id}'`.

Immediately **after** the move, `cmd_archive` fires `_drive_teardown(plan_id)` —
a best-effort `session teardown` delegation through the same executor channel as
the bind/repaint seam. This is the **live-surface counterpart** of the persisted
`title_token` pop above: the pop retires the persisted token in the archived
snapshot, the teardown retires the LIVE terminal title (reset to the terminal's
own default) and the session's plan binding, so a finished plan leaves neither a
stale title nor a stale binding behind. It is activation-gated inside the
delegate and fully exception-swallowing — a delegation failure never changes the
archive command's status or exit code.

The teardown carries the same **observable-non-delivery** contract as the repaint
seam: when an *activated* delegate reports a failed title reset (`reset: false`)
and/or a failed binding release (`unbound: false`), the seam emits one
`logger.warning` naming the plan and the failed half (both halves are named when
both failed, matching the delegate's independent reporting). An inactive delegate
(`active: false` / `reason: feature_inactive`) is the ordinary nothing-to-do case
and stays at DEBUG, as does every other failure path. Only the observability of a
non-delivery changes — never the archive command's status or exit code.

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
  trigger while a long-running Bash tool call executes; `PreToolUse:Bash` and the
  matcher-less `PostToolUse` trigger bracket the busy window (busy on enter, back
  to ➤ active on exit). The process icons ➤ and ? MUST NOT appear for a finished plan. The
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
3b. **Teardown branch** — in hook mode, a `SessionStart` payload whose `source`
   is `clear` is a session TEARDOWN, not a render: the reader calls
   `session_teardown()` and writes **nothing** to stdout. A render here would
   repaint a title for a session that no longer drives a plan. Every other source
   falls through to compose + emit.
4. **Compose** via `compose(state, hook_event_name, tool_name=tool_name)`.
   statusLine mode receives no hook stdin payload and composes with `event=None`
   (the composer applies the active icon for non-terminal phases and the ✅
   override for terminal ones); hook mode parses the JSON payload Claude Code
   writes to stdin (best-effort — missing/malformed input yields `event=None`
   and never raises).
5. **Emit the title** on the appropriate output channel (see Output Channels).
   `None`/empty composed string → no-op.

### `session push-title-token` — direct `/dev/tty` push

`session_push_title_token(plan_id, icon=None)` is the single canonical **repaint
seam** — the live-push path shared by every persisted-title-state change. It reads
the plan's title state from `status.json` via `_read_title_state`, composes via
`compose(state, None, icon_override=icon)`, and writes the OSC escape
(`\x1b]0;{composed}\x07`) directly to `/dev/tty`. The `--icon` argument is
**optional**: a glyph push (⏳/🔒 from the lock machinery) supplies it, while a
plain repaint omits it (`icon=None`) to re-render the current title with its
default active icon. Three consumers drive this one seam:

- **`manage-status`'s phase-write drive seam** — an icon-less repaint on every
  `current_phase` write (see State above);
- **`manage-locks/merge_lock.py`** — the ⏳/🔒 lock-state pushes on acquire/block,
  AND a plain icon-less repaint on the release/clear path so the lock glyph
  disappears live once the lock is released; and
- the orchestration-layer `build-busy` bracketing (see
  [`persona-plan-marshall-agent`](../../persona-plan-marshall-agent/SKILL.md)).

This is the **FALLBACK** delivery channel — the primary one is the hook-written
`terminalSequence` envelope (see Output Channels below), which needs no tty
ownership. The push exists for the blocking windows no hook event spans.

It is best-effort and never raises, but the outcome is **observable** rather than
silently swallowed. The two no-push outcomes are distinguished on the return TOON:

| Outcome | `pushed` | `reason` | `delivery` |
|---------|----------|----------|------------|
| State absent / unrenderable | `false` | `no_title_state` | _(absent — no channel was attempted)_ |
| `/dev/tty` not openable (CI, background, dispatched agent) | `false` | `no_controlling_tty` | `dev_tty_fallback` |
| Push landed | `true` | _(absent)_ | `dev_tty_fallback` |

The `manage-status` drive seam consumes that distinction: a repaint reported as
non-delivered for any reason **other** than `no_title_state` emits one
`logger.warning`, so a silently-dead title channel is visible instead of hidden at
DEBUG. Every other failure path keeps its DEBUG level, and the seam still never
alters the command's status or exit code.

### Session-Plan Binding

The session identifier is bound to a plan through a filesystem cache rooted at
`_SESSION_CACHE_BASE` (`~/.cache/plan-marshall/sessions`):

```text
~/.cache/plan-marshall/sessions/{session_id}/active-plan   →   plan_id
```

The binding policy lives in one pure, importable module,
`platform-runtime/scripts/session_binding.py`, wrapped by four testable
`platform-runtime` verbs. The `session_id` (and the `plan_id`) originate from an
external hook payload and are each validated as a safe single path segment
(traversal-sentinel rejection + 120-char cap) before any filesystem use, to
prevent path traversal and glob injection.

| Verb | Policy fn | Role |
|------|-----------|------|
| `session bind --plan-id {id} [--session-id {id}]` | `session_binding.bind` | **Last-driven-wins** unconditional write of the caller's OWN slot — NO protect-active, NO stale-slot reclaim, NO plan-dir-exists check. |
| `session resolve-plan [--session-id {id}]` | `session_binding.resolve_plan` | Read side — returns the bound `plan_id` (or empty). `session render-title` resolves session→plan through it. |
| `session doctor [--fix]` | `session_binding.doctor` | Reverse-index conflict scan + stale-slot GC + orphan-directory prune (see below). |
| `session teardown` | `session_binding.unbind` | **Activation-gated** end-of-session retire: resets the tab to the terminal's own default and drops the caller's OWN slot (see below). |

#### `session teardown` — activation-gated title reset + unbind

`session teardown` is the end-of-session counterpart of `session bind` /
`session render-title`. Order is load-bearing — the **activation signal is read
FIRST**:

- **Inactive** (`_terminal_title_active()` is False — no render-hook entry on any
  render-trigger event AND no `statusLine` command in either
  `.claude/settings.json` or `.claude/settings.local.json`): the verb returns
  `active: false` / `reason: feature_inactive` having written no title escape,
  opened no `/dev/tty`, mutated no binding, and raised nothing. A project that
  never opted into terminal titles is never touched. Any settings read failure
  also reports inactive (fail-safe, not a guess).
- **Active**: the session id is resolved from `$CLAUDE_CODE_SESSION_ID`, the
  neutral-default reset escape `\x1b]0;\x07` — a bare OSC-0 with an **empty**
  payload, which returns the tab to the terminal's own default rather than
  painting some other string — is written to `/dev/tty` best-effort, and then
  `session_binding.unbind` drops the caller's own slot (pruning the now-empty
  session directory). `reset` and `unbound` are reported **independently**, so a
  title reset that landed while the unbind failed (or the reverse, off a
  controlling terminal) is visible rather than collapsed into one flag.

Two call sites drive it: the `SessionStart:clear` render trigger (the renderer
branches on `source == "clear"`, performs the teardown, and writes nothing to
stdout) and `manage-status cmd_archive` (see Archive interaction above).

#### Binding ownership — bind-on-drive, last-driven-wins

The **writer** of the `active-plan` binding is `session bind`, fired from the
`manage-status` phase-state-write drive seam (see Persisted-title-state-write
drive seam above) on every `current_phase` write. The write is
**last-driven-wins**: it unconditionally binds the caller's own per-session slot,
so a session that switches to drive a different live plan immediately rebinds to
it. Because the cache is per-session (keyed by `session_id`), `bind` touches only
the caller's slot — there is no cross-session check-then-act window and no shared
mutable index. Every path is best-effort / no-raise.

This **replaces** the former **no-overwrite / protect-active / stale-reclaim**
policy that the generated executor template wrote via `_write_active_plan` on
every plan-scoped invocation. That in-template binder has been **removed outright**
(clean break): the executor no longer writes any session→plan binding. The old
protect-active policy stuck a session to its first-bound plan, so a session that
switched to drive a second live plan stayed pinned to the first (the sticky-binding
pollution, Defect 2); last-driven-wins fixes it by making the most recent driver
authoritative.

#### `session doctor` — reverse-index conflict scan + stale GC + orphan prune

`session doctor` visits **every directory** under
`~/.cache/plan-marshall/sessions/` — not only the ones that yield a readable
slot — builds an **in-memory plan→sessions reverse index** from the live slots,
and reports a **three-way** health picture:

- **conflicts** — any plan bound by more than one session (two sessions driving
  the same plan);
- **stale** slots — a slot whose bound plan is archived or deleted (its live plan
  dir, on main OR in its phase-5+ worktree, is gone); and
- **orphans** — a session directory that carries no binding at all, because its
  `active-plan` file is absent, empty, or unreadable. These are the residue the
  `unbind` prune could not remove, and the all-directories scan is what makes
  them visible: a slot-only walk skips them by construction, so the cache root
  accumulates empty directories no verb ever reports.

The three categories are disjoint at scan time: a stale slot resolves to a
`plan_id` while an orphan directory resolves to nothing, so the report never
double-counts a directory.

With `--fix` it GCs each stale slot (removes its `active-plan` file) and prunes
each orphan directory. Both prunes share one `_remove_slot_and_prune` body — the
same unlink-then-rmdir the public `unbind` teardown uses — so slot removal has a
single home. The `scanned` count keeps its original meaning (live slots scanned)
and does not include orphan directories; `orphans_removed` is reported separately
from `gc_removed`.

The scan keeps **NO shared mutable index** (no `index.json`) — it is per-file and
idempotent, so it introduces no new shared-file TOCTOU hazard. Stale GC delivers
release-on-exit implicitly: an archived plan's slot becomes GC-eligible, so no
separate `session release` verb is needed.

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
  - `SessionStart` when `source ∈ {startup, resume}` (the `compact` source does
    **not** support it; the `clear` source never reaches the emit at all — it
    branches earlier into the session teardown and writes nothing to stdout).

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
