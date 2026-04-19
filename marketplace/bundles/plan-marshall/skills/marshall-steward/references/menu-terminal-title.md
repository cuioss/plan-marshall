# Menu Option: Terminal Title

Configure dynamic terminal titles + statusline for Claude Code sessions. Writes hook entries and a `statusLine` command into `~/.claude/settings.json` and/or `./.claude/settings.json` so each terminal tab reflects the active plan-marshall phase and live status (`running`, `waiting`, `idle`, `done`).

The hooks invoke `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/set_terminal_title.py` by absolute path — no executor or plugin cache dependency at runtime.

---

## Step 1: Choose Scope

```
AskUserQuestion:
  question: "Where should the terminal-title hooks be written?"
  header: "Scope"
  options:
    - label: "Both (Recommended)"
      description: "Global (~/.claude/settings.json) + Project (./.claude/settings.json)"
    - label: "Global"
      description: "~/.claude/settings.json only"
    - label: "Project"
      description: "./.claude/settings.json only"
  multiSelect: false
```

Remember the selected scope — it drives which settings.json files are patched in Step 4.

---

## Step 2: Choose Icon Set

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

## Step 3: Resolve Script Path

Read `${PLUGIN_ROOT}` from `.plan/local/marshall-state.toon` and compute the absolute path to the script:

```
{PLUGIN_ROOT}/plan-marshall/<version>/skills/plan-marshall/scripts/set_terminal_title.py
```

Glob `{PLUGIN_ROOT}/plan-marshall/*/skills/plan-marshall/scripts/set_terminal_title.py` and pick the first (and only) match. Abort with a clear error if the script is missing — the user likely needs to run `/sync-plugin-cache` first.

---

## Step 4: Patch settings.json

For each selected target (`~/.claude/settings.json` and/or `./.claude/settings.json`):

1. Read the existing settings.json (or start from `{}` if the file is missing).
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
    ]
  }
}
```

The two `SessionStart` entries are intentional: the matcher-less entry covers `startup` / `resume` / `compact`, and the `matcher: "clear"` entry restores the title after `/clear` so the user can reuse the session without a stale label.

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

### Merge procedure

The marshall-steward skill writes the merge as a small inline Python operation (no new helper script):

1. `import json`; load existing settings (or `{}`).
2. Ensure `settings["hooks"]` exists.
3. For each of the four event keys, append the new entry objects to `settings["hooks"][event]` (create the list if missing).
4. Set `settings["statusLine"]` to the command dict unless the user declined the overwrite.
5. `json.dump(settings, path, indent=2)` with `sort_keys=False` to preserve key order.

---

## Step 5: Test It

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

---

After completion, return to Main Menu.
