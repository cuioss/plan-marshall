# Plan — Terminal-title `build-busy` (🔨) does not clear on phase transition

**Command:** `/plan-marshall task="implement .plan/plan-optimization/plans/plan-terminal-title-stale-build-busy.md"`
**Status:** queued — roadmap tail. Surface: `plan-marshall:manage-terminal-title` +
`claude_runtime.py` hook. Not yet checked for file-overlap against HS/EV/WT.
**Lane/posture:** surgical/bounded — single defect, no design-first work needed for the fix itself,
but the outline must first pin the exact trigger site(s) (see "What the outline must establish").

## Observed facts (confirmed by direct source read, 2026-07-15)

- Icon precedence in `compose()`: `terminal ✅ > build-busy 🔨 > icon_override > process icon`
  (`manage_terminal_title.py:236-245`). The actual fallback/default icon is `➤`
  (`resolve_icon`, `manage_terminal_title.py:134`) — 🔨 is never a default, only an explicit override.
- `title_token` is a field persisted in the **plan's `status.json`**, keyed by `plan_id`
  (`_status_core.py:49,64`). It is not scoped to the current session's Bash history and is not
  reset on phase transition — nothing in phase-1 through phase-6 clears it on entry or exit.
- Two production code paths SET `title_token=build-busy`:
  1. `PreToolUse:Bash` hook, auto-set only for the 4 build-wrapper notations (maven/gradle/npm/
     pyproject) via `_command_is_build` (`claude_runtime.py:231-257`,
     `_claude_runtime_impl.py:382-389`).
  2. `persona-plan-marshall-agent/standards/agent-behavior-rules.md:314-322` instructs agents to
     manually bracket **any** long-running orchestration call with `build-busy` — explicitly
     including "a resolved build / verify / coverage canonical command, a `git push`, a CI-wait,
     or any long git/shell op" — via `manage-status title-token set --state build-busy`.
- `title_token` is CLEARED only by: (a) the agent's own explicit obligation after the bracketed op
  completes (same standards doc), or (b) plan archival, which pops it unconditionally
  (`_cmd_lifecycle.py:271-275`). There is no clear on phase-boundary, no staleness timeout, and no
  clear tied to Task/execution-context dispatch itself.
- Observed symptom (screenshot, 2026-07-15 16:10): 3 concurrent plans — `marshall-steward_upgrade`
  at 5-execute, `hardening-sweep` at 4-plan, `ext-point-verify-consumers` at 4-plan — ALL showed 🔨
  simultaneously. phase-4-plan (task-creation) does not itself invoke any build-wrapper command, so
  the icon on those two sessions cannot be explained by a build running *in that phase*.
- **One dangling arm observed and self-reported live (2026-07-15, a 5-execute session).** The agent's
  own transcript: background command "Run whole-tree module-tests detached (orchestrator-tier)" **was
  stopped**; the agent then reported *"build-busy is still armed (state not yet handled) — retrying the
  detached module-tests run since the prior attempt was killed before producing output."* This confirms
  ONE concrete dangling path: a **detached orchestrator-tier build killed before producing output**
  leaves the arm set, because the clear obligation lives after the op's completion and that completion
  never arrives. Scope of what this proves: it accounts for the 5-execute session only — the two
  4-plan sessions never reach a build op and their arm source remains unidentified. Note also that
  recovery here depended on the agent *noticing* the stale arm in its own state and retrying; there
  was no mechanism that would have surfaced or healed it otherwise.

**Upstream cause of the confirmed path — now DIAGNOSED. See
[`../../plan-server/plans/plan-background-build-kill.md`](../../plan-server/plans/plan-background-build-kill.md)
and the evidence in [`../../plan-server/background-build-kill-forensics.md`](../../plan-server/background-build-kill-forensics.md).**
**The Claude Code harness kills `run_in_background` jobs externally** (90 kills / 23 days / 2 repos;
decisive: a bare `sleep 300` killed at 72 s; confirmed upstream as
[claude-code#25188](https://github.com/anthropics/claude-code/issues/25188)). The wrapper is killed
from outside, so the `build-busy` clear obligation is never reached. **Sequencing:** landing BK first
may shrink or dissolve this plan's scope — the killed-detached-build path is TT's only confirmed
dangling source. Decide ordering before scheduling.

## What is NOT yet established (do not pre-decide; outline must confirm)

- The arm source for the two **4-plan** sessions. The killed-detached-build path above is confirmed
  for the 5-execute session but cannot apply here (no build op is reached in phase-4-plan). Crash,
  compaction, a missed completion notification, or a long git/shell op bracketed per
  `agent-behavior-rules.md:314-322` are all plausible — none confirmed. Read each plan's
  `status.json` / decision log history before assuming which op it was.
- Whether the killed-detached-build path is the *dominant* source or merely one of several. One
  confirmed instance is not a frequency claim.
- Whether the fix should be (a) a phase-transition-safe reset, (b) a staleness check (e.g. token
  older than N minutes / no matching in-flight process → treat as stale), (c) tightening the
  clear-obligation call sites so they can't be skipped, or (d) some combination. This is a design
  decision for the outline, not pre-answered here.

## Constraints

- Do not weaken the existing signal for genuinely long-running ops (build/push/CI-wait still need
  a visible indicator) — the fix must close the staleness gap without losing the live signal.
- Tests: reproduce a dangling `build-busy` token and prove the fix's mechanism resolves it — either
  by clearing on the next phase transition or by detecting and self-healing the stale state. The
  killed-detached-build case above gives a concrete repro shape: arm the token, start a detached
  op, kill it before it produces output, assert the token does not stay armed indefinitely.

## Lifecycle (handled like a plan source)

Move into the plan's own directory on creation. **After archive:** add the §3 Shipped row, remove
this plan's §4 queue row in `HANDOVER.md`, update `00-README.md`.
