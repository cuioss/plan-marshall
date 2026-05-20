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
2. **Plan + phase** — uses the worktree-cwd plan-id resolution below, which verifies the resolved plan is still active before rendering. Reads `current_phase` from the resolved plan's `status.json`. Shown as `{icon} pm:{phase}[:{short_description}]`, where the `:{short_description}` segment is appended only when a `short_description` value is present in `status.json`. When `current_phase` is `complete` or `archived` (terminal phases), the resolution falls through as if no phase were found.

   The `short_description` is auto-derived from the plan title at creation time by `manage-status:manage_status create` — lesson-id noise is stripped from the title and spaces are replaced with underscores, producing a compact human-readable suffix. No runtime truncation is applied.
3. **Session active-plan cache** — second-tier plan-id source consulted only when the worktree-cwd resolution (precedence step 2) returns no plan. The cache lives at `~/.cache/plan-marshall/sessions/{session_id}/active-plan` and is written by the executor (`.plan/execute-script.py`, generated from `execute-script.py.template`) on every invocation carrying `--plan-id X` or `--audit-plan-id X`. The reader walks up from the hook's `cwd` to the nearest `.plan`-bearing ancestor, locates the cached plan's `status.json` there, and renders `{icon} pm:{phase}[:{short_description}]` after verifying the plan is alive and non-terminal (same terminal-phase guard as step 2). The cache is keyed by `session_id`, so concurrent Claude Code tabs operating on different plans render independent titles — cross-tab isolation is preserved by construction.
4. **Active slash command** — captured on `UserPromptSubmit` from the hook stdin payload's `prompt` field when it starts with `/`, stored per `session_id` at `~/.cache/plan-marshall/sessions/{session_id}/active-command`, and cleared on `Stop`/`SessionStart`. Shown as `{icon} {command}` when no plan/phase resolves. An alias map collapses selected verbose command names to shorter labels; today the only entry is `plan-marshall:plan-marshall` → `pm`. All other commands display verbatim.
5. **Fallback** — `{icon} claude` when neither a plan/phase nor an active command is known.

## Plan-id resolution

When a plan-id is needed (precedence step 2 above), the script resolves it first from the hook's cwd: when the cwd is inside `.plan/local/worktrees/<id>/`, the worktree directory name is the plan_id. The match is gated by an `os.path.isdir(cwd)` check on the full cwd, so a stale cwd that string-matches a removed worktree path is discarded. The cwd is per-hook-invocation and cannot leak across Claude Code tabs, which keeps concurrent sessions isolated: a freshly opened tab outside any worktree directory renders the active-command segment or the `◯ claude` fallback regardless of the parent shell's environment.

When the cwd resolution returns no plan-id (precedence step 3 above), the script consults the session active-plan cache. It reads `~/.cache/plan-marshall/sessions/{session_id}/active-plan`, validates the cached value's shape (non-empty, no path separators, no `..`/`.`, length-bounded), walks up from the hook's `cwd` to the nearest `.plan`-bearing ancestor to anchor `status.json` resolution, and uses the cached plan-id only when `status.json` exists and `current_phase` is non-terminal. Any failure along the chain (missing cache, malformed value, missing `status.json`, terminal phase) falls through to the next precedence tier.

When neither resolution path yields a plan, no plan is rendered; the title falls back to precedence step 4 (active slash command) or step 5 (`claude`).

## Hook output contract

Hook-mode invocations (no `--statusline`) emit `{"terminalSequence": "<OSC>"}` as JSON on stdout per Claude Code 2.1.141+. Claude Code's hook-output parser reads the payload and forwards the escape sequence to the controlling terminal. This replaces the pre-2.1.139 `/dev/tty` write path, which is no longer available to hook subprocesses.

The `--statusline` path is unchanged: the title is written verbatim to stdout for Claude Code's `statusLine` command to consume.

The script silently falls back on any read/write error — hooks never break the session.

See [hook-authoring-guide.md](hook-authoring-guide.md) for the general JSON envelope contract that applies to any new hook-driven plan-marshall script.

Configure via `/marshall-steward` → **Configuration** → **Terminal Title** — the wizard writes only to `./.claude/settings.local.json` (project-local, per-developer, gitignored). See [menu-terminal-title.md](../../marshall-steward/references/menu-terminal-title.md).
