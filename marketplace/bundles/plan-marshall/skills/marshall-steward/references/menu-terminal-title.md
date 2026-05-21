# Menu Option: Terminal Title

Terminal-title configuration is split across two surfaces:

- **Writer** — `manage-status` mutation paths publish `{plan_dir}/title-body.txt` whenever phase, short_description, or archive lifecycle changes. This is built into the plan-marshall bundle; no user configuration is required to enable it. See [`../../manage-status/standards/status-lifecycle.md` § Title-Body Artifact](../../manage-status/standards/status-lifecycle.md) for the publication contract.
- **Reader** — the per-target `session render-title` operation (implemented in `plan-marshall:platform-runtime`) composes `{icon} {body}` from the active-command-state cache plus `title-body.txt` and forwards the resulting OSC sequence to the controlling terminal.

Until a per-target reader is available, `marshall-steward` does NOT install any terminal-title hooks; the writer publishes state, but no surface is configured to consume it. The wizard MUST surface this state to the user and otherwise no-op.

---

## Step 1: Inform and Exit

Print the following to the user, then return to Main Menu:

```
Terminal title configuration is pending.

The writer side (plan-marshall publishes {plan_dir}/title-body.txt on every
status mutation) ships with the bundle and is already active. The reader side
(per-target `session render-title` operation that composes `{icon} {body}` and
forwards the OSC sequence to the terminal) is specified in the cluster-01
platform-api design doc and will land per-target as that work completes.

No hooks were written to ./.claude/settings.local.json. Re-run this menu
once the per-target reader is available.
```

The wizard MUST NOT write any hook entries, `statusLine` entries, or
`CLAUDE_CODE_DISABLE_TERMINAL_TITLE` env keys to `./.claude/settings.local.json`
until the per-target reader is integrated.

---

After completion, return to Main Menu.
