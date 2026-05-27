# Menu Option: Terminal Title

Configure the dynamic terminal-title integration. When enabled, each terminal
tab shows the active plan-marshall plan, phase, and a live status icon for the
Claude Code session running in it. The same body also drives the Claude Code
statusLine inside the TUI.

Terminal-title configuration is split across two surfaces, both shipped with the
plan-marshall bundle:

- **Writer** — `manage-status` mutation paths publish `{plan_dir}/title-body.txt`
  whenever phase, short_description, or archive lifecycle changes. No user
  configuration is required to enable it. See
  [`../../manage-status/standards/status-lifecycle.md` § Title-Body Artifact](../../manage-status/standards/status-lifecycle.md)
  for the publication contract.
- **Reader** — the per-target `session render-title` operation (implemented in
  `plan-marshall:platform-runtime`) composes `{icon} {body}` from the active
  plan's `title-body.txt` and forwards the resulting OSC sequence (hook mode)
  or plain text (statusLine mode) to the controlling terminal.

The remaining wiring is the set of hook entries that drive the reader on every
render-trigger event. This menu option installs them into
`.claude/settings.local.json`. A single invocation of `project install-hook`
writes:

- `hooks.SessionStart` — two entries (matcher-less + `matcher: "clear"`) plus
  the existing session-capture entry (preserved when present).
- `hooks.UserPromptSubmit`, `hooks.Notification`, `hooks.Stop` — one
  matcher-less render entry each.
- `hooks.PostToolUse` — one entry with `matcher: "AskUserQuestion"`.
- `statusLine` — the renderer in plain-text mode.
- `env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE` — set to `"1"` so Claude Code does
  not overwrite our title with its own.

## Reachability

This option is reachable from the marshall-steward **Configuration** menu
(Main Menu → "3. Configuration" → "Terminal Title"), regardless of whether the
project is being set up for the first time or is already configured. A project
that already has `.claude/settings.local.json` and `.plan/marshal.json` reaches
this option the same way a fresh project does — the Configuration menu is not
gated behind first-run setup.

The detect → confirm → install flow below is the add/fix-into-existing-config
path: it installs every missing render entry, preserves entries already present,
and surfaces explicit prompts for the two conflict cases (`statusLine` /
`env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE` set to a different value).

---

## Step 1: Detect

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

Inspect the `hook` entry in the `results` array. When `healthy: true` and the
detail names `settings.local.json`, the SessionStart capture hook is already
installed. Note that this signal alone does NOT prove the five render-trigger
events, statusLine, and env entries are present — the install operation in
Step 3 reports the full picture.

When the user wants to know exactly which pieces are present without writing,
parse `.claude/settings.local.json` directly and look for the renderer command
string

```
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session render-title
```

across `hooks.SessionStart`, `hooks.UserPromptSubmit`, `hooks.Notification`,
`hooks.Stop`, `hooks.PostToolUse` (matcher `AskUserQuestion`), plus the
top-level `statusLine` and `env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE` keys.

When everything is already present, print an "already configured" message and
return to the Configuration menu WITHOUT prompting:

```
Terminal title is already configured.

All five render-trigger hook entries, the statusLine command, and the
CLAUDE_CODE_DISABLE_TERMINAL_TITLE env entry are present in
./.claude/settings.local.json. A fresh Claude Code session will drive the live
tab title and statusline automatically.
```

Otherwise proceed to Step 2.

---

## Step 2: Confirm

Prompt the user before writing anything:

```
AskUserQuestion:
  question: "Enable the dynamic terminal title and statusLine? This installs five render-trigger hook entries, a statusLine command, and an env entry into ./.claude/settings.local.json."
  header: "Terminal Title"
  options:
    - label: "Enable"
      description: "Install the SessionStart (matcher-less + clear), UserPromptSubmit, Notification, Stop, PostToolUse:AskUserQuestion hook entries plus statusLine and env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE"
    - label: "Skip"
      description: "Make no changes; the terminal title stays disabled"
  multiSelect: false
```

On **Skip**: write nothing and return to the Configuration menu.

On **Enable**: proceed to Step 3.

---

## Step 3: Install

Install the full wiring by invoking `project install-hook`:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  project install-hook --target .claude/settings.local.json
```

Inspect the TOON response:

- `status: success` — the call landed; consult the per-piece summary below.
- `status: error` — report the `message` field and advise the user to check
  write permissions on `./.claude/settings.local.json`. Do not proceed to the
  conflict-resolution prompts.

### Per-event summary

Two fields list which render-trigger events landed and which were already
present:

- `installed_events` — the events whose render entry was freshly inserted on
  this call. SessionStart counts once even though it gets two entries
  (matcher-less + `matcher: "clear"`).
- `already_present_events` — the events where our render entry was already
  installed (no write was needed).

The union of the two lists is always `["SessionStart", "UserPromptSubmit",
"Notification", "Stop", "PostToolUse"]`. Report the breakdown so the user can
see exactly which entries were added:

```
Installed render entries: <installed_events>
Already present:          <already_present_events>
```

### statusLine conflict resolution

`statusLine_status` is one of `installed`, `already_present`,
`already_present_other`, or `overwritten`.

- `installed` / `already_present` / `overwritten` — no further prompt needed.
- `already_present_other` — `.claude/settings.local.json` already defines a
  `statusLine` whose command differs from the renderer. The install operation
  preserved that value. Prompt the user before overwriting:

  ```
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
    project install-hook --target .claude/settings.local.json --overwrite-statusline
  ```

  Expect `statusLine_status: overwritten` in the response.

  On **Keep existing**: skip; report that the existing statusLine was kept.

### env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE conflict resolution

`env_status` follows the same enum (`installed`, `already_present`,
`already_present_other`, `overwritten`).

- `installed` / `already_present` / `overwritten` — no further prompt needed.
- `already_present_other` — the env entry is already set to a value other than
  `"1"`. Prompt the user before overwriting:

  ```
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
    project install-hook --target .claude/settings.local.json --overwrite-env-disable
  ```

  Expect `env_status: overwritten` in the response.

  On **Keep existing**: skip; report that the existing env value was kept.

The two prompts and re-invocations are independent — handle them in sequence
when both `already_present_other` signals fire, passing the appropriate flag(s)
on the follow-up call. The follow-up call may carry both flags at once when the
user consented to both overwrites.

### Final report

Once all conflicts (if any) are resolved, report the outcome:

```
Terminal title enabled.

Render hooks: <installed_events ∪ already_present_events>
statusLine:   <statusLine_status>
env entry:    <env_status>

Start a fresh Claude Code session to see the live tab title and statusline
(plan, phase, status icon).
```

---

After completion, return to the Configuration menu.
