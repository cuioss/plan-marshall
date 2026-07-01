# Menu Option: Terminal Title

Configure the dynamic terminal-title integration or override the active plan
for the current Claude Code session. When the integration is enabled, each
terminal tab shows the active plan-marshall plan, phase, and a live status
icon for the Claude Code session running in it. The same body also drives the
Claude Code statusLine inside the TUI.

Terminal-title configuration is a three-way split across surfaces shipped with
the plan-marshall bundle:

- **State** — `manage-status` persists `current_phase`, `short_description`, and
  the `title_token` field into `status.json` (the single source of persisted
  title state) on the relevant mutation paths. No user configuration is required.
  See
  [`../../manage-status/standards/status-lifecycle.md` § Title Token](../../manage-status/standards/status-lifecycle.md)
  for the state contract.
- **Composer** — the pure `plan-marshall:manage-terminal-title` library owns the
  `compose(state, event)` function plus the glyph and icon vocabulary; it is
  imported by the resolve+emit layer.
- **Resolve + emit** — the per-target `session render-title` operation
  (implemented in `plan-marshall:platform-runtime`) reads the title state from
  `status.json`, composes `{icon} {glyph} {body}` via the composer, and forwards
  the resulting OSC sequence (hook mode) or plain text (statusLine mode) to the
  controlling terminal.

See
[`../../manage-terminal-title/standards/terminal-title-architecture.md`](../../manage-terminal-title/standards/terminal-title-architecture.md)
for the full end-to-end architecture.

The remaining wiring is the set of hook entries that drive the reader on every
render-trigger event. **Action A** installs those entries into
`.claude/settings.local.json`. **Action B** sets the active-plan cache mapping
for the current session, overriding whichever plan id the executor's
write-through last published.

## Reachability

This option is reachable from the marshall-steward **Configuration** menu
(Main Menu → "3. Configuration" → "Terminal Title"), regardless of whether the
project is being set up for the first time or is already configured. A project
that already has `.claude/settings.local.json` and `.plan/marshal.json` reaches
this option the same way a fresh project does — the Configuration menu is not
gated behind first-run setup.

---

## Sub-Menu Prompt

Before either action runs, ask the user which one to take:

```text
AskUserQuestion:
  question: "Terminal Title — what would you like to do?"
  header: "Terminal Title"
  options:
    - label: "Configure hook wiring"
      description: "Install or repair the SessionStart (matcher-less + clear), UserPromptSubmit, Notification, Stop, PreToolUse:AskUserQuestion, PostToolUse:AskUserQuestion, PostToolUse:Bash render entries plus statusLine and env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE in ./.claude/settings.local.json (Action A)"
    - label: "Override active-plan for this session"
      description: "Write the cache mapping ${XDG_CACHE_HOME:-$HOME/.cache}/plan-marshall/sessions/$CLAUDE_CODE_SESSION_ID/active-plan so the next render trigger uses the selected plan (Action B)"
  multiSelect: false
```

On **Configure hook wiring** proceed to Action A. On **Override active-plan for
this session** proceed to Action B. The user may always return to the
Configuration menu by cancelling the prompt.

---

## Action A — Configure hook wiring

The detect → confirm → install flow below is the add/fix-into-existing-config
path: it installs every missing render entry, preserves entries already present,
and surfaces explicit prompts for the two conflict cases (`statusLine` /
`env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE` set to a different value).

### Step 1: Detect

Probe the current `.claude/settings.local.json` to discover what is already
wired up. Because the install operation is idempotent and reports a precise
per-event summary, the same call drives both detect and install — the
`installed_events` / `already_present_events` / `statusLine_status` / `env_status`
fields in the response distinguish the cases.

For a non-mutating probe before any user prompt, use the platform-runtime
health-check:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  health-check --checks all
```

Inspect the `display` entry in the `results` array. Its `detail` field reports
every required piece on its own line, each ending in `present` or `MISSING`. To
diagnose a partial install, scan the `detail` field for any line containing the
token `MISSING` — each such line names exactly one render entry, statusLine, or
env value that needs to be installed:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  health-check --checks display
```

The `detail` field enumerates all of these labels, in order:

