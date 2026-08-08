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
  `compose()`, and **emits** the result per platform (OSC sequence / statusLine /
  web-desktop sessionTitle). The OpenCode runtime is a no-op.

**One delivering channel.** The hook-mode `terminalSequence` envelope is the
**sole** delivery channel for the terminal tab title: Claude Code itself writes
those bytes to the terminal, so it needs no tty ownership and works from any
process the hook fires in. Both plan titles and orchestrator-epic titles ride it
(see Session-Plan Binding → the orchestrator epic slot below). The channel is
**event-driven, not callable on demand** — a writer reaches the terminal only by
writing state that the *next* render event will read and paint. The normative
consequences of that single-channel shape are the Channel Delivery Contract
below, which is the governing section of this document.

One no-delivery reason survives on the emit surface:

- `reason: feature_inactive` — the terminal-title feature is configured off (no
  render-hook entry and no `statusLine`), so nothing was attempted at all.

`status.json` is the **only** persisted contract between the writer side and the
read+emit side. There is no `title-body.txt` artifact — the title state lives
inline in `status.json` and is composed on demand by the reader.

## Channel Delivery Contract

This section is **normative**. It records the reconciled channel inventory and
the delivery obligations every title writer owes. Where a descriptive section
below and this contract disagree, this contract governs.

### Channel inventory

| Channel | Title states it may carry | Observable in this runtime? |
|---------|---------------------------|------------------------------|
| Hook `terminalSequence` (OSC-0) | Every composed state — `{icon} {glyph} {body}`, including the ✅ terminal state and the 🔨 `build-busy` icon-slot override | **Yes — the only channel that lands.** Claude Code writes the bytes; no tty ownership required |
| Hook `hookSpecificOutput.sessionTitle` | The bare `pm:{phase}[:{short}]` body only — no icon, no glyph | Yes, but **UI-only** (web / desktop session picker) and emitted on `UserPromptSubmit` and `SessionStart{startup,resume}` only |
| `statusLine` | `{icon} {body}` | Yes, in the footer. Carries no glyph and drives no tab title |
| Direct `/dev/tty` OSC push | **None — the write is deleted** (ruling (a)) | No. No context in this runtime holds a controlling terminal, so the write provably never landed |

**Binding rule:** *nothing may be cleared, reset, or repainted on a channel that
cannot deliver.* A writer that targets a non-delivering channel has not
discharged its obligation, however clean its return value looks.

### (a) `/dev/tty` — delete the write, keep the seam

The direct `/dev/tty` OSC write is **removed outright** — not demoted to a debug
or diagnostic path. The rationale is the load-bearing part: **a fallback that
provably never lands is worse than none, because it makes the reset look
implemented.** An untested never-landing path is exactly the false-implementation
signal this contract removes; keeping it as a demoted path would preserve that
signal under a quieter name.

`session push-title-token` itself **survives**. Its orchestrator branch carries
the load-bearing `session_binding.bind_orchestrator` side effect, and its state
writes are what the next render reads. Both are retained; **only the `/dev/tty`
OSC write is removed from it.** The seam's post-change contract is therefore
**"bind + persist state"**, never "repaint". Its return value describes what it
bound and persisted, and carries neither a `pushed` flag, a
`delivery: dev_tty_fallback` field, nor a `reason: no_controlling_tty` value —
all three described a channel that no longer exists.

Artifacts this ruling edits: `platform-runtime/scripts/_claude_runtime_impl.py`
(the OSC writes in `session_push_title_token` and `session_teardown`),
`platform-runtime/standards/contract.md`, `platform-runtime/SKILL.md`,
`platform-runtime/scripts/runtime_base.py` (abstract docstring),
`platform-runtime/scripts/opencode_runtime.py` (no-op reason text),
`plan-marshall/references/hook-authoring-guide.md`,
`persona-marshall-orchestrator/standards/orchestration-model.md`,
`persona-plan-marshall-agent/SKILL.md` and
`persona-plan-marshall-agent/standards/agent-behavior-rules.md`,
`plan-marshall/workflow/await-long-running.md`, and this document.

