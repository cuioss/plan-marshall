# Menu Option: Terminal Title

Configure the dynamic terminal-title integration. When enabled, each terminal
tab shows the active plan-marshall plan, phase, and a live status icon for the
Claude Code session running in it.

Terminal-title configuration is split across two surfaces, both shipped with the
plan-marshall bundle:

- **Writer** — `manage-status` mutation paths publish `{plan_dir}/title-body.txt`
  whenever phase, short_description, or archive lifecycle changes. No user
  configuration is required to enable it. See
  [`../../manage-status/standards/status-lifecycle.md` § Title-Body Artifact](../../manage-status/standards/status-lifecycle.md)
  for the publication contract.
- **Reader** — the per-target `session render-title` operation (implemented in
  `plan-marshall:platform-runtime`) composes `{icon} {body}` from the active
  plan's `title-body.txt` and forwards the resulting OSC sequence to the
  controlling terminal.

The remaining wiring is the SessionStart hook that drives the reader on every
new Claude Code session. This menu option installs that hook into
`.claude/settings.local.json`.

## Reachability

This option is reachable from the marshall-steward **Configuration** menu
(Main Menu → "3. Configuration" → "Terminal Title"), regardless of whether the
project is being set up for the first time or is already configured. A project
that already has `.claude/settings.local.json` and `.plan/marshal.json` reaches
this option the same way a fresh project does — the Configuration menu is not
gated behind first-run setup.

The detect → confirm → install flow below is the add/fix-into-existing-config
path: it adds the SessionStart hook when absent and reports already-configured
(installing nothing) when present, so a user can add or fix the hook at any
point after initial setup.

---

## Step 1: Detect

Check whether the SessionStart hook is already installed by invoking the
`project install-hook` operation. Because the operation is idempotent, this
detect step and the install step share the same call — the `already_present`
field in the response distinguishes the two outcomes.

First, run the operation against `.claude/settings.local.json`:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  project install-hook --target .claude/settings.local.json
```

Do NOT run this command yet if you want to prompt before any write — see Step 2.
The recommended order is: prompt first (Step 2), then run the command (Step 3).
To detect without writing, the equivalent read-only signal is the
platform-runtime health-check `hook` check, which inspects
`.claude/settings.local.json`:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  health-check --checks all
```

Inspect the `hook` entry in the `results` array. When `healthy: true` and the
detail names `settings.local.json`, the hook is already installed — print an
"already configured" message and return to the Configuration menu WITHOUT
prompting:

```
Terminal title is already configured.

The SessionStart hook is present in ./.claude/settings.local.json. A fresh
Claude Code session will drive the live tab title automatically.
```

When the `hook` check is unhealthy (hook absent from both settings files),
proceed to Step 2.

---

## Step 2: Confirm

The hook is not yet installed. Prompt the user before writing anything:

```
AskUserQuestion:
  question: "Enable the dynamic terminal title? This installs a SessionStart hook into ./.claude/settings.local.json."
  header: "Terminal Title"
  options:
    - label: "Enable"
      description: "Install the SessionStart hook so each terminal tab shows the active plan and phase"
    - label: "Skip"
      description: "Make no changes; the terminal title stays disabled"
  multiSelect: false
```

On **Skip**: write nothing and return to the Configuration menu.

On **Enable**: proceed to Step 3.

---

## Step 3: Install

Install the SessionStart hook by invoking `project install-hook`:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  project install-hook --target .claude/settings.local.json
```

Inspect the TOON response:

- `status: success` with `already_present: false` — the hook was installed.
  Report success:

  ```
  Terminal title enabled.

  The SessionStart hook was installed into ./.claude/settings.local.json. Start
  a fresh Claude Code session to see the live tab title (plan, phase, status
  icon).
  ```

- `status: success` with `already_present: true` — the hook was already there
  (a race between detect and install). Report already-configured.

- `status: error` — report the `message` field and advise the user to check
  write permissions on `./.claude/settings.local.json`.

---

After completion, return to the Configuration menu.