- `SessionStart:matcher-less`
- `SessionStart:clear`
- `UserPromptSubmit`
- `Notification`
- `Stop`
- `PreToolUse:AskUserQuestion`
- `PostToolUse:AskUserQuestion`
- `PostToolUse:Bash`
- `statusLine`
- `env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE`

When `display` reports `healthy: true` (no line contains `MISSING`), everything
is wired up. Print an "already configured" message and return to the
Configuration menu WITHOUT prompting:

```text
Terminal title is already configured.

All seven render-trigger hook entries, the statusLine command, and the
CLAUDE_CODE_DISABLE_TERMINAL_TITLE env entry are present in
./.claude/settings.local.json. A fresh Claude Code session will drive the live
tab title and statusline automatically.
```

Otherwise proceed to Step 2.

### Step 2: Confirm

Prompt the user before writing anything:

```text
AskUserQuestion:
  question: "Enable the dynamic terminal title and statusLine? This installs seven render-trigger hook entries, a statusLine command, and an env entry into ./.claude/settings.local.json."
  header: "Terminal Title"
  options:
    - label: "Enable"
      description: "Install the SessionStart (matcher-less + clear), UserPromptSubmit, Notification, Stop, PreToolUse:AskUserQuestion, PostToolUse:AskUserQuestion, PostToolUse:Bash hook entries plus statusLine and env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE"
    - label: "Skip"
      description: "Make no changes; the terminal title stays disabled"
  multiSelect: false
```

On **Skip**: write nothing and return to the Configuration menu.

On **Enable**: proceed to Step 3.

### Step 3: Install

Install the full wiring by invoking `project install-hook`:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  project install-hook --target claude
```

Inspect the TOON response:

- `status: success` — the call landed; consult the per-piece summary below.
- `status: error` — report the `message` field and advise the user to check
  write permissions on `./.claude/settings.local.json`. Do not proceed to the
  conflict-resolution prompts.

#### Per-event summary

Two fields list which render-trigger events landed and which were already
present:

- `installed_events` — the events whose render entry was freshly inserted on
  this call. SessionStart counts once even though it gets two entries
  (matcher-less + `matcher: "clear"`).
- `already_present_events` — the events where our render entry was already
  installed (no write was needed).

The union of the two lists is always `["SessionStart", "UserPromptSubmit",
"Notification", "Stop", "PreToolUse:AskUserQuestion",
"PostToolUse:AskUserQuestion", "PostToolUse:Bash"]`. Report the breakdown so the
user can see exactly which entries were added:

```text
Installed render entries: <installed_events>
Already present:          <already_present_events>
```

#### statusLine conflict resolution

`statusLine_status` is one of `installed`, `already_present`,
`already_present_other`, or `overwritten`.

- `installed` / `already_present` / `overwritten` — no further prompt needed.
- `already_present_other` — `.claude/settings.local.json` already defines a
  `statusLine` whose command differs from the renderer. The install operation
  preserved that value. Prompt the user before overwriting:

  ```text
  AskUserQuestion:
    question: "An existing statusLine command was found in ./.claude/settings.local.json. Overwrite it with the plan-marshall renderer?"
    header: "Existing statusLine"
    options:
      - label: "Overwrite"
        description: "Replace the existing statusLine with `session render-title --statusline`"
      - label: "Keep existing"
        description: "Leave the existing statusLine command untouched; only hook entries and env will be installed"
    multiSelect: false
  ```

  On **Overwrite**: re-invoke `project install-hook` with
  `--overwrite-statusline`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
    project install-hook --target claude --overwrite-statusline
  ```

  Expect `statusLine_status: overwritten` in the response.

  On **Keep existing**: skip; report that the existing statusLine was kept.

#### env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE conflict resolution

`env_status` follows the same enum (`installed`, `already_present`,
`already_present_other`, `overwritten`).

