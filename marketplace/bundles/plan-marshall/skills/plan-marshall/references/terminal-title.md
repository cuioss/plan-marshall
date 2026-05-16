# Terminal Title Integration

Each Claude Code session tab can display the active plan, current phase, active slash command, and a live status icon (`▶` running, `?` waiting, `◯` idle, `✓` done). The integration is hook-driven — five `hooks` entries and one `statusLine` entry invoke [`../scripts/set_terminal_title.py`](../scripts/set_terminal_title.py) by absolute path:

| Claude Code event | Status arg | Effect |
|-------------------|-----------|--------|
| `SessionStart` (matcher-less) | `idle` | Initial label on startup / resume / compact |
| `SessionStart` (`matcher: "clear"`) | `idle` | Restores the label after `/clear` so the session can be reused |
| `UserPromptSubmit` | `running` | Flips to `▶` when Claude begins work; captures the leading `/command` token (if any) into a session-scoped state file |
| `Notification` | `waiting` | Flips to `?` when Claude is blocked on input |
| `PostToolUse` (`matcher: "AskUserQuestion"`) | `running` | Flips back to `▶` after the user answers an `AskUserQuestion` — Claude Code emits no dedicated "tool result returned" event, so this hook closes the `Notification → waiting` loop |
| `Stop` | `idle` | Returns to `◯` when the turn ends and clears the session-scoped command state |
| `statusLine` command | — | Prints the same title to Claude Code's statusline (mirrored via `/remote-control`) |
| `phase-6-finalize` Step 7 | `done --plan-label {short_description}` | Emits `✓ pm:done:{short_description}` once after `default:archive-plan` returns, signalling plan completion. Stateless: sticks until the next hook overwrites it |

The script resolves the title with this precedence:

1. **Explicit `done` + `--plan-label`** — fired by `phase-6-finalize` Step 7 after the plan is archived and the worktree removed. Bypasses cwd/status.json resolution entirely and renders `✓ pm:done:{short_description}` from the caller-supplied label. The emission is stateless; the next `UserPromptSubmit` hook naturally overwrites it with `▶ …`.
2. **Plan + phase** — uses the three-strategy plan-id resolution chain below, then reads `current_phase` from the resolved plan's `status.json`. Shown as `{icon} pm:{phase}[:{short_description}]`, where the `:{short_description}` segment is appended only when a `short_description` value is present in `status.json`.

   The `short_description` is auto-derived from the plan title at creation time by `manage-status:manage_status create` — lesson-id noise is stripped from the title and spaces are replaced with underscores, producing a compact human-readable suffix. No runtime truncation is applied.
3. **Active slash command** — captured on `UserPromptSubmit` from the hook stdin payload's `prompt` field when it starts with `/`, stored per `session_id` at `~/.cache/plan-marshall/sessions/{session_id}/active-command`, and cleared on `Stop`/`SessionStart`. Shown as `{icon} {command}` when no plan/phase resolves. An alias map collapses selected verbose command names to shorter labels; today the only entry is `plan-marshall:plan-marshall` → `pm`. All other commands display verbatim.
4. **Fallback** — `{icon} claude` when neither a plan/phase nor an active command is known.

## Plan-id resolution (strategies tried in order)

When a plan-id is needed (precedence step 2 above), the script tries these strategies in order and uses the first match:

1. **Worktree cwd regex** — when the hook's cwd is inside `.plan/local/worktrees/<id>/`, the worktree directory name is the plan_id. Matches the common case where the user runs Claude Code from inside the plan's isolated worktree.
2. **`$PLAN_ID` environment variable** — when an explicit `PLAN_ID` is exported into the hook subprocess environment, its (stripped) value is the plan_id.
3. **Active-plan scan** — when the first two strategies miss (typical for sessions running in the main checkout root), the script scans `<git-common-dir>/../.plan/local/plans/*/status.json` for plans whose `current_phase` is one of the six in-progress phases (`1-init` through `6-finalize`). Returns the plan_id of the most-recently-modified `status.json` when at least one match exists; returns nothing when only archived/complete plans are present. The mtime tiebreaker matches user expectation (latest activity wins).

## Hook output contract

Hook-mode invocations (no `--statusline`) emit `{"terminalSequence": "<OSC>"}` as JSON on stdout per Claude Code 2.1.141+. Claude Code's hook-output parser reads the payload and forwards the escape sequence to the controlling terminal. This replaces the pre-2.1.139 `/dev/tty` write path, which is no longer available to hook subprocesses.

The `--statusline` path is unchanged: the title is written verbatim to stdout for Claude Code's `statusLine` command to consume.

The script silently falls back on any read/write error — hooks never break the session.

Configure via `/marshall-steward` → **Configuration** → **Terminal Title** — the wizard writes only to `./.claude/settings.local.json` (project-local, per-developer, gitignored). See [menu-terminal-title.md](../../marshall-steward/references/menu-terminal-title.md).