### (b) Terminal-state delivery — `SessionStart:clear` is the sole release point

`✅ pm:Completed` reaches the tab by **rendering the archived state on the next
hook event**: the archived-status reader in `claude_runtime.py` (the
`archived-plans/*-{plan_id}/status.json` fallback arm) already resolves a moved
plan directory, so the state is readable after the archive move. Delivery
therefore requires only that the session→plan binding still exist when that next
event fires.

The hard ordering rule: **no binding release before the state it enables has been
delivered.** The ruling that satisfies it: **the archive path performs no binding
release at all.** Unbinding is not how "done" is expressed, and
`SessionStart:clear` already routes to `session_teardown`
(`_claude_runtime_impl.py`), so the genuine session-end release point already
exists and needs no new machinery. Archive drops the release; the session
releases when the session ends. `SessionStart:clear` is consequently the **sole**
binding-release point.

Both writers of `current_phase = 'complete'` are in scope for this ruling and
neither may release a binding: `cmd_transition` (`_cmd_lifecycle.py:375`) and
`cmd_archive` (`_cmd_lifecycle.py:443`).

Artifacts this ruling edits: `manage-status/scripts/_cmd_lifecycle.py`
(`cmd_archive`, `cmd_transition`),
`platform-runtime/scripts/_claude_runtime_impl.py` (`session_teardown`),
`platform-runtime/scripts/session_binding.py`, and this document.

### (b2) The delivery obligation covers every rendered-state transition

Ruling (b) is one instance of a general rule, not the rule itself:

> **A state write whose rendered projection changes MUST be paired with a
> delivered repaint on the delivering channel, or it is not a completed
> transition.**

"Clear the state" and "clear the title" are two obligations. Discharging only the
first leaves the terminal asserting something false: a `status.json` write fires
no render event, so a token cleared in state alone can keep painting its glyph
indefinitely. This is not archive-specific — it applies equally to a `build-busy`
clear at a mid-plan phase boundary, where the persisted state is correct and the
tab still shows 🔨. **The archive case is one instance of this rule, not the
rule itself**, and a reader who comes away believing the obligation is
archive-scoped has misread it.

**Delivery consequence of ruling (a).** With the `/dev/tty` write deleted, the
hook `terminalSequence` envelope is the only channel that can satisfy this
obligation, and that channel is event-driven rather than callable on demand.
**The paired repaint is therefore necessarily DEFERRED to the next hook event.**
A writer discharges its delivery obligation by writing state the renderer will
read — ensuring the *next* render paints the corrected title — not by pushing
bytes at write time. This is the positive mechanism, stated so that "deliver a
repaint" is never read as an instruction to re-introduce a live push.

The gap this leaves is named and accepted: between the state write and the next
hook event the terminal is **knowingly stale**. That window is bounded by render
cadence (ruling (d) keeps the cadence live and narrow), is accepted as the cost
of a single honest channel, and **is not to be closed by resurrecting the
`/dev/tty` write.**

### (c) `title_token` ownership — structured record, arbitration, state-driven GC exemption

`title_token` is a **structured record**, not a bare state string:

```json
{"owner": "merge-lock", "state": "lock-owned", "set_at": "2026-01-01T00:00:00Z"}
```

- **`owner`** — the writer that set the token. Vocabulary: `build-hook` (the
  `PreToolUse:Bash` / `PostToolUse:Bash` render-hook assist that brackets a build
  window), `merge-lock` (`manage-locks/merge_lock.py`), and `cli` (an explicit
  `manage-status title-token set` invocation from the orchestration layer).
- **`state`** — the bare state marker, validated against `TITLE_TOKEN_STATES`
  (`lock-waiting`, `lock-owned`, `build-busy`) exactly as before.
- **`set_at`** — the UTC ISO-8601 instant of the set, the input to the staleness
  rule below.

**Last-writer arbitration.** A `set` from any owner replaces the record
wholesale — last writer wins, and the record always names its current owner. A
`clear` is **owner-scoped**: only the recorded `owner` may clear its own token.
A foreign clear is a no-op, so a lock glyph owned by `merge-lock` cannot be
clobbered by an unrelated build bracket, and the asymmetry (open SET, scoped
CLEAR) is what makes ownership meaningful.

