# PLAN-26: terminal-title-refresh-cadence

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Operator-surfaced 2026-07-20 (screenshots: tab title stuck at `pm:2-refine`/`pm:4-plan`
> while the footer correctly showed `pm:6-finalize`/done). **Root cause orchestrator-VERIFIED against
> source** (findings inlined). Re-ground line citations at outline — current as of `main` @ `464f53ec1`.

## Objective

The terminal TAB TITLE frequently freezes at an early plan phase while the in-terminal FOOTER shows the
correct current phase. Make the title track phase as reliably as the footer does — the two must not
diverge — and pin the consistency with a test so it cannot silently regress again. Additionally, give the
title a **teardown lifecycle**: on `/clear` (and when the bound plan is closed/archived) reset the title
to a neutral default and clear the stale session→plan binding — strictly as a **no-op when the
terminal-title feature is not activated**.

## Verified root cause (orchestrator, 2026-07-20)

**Title and footer SHARE composition but DIVERGE at delivery cadence.** Both call the same pure
`compose()` over the same `status.json` via `session_render_title()`
(`platform-runtime/scripts/_claude_runtime_impl.py`, ~line 400; `statusline` flag splits footer-emit vs
title-emit). It is **not** a composition bug, **not** a dedup/"write-only-if-changed" guard (none exists),
and **not** #931's `drop_stale_build_busy` (that only clears a stale 🔨 token). The divergence is entirely
in *when each is delivered*:

- **Footer** = `statusLine=True` → `sys.stdout.write(composed)` as plain text, registered as Claude Code's
  `statusLine` command (`claude_runtime.py:158`). **Claude Code re-invokes statusLine continuously in the
  main UI process**, so the footer is always fresh.
- **Title** = `statusLine=False` → OSC-0 envelope, emitted only on discrete triggers: (a) title-render
  hook events (`claude_runtime.py:139-142`) — for the MAIN session the reliably-delivered ones
  (`UserPromptSubmit`, `Stop`) fire **only at turn boundaries**; and (b) the unified phase-write seam's
  `/dev/tty` repaint (`_status_core.py` `_surface_drive`→`_drive_repaint`→`session_push_title_token`,
  `_claude_runtime_impl.py:489-496`).

**Two silent-failure gates make (b) unreliable:**
1. `session_push_title_token` writes `open("/dev/tty","w")` inside `try/except OSError: pushed=False` — so
   when the phase transition runs **without the user's controlling terminal** (a Task sub-agent, a
   worktree, a backgrounded/detached process — all normal in phase-5 execute and phase-6 finalize),
   `/dev/tty` raises and the title is **never repainted**, with no surfaced error.
2. The whole delegation is fire-and-forget: `_status_core._run_executor` uses `subprocess.run(..,
   check=False)` and swallows failures at DEBUG.

**Net:** when the orchestrator walks phases 2→3→4→5→6 within a SINGLE long agent turn, the main session
fires no `UserPromptSubmit`/`Stop` until the run ends, and the `/dev/tty` repaint no-ops off the
controlling terminal — so the title freezes at the phase painted at the last main-session turn boundary
(`2-refine`/`4-plan`), while the continuously-polled footer advances. "Often but not always" because a
transition occasionally coincides with a delivered hook or a repaint that does reach the tty.

**No test asserts footer/title consistency** — existing tests check each seam in isolation
(`test__claude_runtime_impl.py` footer-only; `test_manage_status_transition.py:1348` asserts only that
`_surface_drive` is *called*, not that the OSC reaches a terminal or matches the footer phase). That gap
is why the divergence shipped.

## Deliverables

### D1 — give the title a refresh cadence that tracks phase within a long turn

The footer is fresh because it rides the continuously-polled `statusLine` invocation; the title has no
equivalent continuous trigger. **Fix:** deliver the title on a signal that fires as reliably as the
footer does, so the tab title advances with the phase during a long multi-phase turn. **Confirm the exact
seam at outline** — the leading candidate is to have the continuously-invoked `statusLine` path ALSO
carry the title (the footer already re-composes every poll; the open question is whether Claude Code's
`statusLine` output can carry a `terminalSequence`/OSC alongside the plain-text footer, or whether a
different reliably-continuous title mechanism exists). **A `claude-code-guide` consult at outline is
warranted** to confirm the host contract before committing to a seam — do NOT guess it. **Acceptance:**
during a single agent turn that transitions through ≥2 phases, the tab title reflects the current phase
(not a stale earlier one) without depending on a turn-boundary hook.

### D2 — stop the in-turn title path from silently no-opping off the controlling terminal

The `/dev/tty` repaint is currently the primary in-turn refresh AND it silently fails whenever the writer
lacks a controlling terminal (the common phase-5/6 case). **Fix:** route the in-turn title through a path
that does not require the phase-writing process to own the user's tty (e.g. the host `terminalSequence`
envelope the hook path already uses, rather than a direct `/dev/tty` write), and/or demote `/dev/tty` to
an explicitly-labelled fallback whose failure is observable rather than DEBUG-swallowed. **Do NOT** just
raise the log level and call it fixed — the defect is that this is the *primary* path for in-turn
refresh, not that its logging is quiet. **Confirm at outline** how this composes with D1 (they may be one
mechanism). **Acceptance:** a phase transition executed from a sub-agent / worktree / process without a
controlling tty still updates the tab title; the failure of a `/dev/tty` fallback is surfaced, not
silent.

### D3 — pin footer/title consistency with a regression test

