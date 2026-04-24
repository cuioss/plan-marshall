# Menu Option: Terminal Title

Configure dynamic terminal titles + statusline for Claude Code sessions. Writes hook entries, a `statusLine` command, and the `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` env key into `./.claude/settings.local.json` (project-local, per-developer, gitignored by Claude Code convention) so each terminal tab reflects the active plan-marshall phase and live status (`running`, `waiting`, `idle`, `done`).

The hooks invoke `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/set_terminal_title.py` by absolute path — no executor or plugin cache dependency at runtime.

---

## Step 1: Choose Icon Set

```
AskUserQuestion:
  question: "Which icon set should the title use?"
  header: "Icons"
  options:
    - label: "Unicode (Recommended)"
      description: "▶ running, ? waiting, ◯ idle, ✓ done"
    - label: "Text-only"
      description: "> running, ? waiting, . idle, done done (for terminals without Unicode)"
  multiSelect: false
```

The current script ships only the Unicode set. "Text-only" is reserved for a future ASCII build — if selected today, fall back to Unicode and inform the user.

---

## Step 2: Resolve Script Path

Read `${PLUGIN_ROOT}` from `.plan/local/marshall-state.toon` and compute the absolute path to the script:

```
{PLUGIN_ROOT}/plan-marshall/<version>/skills/plan-marshall/scripts/set_terminal_title.py
```

Glob `{PLUGIN_ROOT}/plan-marshall/*/skills/plan-marshall/scripts/set_terminal_title.py` and pick the first (and only) match. Abort with a clear error if the script is missing — the user likely needs to run `/sync-plugin-cache` first.

---

## Step 3: Patch settings.local.json

Patch the project-local `./.claude/settings.local.json` (create the file with `{}` if it does not yet exist):

1. Read the existing `./.claude/settings.local.json` (or start from `{}` if the file is missing).
2. Merge the following entries **without clobbering** any existing hooks (`PreToolUse`, `PostToolUse`, etc. must stay intact). Within each event array, append the new entry; do not replace entries written by other integrations.
3. Write the file atomically (write-then-rename).

### Hook entries to merge

```jsonc
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python3 <ABS_PATH>/set_terminal_title.py idle" }] },
      { "matcher": "clear", "hooks": [{ "type": "command", "command": "python3 <ABS_PATH>/set_terminal_title.py idle" }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "python3 <ABS_PATH>/set_terminal_title.py running" }] }
    ],
    "Notification": [
      { "hooks": [{ "type": "command", "command": "python3 <ABS_PATH>/set_terminal_title.py waiting" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "python3 <ABS_PATH>/set_terminal_title.py idle" }] }
    ],
    "PostToolUse": [
      { "matcher": "AskUserQuestion", "hooks": [{ "type": "command", "command": "python3 <ABS_PATH>/set_terminal_title.py running" }] }
    ]
  }
}
```

The two `SessionStart` entries are intentional: the matcher-less entry covers `startup` / `resume` / `compact`, and the `matcher: "clear"` entry restores the title after `/clear` so the user can reuse the session without a stale label.

The `PostToolUse` / `AskUserQuestion` entry closes the waiting loop: `Notification` fires `waiting` when Claude blocks on an `AskUserQuestion`, but Claude Code emits no event when the user's answer returns to Claude — `UserPromptSubmit` only fires on fresh prompts from the input box. Without this hook the title would stay `?` for the rest of the turn until `Stop`. The `PostToolUse` hook with `matcher: "AskUserQuestion"` fires as soon as the tool result is delivered to Claude, re-stamping `running` (idempotent — if the title is already `▶`, the re-stamp is a no-op).

### Statusline entry to merge

```jsonc
{
  "statusLine": {
    "type": "command",
    "command": "python3 <ABS_PATH>/set_terminal_title.py --statusline idle"
  }
}
```

If an existing `statusLine` is present, ask the user before overwriting — they may have a custom command there.

### Env entry to merge

```jsonc
{
  "env": {
    "CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1"
  }
}
```

Disables Claude Code's built-in OSC title emitter so our hook-set title is not overwritten (tracked in anthropic/claude-code issues #3396, #4765, #15802, #23355).

Handle the existing `settings["env"]["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"]` value with the same three-branch pattern used for `statusLine`:

- **Absent**: insert the key with value `"1"`.
- **Present with value `"1"`**: no-op (already correct).
- **Present with any other value**: ask the user via `AskUserQuestion` before overwriting. Respect the user's choice — if they decline, leave the existing value untouched.

### Merge procedure

The marshall-steward skill writes the merge as a small inline Python operation (no new helper script):

1. `import json`; load existing `./.claude/settings.local.json` (or `{}` if the file is missing).
2. Ensure `settings["hooks"]` exists.
3. For each of the five event keys (`SessionStart`, `UserPromptSubmit`, `Notification`, `Stop`, `PostToolUse`), append the new entry objects to `settings["hooks"][event]` (create the list if missing). Dedup on the exact `command` string within each matcher group so re-running the wizard on a previously-configured project does not duplicate entries.
4. Set `settings["statusLine"]` to the command dict unless the user declined the overwrite.
5. Ensure `settings["env"]` exists, then apply the three-branch logic above to set `settings["env"]["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] = "1"` (unless the user declined an overwrite of a non-`"1"` existing value).
6. `json.dump(settings, path, indent=2)` with `sort_keys=False` to preserve key order.

---

## Step 4: Test It

Print the following instructions to the user:

```
Terminal title configured.

Try it out:
  1. Open a new VS Code / Ghostty / iTerm terminal tab.
  2. `cd` into a plan worktree (e.g. `.claude/worktrees/<plan-id>`)
     OR: `export PLAN_ID=<plan-id>` for a non-worktree shell.
  3. Start `claude`.
  4. Watch the tab title flip between ▶ (running), ? (waiting), ◯ (idle),
     and ✓ (done) as you work.

Statusline will appear inside Claude Code's UI and mirror through
/remote-control clients (mobile/web).
```

### If your VS Code tab label doesn't change

VS Code's integrated terminal ignores OSC title escape sequences by default — the tab label is controlled by VS Code, not the shell. If iTerm2 / Ghostty / Kitty / Terminal.app show the dynamic title correctly but VS Code does not, add the following to your VS Code user settings (`~/Library/Application Support/Code/User/settings.json` on macOS, or via `Cmd+,` → "Open Settings (JSON)"):

```jsonc
{
  "terminal.integrated.tabs.title": "${sequence}"
}
```

This is a VS Code-side setting; the wizard does not patch it because `settings.local.json` (Claude Code) and VS Code's user settings are distinct files owned by different tools. iTerm2, Ghostty, Kitty, and Terminal.app honor the OSC sequence out of the box and need no additional configuration.

---

After completion, return to Main Menu.