**Aged-token staleness.** A token whose `set_at` is older than **3600 seconds**
is stale and may be cleared or replaced by **any** writer. The threshold is
derived, not arbitrary: it comfortably exceeds the longest architecture-resolved
build ceiling in this project (~1926 s for an unscoped whole-tree verify), so a
live bracket can never age out mid-call, while any process death that strands a
token self-heals within the hour without operator action.

**GC exemption.** An archived plan's session slot is **exempt from
`session doctor --fix` GC exactly while it still has an undelivered terminal
state, and becomes collectable once that state has been delivered.** This is a
**state-driven exemption, not a time window** — the predicate is "terminal state
still owed", never an elapsed-time grace period. `session_binding._plan_is_live`,
which today classifies an archived plan stale unconditionally, therefore gains a
**delivery-pending arm** rather than a timeout.

Artifacts this ruling edits: `manage-status/scripts/_status_core.py`,
`manage-status/scripts/_status_query.py` (`cmd_title_token`, `cmd_set_phase`),
`manage-status/scripts/manage-status.py` (the `title-token` argparse surface),
`manage-status/standards/status-lifecycle.md`, `manage-status/SKILL.md`,
`manage-locks/scripts/merge_lock.py`, `manage-locks/SKILL.md`,
`manage-terminal-title/scripts/manage_terminal_title.py` (reads the structured
record), `platform-runtime/scripts/session_binding.py` (`_plan_is_live`),
`platform-runtime/scripts/claude_runtime.py` (the build-command predicate that
sets the token), `marshall-steward/references/menu-terminal-title.md`, and this
document.

### (d) Render cadence — keep the live, narrow shape

The installed render configuration already scopes `PostToolUse` to the
`Bash` and `AskUserQuestion` matchers, and the render cadence is among the
largest recurring script costs in the project. Both facts point the same way, so
this is a **standing joint position** that any future cadence work inherits
without re-opening this contract:

- Keep `PostToolUse` **matcher-scoped** — do not widen it to a matcher-less
  entry. The installer writes the two scoped entries and prunes nothing.
- `_DISPLAY_RENDER_ENTRIES` is converged to the live shape: the two
  `PostToolUse` rows are matcher-scoped (`AskUserQuestion` + `Bash`), and the
  installed `SessionStart:clear` entry — previously absent from the expected
  set, so its removal would have gone unreported — is included.
- **`_prune_matcher_scoped_render_entries` is deleted**, not left dormant. It
  existed to prune matcher-scoped entries back toward a matcher-less shape this
  contract rejects, so keeping it would have preserved a live path to the wrong
  shape.
- The `display` health check is **fail-closed**: an expected-vs-installed
  divergence returns `status: error`. It previously returned `status: success`
  with `all_healthy: false`, which is invisible to any caller that branches on
  status. The fail is scoped to the `display` check — `mcp-diagnostics`
  reporting an unreachable port is an environmental condition, not a
  misconfiguration, and failing on it would train callers to ignore the status.

Ruling (c)'s paired `build-busy` clear depends on this: the clear rides the
already-installed `PostToolUse:Bash` entry, which is precisely the entry a
widening-and-pruning cadence would remove.

Artifacts this ruling edits:
`platform-runtime/scripts/_claude_runtime_impl.py` (`_DISPLAY_RENDER_ENTRIES`,
`_prune_matcher_scoped_render_entries`),
`plan-marshall/references/hook-authoring-guide.md`,
`marshall-steward/references/menu-terminal-title.md`, and this document.

### Deferred — the statusLine rendered-state substitution

The host behaviour of an **empty statusLine output** is an **open fact and is
NOT assumed here**: whether the host preserves the previous footer, blanks it, or
falls back to its own default has not been confirmed. The rendered-state
substitution for statusLine mode is therefore **deferred** pending a confirmed
host check; only the named-no-op observability half of the render path is in
scope now. This contract asserts no host behaviour it has not confirmed.

### Hook configuration is human-gated

This contract **records** decisions about the `.claude/settings.json` /
`.claude/settings.local.json` render-hook shape (ruling (d)) but is not itself a
license to write those files. The settings surface is human-gated — it carries a
permission prompt and a startup-reload latency — so any settings change is
surfaced to the operator as a separate manual step and is never written by
automated plan execution.

## Component Map

```text
STATE (manage-status)            COMPOSER (manage-terminal-title)   RESOLVE+EMIT (platform-runtime)
┌──────────────────────────┐     ┌──────────────────────────────┐  ┌────────────────────────────────────┐
│ title-token set          │     │ compose(state, process_state)│  │ session render-title                 │
│   --state --owner        │     │  1. _compose_body(state)     │  │  1. $CLAUDE_CODE_SESSION_ID          │
│ title-token clear        │     │     pm:{phase}[:{short}]     │  │  2. session cache → plan_id          │
│   --owner (owner-scoped) │     │     pm:Completed[:{short}]   │  │  3. _read_title_state(plan_id):      │
│   writes status.title_   │     │  2. title_token_state(rec)   │  │     live → worktree → archived     │
│   token (NO rendering)   │     │     → TITLE_TOKEN_GLYPHS     │  │     status.json (first hit wins),   │
└────────────┬─────────────┘     │     ⏳/🔒 (active phase)      │  │     aged tokens dropped on read    │
             │ writes            │  3. resolve_icon(process_st) │  │  4. compose(state, process_state) ───┤
             ▼                   │     ➤/?/⚙/✓, ✅ terminal     │  │  5. emit per platform:               │
   status.json                   │        override, 🔨 build     │  │     OSC terminalSequence (every event)│
   (current_phase,               │  → '{icon} {glyph} {body}'   ──►│     + sessionTitle (UI, gated)        │
    short_description,  ────────►│     or None (no-op)          │  │     statusLine: plain '{icon} {body}' │
    title_token =                └──────────────────────────────┘  │  6. NAMED outcome on stderr (8 total)│
     {owner,state,set_at})       (pure; imports neither side)      │                                      │
             │                                                     │ session push-title-token:            │
   cmd_archive moves the                                           │  bind + persist state (NO repaint)   │
   whole plan dir →                                                │  next hook event delivers it         │
   archived-plans/{date}-                                          │ session teardown (SessionStart:clear │
   {plan_id}/status.json                                           │  only): session unbind               │
   and releases no binding                                         │ (OpenCode runtime: no-op)            │
                                                                   └────────────────────────────────────┘
```

Render triggers wired by `project install-hook`: `SessionStart:matcher-less`,
`SessionStart:clear` (the entry that routes the session teardown — the renderer
branches on `source == "clear"`, tears the session down, and writes nothing),
`UserPromptSubmit`, `Notification`, `Stop`, `PreToolUse:AskUserQuestion`,
`PreToolUse:Bash`, `PostToolUse:AskUserQuestion`, and `PostToolUse:Bash`.
`PostToolUse` is **matcher-scoped**, not matcher-less — see Channel Delivery
Contract ruling (d). Nine render-trigger labels in total, plus `statusLine`.

That list is the `_DISPLAY_RENDER_ENTRIES` expected set the `display` health
check reports against, and the check is **fail-closed**: a divergence between
the expected and installed sets returns `status: error`, not a `success`
carrying `all_healthy: false`.

## State — `manage-status`

`manage-status` is the writer of persisted title state. It writes three fields
into `status.json` and performs **no title rendering** — that responsibility
belongs entirely to the composer.

| Field | Written by | Role |
|-------|------------|------|
| `current_phase` | the plan lifecycle commands (`transition`, etc.) | The active phase name (`5-execute`, `complete`, `archived`, …) |
| `short_description` | plan metadata setters | The optional short title-body name token |
| `title_token` | `manage-status title-token set\|clear` (the CLI writer), the `build-hook` render assist, and `merge-lock`; `archive` pops any token before persisting | The structured `{owner, state, set_at}` record carrying the lock-coordination (`lock-waiting`/`lock-owned`) or orchestration-busy (`build-busy`) state (no glyph/icon) |

### The `title-token` verb

