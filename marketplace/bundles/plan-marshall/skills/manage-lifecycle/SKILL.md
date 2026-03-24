---
name: manage-lifecycle
description: Plan lifecycle operations - discovery, phase transitions, archiving, and routing
user-invocable: false
---

# Manage Lifecycle Skill

Plan lifecycle operations including discovery, phase transitions, archiving, and routing context.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify .plan/ files directly; all mutations go through the script API
- Do not invent script arguments not listed in the Script API table
- Do not skip phase transition validation

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle {command} {args}`
- Phase transitions must use the `transition` command (never manual file edits)
- Routing context is read-only; use `get-routing-context` for combined state

## Script API

Script: `plan-marshall:manage-lifecycle:manage-lifecycle`

| Command | Parameters | Description |
|---------|------------|-------------|
| `list` | `[--filter]` | Discover all plans |
| `transition` | `--plan-id --completed` | Transition to next phase |
| `archive` | `--plan-id [--dry-run]` | Archive completed plan |
| `route` | `--phase` | Get skill for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |
