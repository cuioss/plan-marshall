---
name: marshall-steward-claude-wizards
description: Claude-only configuration wizards split out of marshall-steward. Owns the Terminal Title and PreToolUse Enforcement Hook install/repair flows and their health-check twin, which write .claude/settings.local.json wiring that only the Claude Code harness consumes.
targets: [claude]
mode: workflow
---

# Marshall Steward — Claude-Only Wizards

This skill is a **Claude-only** fragment of the target-neutral
`marshall-steward` skill. It exists because the surfaces it owns — the dynamic
terminal-title render-hook wiring and the conditional PreToolUse enforcement
hook — install entries into the resolved **Claude** settings file
(`.claude/settings.local.json`) and drive the Claude-specific `statusLine` and
`$CLAUDE_CODE_SESSION_ID` session machinery. Nothing in here has meaning on a
non-Claude harness, so the skill is scoped `targets: [claude]` and reaches no
other component-tree target.

The target-neutral `marshall-steward` skill keeps the banner, the menu shape,
and every menu that is meaningful on every harness; its Configuration menu and
Health Check route the Terminal Title and Enforcement Hook options here only
when running on Claude. On a non-Claude target those rows are absent, and no
surface here implies a working wizard there.

## Reachability

These flows are reached from `marshall-steward`:

- **Configuration → Terminal Title** — run the
  `references/menu-terminal-title.md` flow.
- **Configuration → Enforcement Hook** — run the
  `references/menu-enforcement-hook.md` flow.
- **Health Check Step 6b** — the terminal-title-hook check twin documented in
  `marshall-steward/references/menu-healthcheck.md`.

Each reference is loaded in full and executed, then control returns to the
caller's Configuration / Health menu.

## References

| Reference | Purpose | Load When |
|-----------|---------|-----------|
| `menu-terminal-title.md` | Two-action sub-menu: install render-hook wiring; override active-plan for the current session | Configuration → Terminal Title |
| `menu-enforcement-hook.md` | Detect→confirm→install sub-menu for the conditional PreToolUse enforcement hook (orthogonal `--enforcement` install) | Configuration → Enforcement Hook |

## Enforcement

These flows are Claude-only by construction. Do not retro-fit them onto a
non-Claude harness, and do not present a wizard here as working on a harness
that does not consume `.claude/settings.local.json`.