The `title-token` subcommand is the CLI writer of the `title_token` field:

- `title-token set --plan-id {id} --state {state}` writes the structured record
  with `owner: cli`. `{state}` is validated against `TITLE_TOKEN_STATES`
  = `{lock-waiting, lock-owned, build-busy}`.
- `title-token clear --plan-id {id}` removes the `title_token` field when the
  caller owns it or the record is stale (idempotent).

The record shape, the owner vocabulary, the last-writer arbitration rule, and the
aged-token staleness threshold are specified once in Channel Delivery Contract
ruling (c) and are not restated here.

`manage-status` persists **only the state record** — it never renders the
glyph or icon. The state → display rendering is owned exclusively by the composer:
`lock-waiting`/`lock-owned` map to ⏳/🔒 glyphs via the `TITLE_TOKEN_GLYPHS` map,
and `build-busy` maps to the 🔨 icon-slot override (see Composer below).
`build-busy` is deliberately absent from `TITLE_TOKEN_GLYPHS` — it is an
icon-slot override, not a glyph. This keeps `manage-status` free of any display
vocabulary. `build-busy` is set and cleared by the **machine-owned** render-hook
bracket (`PreToolUse:Bash` / `PostToolUse:Bash`, owner `build-hook`) around a
foreground build, and by the orchestrator wait seam (owner `cli`) around a
detached one — see Channel Delivery Contract ruling (c) above.

### Persisted-title-state-write drive seam

Every persisted `current_phase` write fires a single best-effort **drive seam**
immediately after `write_status`, so the session binding stays current and the
freshly persisted phase is the state the **next** hook event renders. Delivery is
deferred to that event by construction — see Channel Delivery Contract ruling
(b2). The three phase writers — `cmd_create` (first-phase seed), `cmd_transition`
(phase advance), and `cmd_set_phase` — call one shared `_surface_drive(plan_id)`
helper that fires two fire-and-forget delegations to `platform-runtime` through
the executor subprocess channel (the same channel `manage-locks/merge_lock.py`
uses):

- a **state persist** — `session push-title-token --plan-id {id}` with no icon,
  which composes and persists the current title state for the next render; and
- a **bind** — `session bind --plan-id {id}`, the last-driven-wins session→plan
  binding (see Session-Plan Binding below).

The seam is fully exception-swallowing: a delegation failure never changes the
status-write outcome or the command's exit code. `manage-status` still composes
and emits nothing itself — it delegates both halves to `platform-runtime`,
preserving the state-layer's render-free contract (exactly as `merge_lock.py`
delegates its own title-token surface).

A stale `build-busy` token cannot leak the 🔨 hammer icon across a phase change,
because staleness is resolved by the aged-token rule in Channel Delivery Contract
ruling (c) rather than by a phase-boundary sweep. The live lock-coordination
tokens (`lock-waiting` / `lock-owned`) are owner-scoped and are never cleared by
a foreign writer.

### Archive interaction

`cmd_archive` (in `manage-status`) performs three mutations to `status.json`
before moving the plan directory:

1. Marks the active phase `done`.
2. Sets `current_phase = 'complete'` when every phase is done.
3. Pops the `title_token` field (`status.pop('title_token', None)`) — an
   archived plan has no live session driving its terminal title, so any
   in-flight token (`lock-waiting` / `lock-owned` / `build-busy`) left behind
   would persist a stale glyph or icon-slot override in the archived snapshot.
   The pop is owner- and token-agnostic: it covers every record regardless of
   `owner` or `state` with a single operation, because a plan going dormant holds
   no live coordination state worth arbitrating over. This is the one sanctioned
   exception to the owner-scoped clear of Channel Delivery Contract ruling (c).

After writing the mutated `status.json` back to the live plan directory,
`cmd_archive` moves the **entire plan directory** to
`.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/` via `shutil.move`.
Because `status.json` is the single source of title state and it travels
inside the moved directory, the archived `status.json` carries the terminal
`current_phase` and the cleared `title_token` state into the archive with no
separate body artifact to preserve. The archive name is built from
`date_prefix = now_utc_iso()[:10]` and `archive_name = f'{date_prefix}-{plan_id}'`.

`cmd_archive` **releases no session binding.** This is the direct consequence of
Channel Delivery Contract ruling (b): the terminal `✅ pm:Completed` state is
delivered by the next hook event rendering the archived `status.json`, and that
render can only resolve the plan while the session→plan binding still exists.
Releasing at archive time would destroy the delivery route for the very state the
archive just persisted, violating the ordering rule *no binding release before
the state it enables has been delivered.* The binding survives the archive and is
released at session end by `SessionStart:clear`, the sole release point.

The retained binding is protected from garbage collection for exactly as long as
it is needed: `session doctor --fix` exempts an archived plan's slot **while its
terminal state is undelivered**, and collects it once delivered — the
state-driven exemption specified in ruling (c).

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

`compose(state_dict, process_state, icon_override=None) -> str | None`
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
  `build-busy` state is set and cleared by the **machine-owned** render-hook
  bracket — the `PreToolUse:Bash` / `PostToolUse:Bash` render assist, no LLM turn
  owns either half — see Channel Delivery Contract ruling (c).

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
   below). When a plan is bound, its `status.json` supplies the title state
   (Step 3). When **no** plan is bound, the reader falls back to the parallel
   **orchestrator epic binding** (the `active-orchestrator` slot): it resolves the
   bound epic slug and reads the epic's title state via the existing orchestrator
   composer branch, so an orchestrator epic reaches the PRIMARY hook channel
   exactly as a plan does — the orchestrator title needs no controlling terminal.
   Neither a plan nor an epic bound → no-op. The plan read path is unchanged; the
   orchestrator fallback is reached only when the plan slot is empty.
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
4. **Compose** via `compose(state, process_state)`, where the reader maps the
   hook event and tool name to the target-neutral process state.
   statusLine mode receives no hook stdin payload and composes with
   `process_state=None` (the composer applies the active icon for non-terminal
   phases and the ✅ override for terminal ones); hook mode parses the JSON
   payload Claude Code writes to stdin (best-effort — missing/malformed input
   yields `process_state=None` and never raises).
5. **Emit the title** on the appropriate output channel (see Output Channels).
   `None`/empty composed string → no-op.

### `session push-title-token` — bind + persist state

`session_push_title_token(plan_id, icon=None)` is the canonical **bind + persist
seam** shared by every persisted-title-state change. It reads the plan's title
state from `status.json` via `_read_title_state`, composes via
`compose(state, None, icon_override=icon)`, and persists the composed state for
the next render event to deliver. It **writes no escape sequence and repaints
nothing** — per Channel Delivery Contract ruling (a) the `/dev/tty` write is
deleted, and per ruling (b2) the paired repaint is deferred to the next hook
event. The `--icon` argument is **optional**: a glyph state (⏳/🔒 from the lock
machinery) supplies it, while a plain state refresh omits it (`icon=None`) to
keep the default active icon. Two consumers drive this one seam:

- **`manage-status`'s phase-write drive seam** — an icon-less state persist on
  every `current_phase` write (see State above); and
- **`manage-locks/merge_lock.py`** — the ⏳/🔒 lock-state writes on
  acquire/block, AND a plain icon-less write on the release/clear path so the
  next render drops the lock glyph.

`build-busy` is NOT a consumer of this seam. The render-hook bracket
(`PreToolUse:Bash` / `PostToolUse:Bash`) mutates the in-memory state dict
directly and persists through `manage-status title-token set/clear --owner
build-hook`, and the orchestrator wait seam persists through `title-token set
--owner cli` (see [`await-long-running`](../../plan-marshall/workflow/await-long-running.md)
§ step (b)) — neither calls `session push-title-token`.