- `installed` / `already_present` / `overwritten` — no further prompt needed.
- `already_present_other` — the env entry is already set to a value other than
  `"1"`. Prompt the user before overwriting:

  ```text
  AskUserQuestion:
    question: "env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE is already set in ./.claude/settings.local.json to a value other than \"1\". Overwrite it?"
    header: "Existing env"
    options:
      - label: "Overwrite"
        description: "Set CLAUDE_CODE_DISABLE_TERMINAL_TITLE to \"1\" so Claude Code does not overwrite our title"
      - label: "Keep existing"
        description: "Leave the existing env value untouched"
    multiSelect: false
  ```

  On **Overwrite**: re-invoke `project install-hook` with
  `--overwrite-env-disable`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
    project install-hook --target claude --overwrite-env-disable
  ```

  Expect `env_status: overwritten` in the response.

  On **Keep existing**: skip; report that the existing env value was kept.

The two prompts and re-invocations are independent — handle them in sequence
when both `already_present_other` signals fire, passing the appropriate flag(s)
on the follow-up call. The follow-up call may carry both flags at once when the
user consented to both overwrites.

#### Final report

Once all conflicts (if any) are resolved, report the outcome:

```text
Terminal title enabled.

Render hooks: <installed_events ∪ already_present_events>
statusLine:   <statusLine_status>
env entry:    <env_status>

Start a fresh Claude Code session to see the live tab title and statusline
(plan, phase, status icon).
```

After completion, return to the Configuration menu.

---

## Action B — Override active-plan for this session

The active-plan cache mapping at
`${XDG_CACHE_HOME:-$HOME/.cache}/plan-marshall/sessions/$CLAUDE_CODE_SESSION_ID/active-plan`
is normally populated on the first `/plan-marshall` invocation in a session
(the executor's write-through publishes the plan id alongside the command it
ran). Until that first invocation lands, a fresh session shows the host
terminal's default title; this action is the explicit override path for setting
the active plan up front, or for switching to a different plan mid-session.

The override is **session-scoped**: the cache mapping lives under the current
`$CLAUDE_CODE_SESSION_ID` directory, so closing the terminal and opening a new
one starts from an empty mapping again (the next `/plan-marshall` invocation
in the new session will repopulate it via the executor write-through).

### Step 1: Precondition — session id must be set

Read `$CLAUDE_CODE_SESSION_ID`. When unset, print:

```text
Cannot override active plan: $CLAUDE_CODE_SESSION_ID is not set. The override
sub-action must be invoked from inside a Claude Code session.
```

and return to the Configuration menu.

### Step 2: Enumerate active plans

List all plans whose `current_phase ∉ {complete, archived}`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list
```

The TOON contract for `list` carries `current_phase` per row; filter
client-side to retain only non-terminal plans. For each surviving plan, capture
`plan_id`, `current_phase`, and `short_description` from the row.

- **Zero active plans** → print `No active plans to choose from.` and return
  to the Configuration menu.
- **One active plan** → confirm via `AskUserQuestion`:

  ```text
  AskUserQuestion:
    question: "Set active plan for this session to `<plan_id>`?"
    header: "Override active plan"
    options:
      - label: "Confirm"
        description: "<current_phase> — <short_description>"
      - label: "Cancel"
        description: "Leave the current mapping untouched"
    multiSelect: false
  ```

  On **Confirm**: proceed to Step 3 with the single plan id. On **Cancel**:
  return to the Configuration menu.

- **Multiple active plans** → present them via `AskUserQuestion` with
  `multiSelect: false`; each option carries `label: <plan_id>` and
  `description: "<current_phase> — <short_description>"` sourced from
  `status.json`. The user's selection is the override target.

### Step 3: Write the cache mapping

Resolve the cache path with `XDG_CACHE_HOME` honored:

```text
${XDG_CACHE_HOME:-$HOME/.cache}/plan-marshall/sessions/$CLAUDE_CODE_SESSION_ID/active-plan
```

Write atomically (write to a sibling temp file, then rename) so a partial write
cannot corrupt the cache. Create the session directory with parents as needed.

### Step 4: Report

On success, print:

```text
Active plan for session $CLAUDE_CODE_SESSION_ID set to <plan_id>.
The next render-trigger event (next prompt, notification, or stop) will
update the tab title.
```

On any I/O failure, surface the OS error and advise the user to check write
permissions on the cache directory:

```text
Failed to write active-plan cache mapping: <os_error>.
Check write permissions on ${XDG_CACHE_HOME:-$HOME/.cache}/plan-marshall/sessions/.
```

After completion, return to the Configuration menu.