Add the coverage whose absence let this ship: after a phase write, assert the tab title and the footer
render the SAME phase, AND that the title is delivered when the writer lacks a controlling tty (simulate
the sub-agent/worktree case). **Also cover D4's teardown in both feature states:** with the feature ON,
`/clear`/archive reset the title and clear the binding; with the feature OFF, `/clear`/archive do NO
title write and NO binding mutation and raise nothing. **Acceptance:** a test fails if the title lags the
footer after a transition, if the title delivery silently no-ops without a controlling terminal, or if the
D4 teardown fails to reset when ON or does anything at all when OFF. Mirror the
"provenance/real-condition" discipline this epic favours — assert against the actual divergence shape,
not a hand-mocked happy path.

### D4 — title teardown on `/clear` + session-binding cleanup, activation-gated no-op

When a session is reset via `/clear` (and when the bound plan is closed/archived), the tab title should
be reset to a neutral default (candidate: `plan-marshall` — confirm the exact string at outline) rather
than left frozen at the last plan's phase, and the now-stale session→plan binding should be removed so a
fresh session does not inherit a dead binding. **Two triggers, confirm both seams at outline:** (a)
`/clear` — a host event; **whether `/clear` is hookable at all (a clear/session-reset event) is a
host-contract question for the SAME `claude-code-guide` consult D1 needs** — do NOT guess it; if no
`/clear` hook exists, record that and fall back to the next session-start reset. (b) plan close/archive —
the existing `phase-6-finalize` archive / `manage-status archive` path, where the binding for the retired
plan is dropped.

**Hard guard (load-bearing, operator-stated): this MUST be a pure no-op when the terminal-title feature
is not activated.** The teardown reads the activation flag first and, when the feature is off, does
nothing and raises nothing — it must never write a title escape, never touch `/dev/tty`, and never error
a `/clear` or an archive that would otherwise succeed. The title feature is opt-in; teardown that fires
regardless would regress a user who never enabled it. **Acceptance:** with the feature ON, `/clear`
resets the title to the default and clears the session binding, and closing/archiving the bound plan
drops its binding; with the feature OFF, `/clear` and archive behave exactly as today (no title write,
no binding mutation, no new error path). Covered by the D3 regression suite (both feature states).

## Out of scope / do NOT expand
- The `compose()` string format / icon logic — composition is correct and shared; do NOT touch it.
- #931's `drop_stale_build_busy` build-busy-token logic — unrelated to the phase lag.
- The footer/statusLine mechanism itself — it works; D1 may READ from it but must not regress it.
- Redesigning the hook event list wholesale — target the delivery cadence, not the hook taxonomy, unless
  outline shows a hook change is the minimal correct seam.

## Absorbs
- Operator-surfaced defect "terminal tab title shows a stale phase while the footer is correct,
  intermittently" (2026-07-20).
- Operator-surfaced requirement "on `/clear`, reset the title to a neutral default and clear the stale
  session→plan binding (and on plan close/archive); must be a pure no-op when the feature is off"
  (2026-07-21) → D4.

## Expected Surface
- `platform-runtime/scripts/_claude_runtime_impl.py` — `session_render_title` (title vs footer emit),
  `session_push_title_token` (the swallowed `/dev/tty` write) + `claude_runtime.py` (statusLine
  registration + title-hook event list)
- `manage-status/scripts/_status_core.py` — `_surface_drive`/`_drive_repaint`/`_run_executor` (the
  fire-and-forget repaint delegation) + the phase writers (`_cmd_lifecycle.py` `cmd_transition`,
  `_status_query.py` `cmd_set_phase`)
- `manage-terminal-title` — pure `compose()` (READ-ONLY; do not change format) + the feature-activation
  flag the D4 no-op guard reads (confirm its location — likely `marshal.json`/`manage-config`)
- the `/clear` host event seam (D4a — pending the claude-code-guide consult on whether a clear/reset hook
  exists) + the session→plan binding store (confirm location at outline) + the plan close/archive path
  (`phase-6-finalize` archive / `manage-status archive`) for D4b binding cleanup
- tests: footer/title-same-phase-after-transition; title-delivered-without-controlling-tty;
  clear-resets-title-and-binding-when-on; clear-and-archive-are-noop-when-off

## Dependencies and Sequencing
- Depends on: none. **Needs a `claude-code-guide` consult at outline** — now covering BOTH the D1 host
  contract (can `statusLine` carry a `terminalSequence`/OSC) AND the D4a question (is `/clear` hookable —
  a clear/session-reset event) before the seams are chosen.
- Surface-disjoint from PLAN-20/21/22/23/24/25 — `manage-terminal-title`/`platform-runtime`/`_status_core`
  title path is touched by none of them. **Note:** D4b touches the plan close/archive path, and PLAN-29
  MAY touch `platform-runtime` if it picks the Runtime-op route — confirm no region overlap at outline;
  expected disjoint (title/session-binding vs waiting-op). Startable in parallel with any of them.

## Size / split guard
4 deliverables — under the ~6 presumption. D1 and D2 may collapse into one mechanism at outline (a single
reliable-delivery seam covering both the cadence and the no-tty case); if so, effective count is 3 (that
seam + D3 pin + D4 teardown). D4 is a coherent add on the same title/session-binding surface, not a second
plan. **Split trigger:** if the claude-code-guide consult finds `/clear` is NOT hookable and D4a needs a
substantial alternative delivery mechanism, ship D1–D3 + D4b (archive-path binding cleanup, which needs no
host hook) and stage D4a as a follow-up — recorded as an epic decision. Do not let a missing `/clear` hook
block the phase-lag fix.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-26-terminal-title-refresh-cadence.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-26.md is recorded}