With `store="orchestrator"` (the orchestrator-epic variant driven by the
orchestrator's per-verb call) the seam additionally **establishes the
session→epic binding** (`bind_orchestrator`), so the next hook render resolves
the epic and delivers its title. That binding side effect is the load-bearing
reason the seam survives ruling (a) at all. The orchestrator variant also gates
on the feature-activation signal, returning `reason: feature_inactive` when the
terminal-title feature is configured off.

It is best-effort and never raises, and its outcome is **observable** rather than
silently swallowed. The no-op outcomes are distinguished on the return TOON:

| Outcome | `reason` |
|---------|----------|
| State absent / unrenderable | `no_title_state` |
| Feature configured off (`store="orchestrator"` variant) | `feature_inactive` |
| State composed and persisted | _(absent)_ |

The return carries no `pushed` flag and no `delivery` field: both described the
deleted `/dev/tty` channel, and a seam that never repaints has no delivery result
to report. Delivery is the next render event's outcome, not this seam's.

### Session-Plan Binding

The session identifier is bound to a plan through a filesystem cache rooted at
`_SESSION_CACHE_BASE` (`~/.cache/plan-marshall/sessions`):

```text
~/.cache/plan-marshall/sessions/{session_id}/active-plan            →   plan_id
~/.cache/plan-marshall/sessions/{session_id}/active-orchestrator    →   epic slug
```

The parallel, **kind-disjoint** `active-orchestrator` slot binds the session to an
orchestrator **epic slug** instead of a plan. The two slots are **mutually
exclusive** — binding one kind clears the other (last-driven-wins across kinds), so
a session drives EITHER a plan OR an epic, never both. `session render-title`
resolves the plan slot first and falls back to the orchestrator slot (Step 2
above), so the orchestrator title reaches the PRIMARY hook channel; the epic
binding is established as a best-effort side effect of the orchestrator's per-verb
`push-title-token --store orchestrator` call (`bind_orchestrator`). The plan
read/write path (`active-plan` / `bind` / `resolve_plan`) is byte-for-byte
unchanged. `session teardown` / `unbind` is **kind-agnostic** — it removes both
slots — and `session doctor` treats an orchestrator-only session dir as a live
binding, never an orphan.

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
| `session teardown` | `session_binding.unbind` | **Activation-gated** end-of-session retire: drops the caller's OWN slot (see below). |

#### `session teardown` — activation-gated unbind

`session teardown` is the end-of-session counterpart of `session bind` /
`session render-title`. Order is load-bearing — the **activation signal is read
FIRST**:

- **Inactive** (`_terminal_title_active()` is False — no render-hook entry on any
  render-trigger event AND no `statusLine` command in either
  `.claude/settings.json` or `.claude/settings.local.json`): the verb returns
  `active: false` / `reason: feature_inactive` having mutated no binding and
  raised nothing. A project that never opted into terminal titles is never
  touched. Any settings read failure also reports inactive (fail-safe, not a
  guess).
- **Active**: the session id is resolved from `$CLAUDE_CODE_SESSION_ID` and
  `session_binding.unbind` drops the caller's own slot (pruning the now-empty
  session directory), reporting `unbound`.

The verb writes **no title reset escape**. Per Channel Delivery Contract ruling
(a) the only channel it could have written that reset on — `/dev/tty` — is
deleted, and per the binding rule *nothing may be reset on a channel that cannot
deliver*. Releasing the binding is the whole of the teardown.

**One call site drives it**: the `SessionStart:clear` render trigger (the
renderer branches on `source == "clear"`, performs the teardown, and writes
nothing to stdout). This is the **sole** binding-release point — ruling (b).
`manage-status cmd_archive` does **not** call it (see Archive interaction above).

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

#### Why a multi-session conflict is benign — no guard is needed

A plan bound by several live sessions is a **reportable observation, not a fault**.
Last-driven-wins needs no conflict guard because the binding surface is
**correct by construction** — three structural properties, each of which
independently removes the failure mode a guard would defend against:

- **(a) The lookup is forward-only.** `resolve_plan(session_id)` maps a session to
  a plan. There is no plan→session direction anywhere in the surface, so "which
  session owns this plan?" is a question no consumer can ask and no consumer does
  ask: the two callers of `session resolve-plan` —
  `marshall-orchestrator/workflow/close.md` and
  `marshall-orchestrator/workflow/archive.md` — both invoke it with **no
  `--session-id`**, resolving only their own caller session. A second session
  bound to the same plan is therefore invisible to every read path.
- **(b) `unbind` is self-scoped *on the teardown path*.** `session teardown`
  resolves the session id from the environment and removes only the **calling**
  session's own slot, so one session tearing down can never drop a sibling
  session's binding, and coexistence cannot produce a cross-session release
  there. The claim is scoped to that path deliberately: `session_binding`'s
  stale-slot GC (`_gc_slot`, reached from `doctor(fix=True)`) calls the same
  `unbind` primitive with **other** sessions' ids. That is the one sanctioned
  cross-session release, and it is safe for a different reason than
  self-scoping — the GC acts only on a slot it has already classified stale
  (its plan is gone AND its terminal state has been delivered), never on a live
  binding. Reading (b) as a system-wide invariant would misdescribe the GC;
  reading it as the teardown path's guarantee is exact.
- **(c) There is no `session close` verb.** The operations set is `capture` /
  `render-title` / `push-title-token` / `bind` / `resolve-plan` / `doctor` /
  `teardown` / `reload-directive`. No verb takes a plan id and acts on *whichever*
  session holds it, so no operation can be misdirected by a shared binding.

Consequently the `doctor` **conflict list is diagnostic-only by design** — it
surfaces "two tabs are driving this plan" for a human reading the report, and
nothing in the system branches on it. Fail-closing `resolve_plan` on a detected
conflict would add a guard for a consumer that does not exist, which is precisely
the speculative structure
[`persona-plan-marshall-agent`](../../persona-plan-marshall-agent/SKILL.md)
Principle 7 forbids. `bind` stays unconditional.

#### `session doctor` — reverse-index conflict scan + stale GC + orphan prune

`session doctor` visits **every directory** under
`~/.cache/plan-marshall/sessions/` — not only the ones that yield a readable
slot — builds an **in-memory plan→sessions reverse index** from the live slots,
and reports a **three-way** health picture:

- **conflicts** — any plan bound by more than one session (two sessions driving
  the same plan);
- **stale** slots — a slot whose bound plan is archived or deleted (its live plan
  dir, on main OR in its phase-5+ worktree, is gone) **and whose terminal state
  has already been delivered**. A slot whose archived plan still owes an
  undelivered terminal state is **exempt** and is not reported stale — the
  state-driven exemption of Channel Delivery Contract ruling (c); and
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
release-on-exit implicitly: an archived plan's slot becomes GC-eligible **once
its terminal state has been delivered**, so no separate `session release` verb is
needed.

##### Automatic caller and the main-anchored-caller invariant

The GC has an **automatic caller**: the `default:archive-plan` finalize step runs
`session doctor --fix` immediately after its `manage-status archive` call (see
[`phase-6-finalize/standards/archive-plan.md`](../../phase-6-finalize/standards/archive-plan.md)
§ "Sweep the session-binding store"). Sweeping *after* the archive is what lets the
finishing plan's own now-stale slot be collected in the same pass. Without this
caller the sweep has no scheduled invocation and the cache grows unboundedly.

The sweep's **reporting sink is the global work log** — `manage-logging work`
invoked without `--plan-id`. The record is machine-global housekeeping spanning
every plan's session slots, and the plan that triggered it has just been archived,
so a plan-scoped entry would be buried in an archived plan's own log.

**Main-anchored-caller invariant**: any caller of `session doctor --fix` MUST run
with cwd at the **main checkout**. `_plan_is_live` resolves plan directories
relative to the process cwd, so a sweep fired from inside a worktree would resolve
none of the main checkout's live plan dirs and would classify **every other live
plan's binding as archived**, GC'ing bindings that are still in use. The
`archive-plan` caller satisfies this structurally: it runs at `order: 1000`, after
`default:branch-cleanup` has removed the worktree, so cwd is already main.

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
statusLine text / sessionTitle described above.
The OpenCode implementation is a **no-op** — OpenCode has no equivalent
terminal-title channel, so the operation returns without emitting. The state side
(`manage-status`) and the composer (`manage-terminal-title`) are
platform-agnostic: `manage-status` persists the same `status.json` fields
regardless of target, the composer is a pure function, and only the
`platform-runtime` emit layer differs per platform.
