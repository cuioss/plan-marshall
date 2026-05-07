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

1. **Explicit `done` + `--plan-label`** — fired by `phase-6-finalize` Step 7 after the plan is archived and the worktree removed. Bypasses cwd/status.json resolution entirely and renders `✓ pm:done:{short_description}` from the caller-supplied label. The OSC write is stateless; the next `UserPromptSubmit` hook naturally overwrites it with `▶ …`.
2. **Plan + phase** — from the worktree cwd (`.claude/worktrees/<id>`) or the `$PLAN_ID` env variable, reading `current_phase` from the main checkout's `status.json`. Shown as `{icon} pm:{phase}[:{short_description}]`, where the `:{short_description}` segment is appended only when a `short_description` value is present in `status.json`.

   The `short_description` is auto-derived from the plan title at creation time by `manage-status:manage_status create` — lesson-id noise is stripped from the title and spaces are replaced with underscores, producing a compact human-readable suffix. No runtime truncation is applied.
3. **Active slash command** — captured on `UserPromptSubmit` from the hook stdin payload's `prompt` field when it starts with `/`, stored per `session_id` at `~/.cache/plan-marshall/sessions/{session_id}/active-command`, and cleared on `Stop`/`SessionStart`. Shown as `{icon} {command}` when no plan/phase resolves. An alias map collapses selected verbose command names to shorter labels; today the only entry is `plan-marshall:plan-marshall` → `pm`. All other commands display verbatim.
4. **Fallback** — `{icon} claude` when neither a plan/phase nor an active command is known.

The script silently falls back on any read/write error — hooks never break the session.

Configure via `/marshall-steward` → **Configuration** → **Terminal Title** — the wizard writes only to `./.claude/settings.local.json` (project-local, per-developer, gitignored). See [menu-terminal-title.md](../../marshall-steward/references/menu-terminal-title.md).
