---
name: marshall-steward
description: Project configuration wizard for planning system. Manages executor generation, health checks, build systems, and skill domains.
user-invocable: true
---

# Marshall Steward Skill

Project configuration wizard for the planning system.

## Usage

```
/marshall-steward           # Interactive menu or first-run wizard
/marshall-steward --wizard  # Force first-run wizard
```

## Banner

Output this banner directly as text at command start (do NOT use Bash echo - output it in your response):

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                 :                                     ║
║                               .;:;.                                   ║
║                              :;:::;:                                  ║
║          ...             .;:::::::::;.              ...               ║
║          .::;:::::::::::::;:::::::::;:::::::::::::;::.                ║
║               :;:::::::::::::::::::::::::::::::;:                     ║
║                .;:::::::::::::::::::::::::::::;.                      ║
║                                                                       ║
║                        █▀█ █   █▀█ █▄ █                               ║
║                        █▀▀ █▄▄ █▀█ █ ▀█                               ║
║                  █▀▄▀█ █▀█ █▀█ █▀ █ █ █▀█ █   █                       ║
║                  █ ▀ █ █▀█ █▀▄ ▄█ █▀█ █▀█ █▄▄ █▄▄                     ║
║                                                                       ║
║                .;:::::::::::::::::::::::::::::;.                      ║
║               :;:::::::::::::::::::::::::::::::;:                     ║
║          .::;:::::::::::::;:::::::::;:::::::::::::;::.                ║
║         ...              .;:::::::::;.              ...               ║
║                              :;:::;:                                  ║
║                               .;:;.                                   ║
║                                 :                                     ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Enforcement

**Execution mode**: Run scripts exactly as documented; return to Main Menu after each operation.

**Prohibited actions:**
- Do not invent alternative menu structures or options
- Do not end without returning to menu (unless Quit)
- Do not summarize what you are about to do instead of doing it
- Do not improvise script execution; run exactly as documented

**Constraints:**
- Bootstrap scripts use direct Python paths with glob
- All other scripts use `python3 .plan/execute-script.py {notation} ...`
- After any operation completes, return to Main Menu
- Only exit when user selects "Quit"

---

## What This Skill Provides

**Wizard Mode**: Sequential setup for new projects (executor generation, marshal.json init, build detection, skill domains)

**Menu Mode**: Interactive maintenance for returning users (regenerate executor, health check, configuration)

---

## Scripts

### Own Scripts (bootstrap-capable, run before executor exists)

| Script | Notation | Purpose |
|--------|----------|---------|
| determine_mode | `plan-marshall:marshall-steward:determine_mode` | Determine wizard vs menu mode |
| gitignore_setup | `plan-marshall:marshall-steward:gitignore_setup` | Configure .gitignore for .plan/ |
| bootstrap_plugin | _(direct Python call)_ | Detect plugin root, cache in `.plan/marshall-state.toon` |

### Delegated Scripts (require executor)

| Script | Notation | Purpose |
|--------|----------|---------|
| generate-executor | `plan-marshall:tools-script-executor:generate_executor` | Executor generation |
| manage-config | `plan-marshall:manage-config:manage-config` | Project-level marshal.json CRUD |
| run_config | `plan-marshall:manage-run-config:run_config` | Clean temp, logs, archived-plans, memory |
| ci_health | `plan-marshall:tools-integration-ci:ci_health` | CI provider detection |
| permission_doctor | `plan-marshall:tools-permission-doctor:permission_doctor` | Permission analysis |
| permission_fix | `plan-marshall:tools-permission-fix:permission_fix` | Permission fixes |
| extension_discovery | `plan-marshall:extension-api:extension_discovery` | Extension config defaults |

---

## Prerequisites

The `/marshall-steward` command must set `${PLUGIN_ROOT}` before loading this skill:

1. Run `bootstrap_plugin.py get-root` (direct Python call with glob) to detect plugin root
2. Set `${PLUGIN_ROOT}` to the returned path
3. The plugin root is cached in `.plan/marshall-state.toon` for subsequent calls

---

## Step 1: Determine Mode

Determine whether to run wizard or menu based on existing files.

**BOOTSTRAP**: Since execute-script.py may not exist yet, use DIRECT Python call with glob:

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/determine_mode.py mode
```

**Output (TOON)**:
```toon
mode	wizard
reason	executor_missing
```

### Mode Routing

| mode | reason | Action |
|------|--------|--------|
| `wizard` | `executor_missing` | Load: `Read references/wizard-flow.md` → Execute wizard |
| `wizard` | `marshal_missing` | Load: `Read references/wizard-flow.md` → Execute wizard |
| `menu` | `both_exist` | Show Main Menu below |

### Check for `--wizard` Flag

If `--wizard` flag provided, force wizard regardless of determine_mode result:
```
Read references/wizard-flow.md
```
Execute the wizard flow from that file.

---

## Interactive Menu (Returning User)

Display menu when both executor and marshal.json exist.

### Main Menu

```
AskUserQuestion:
  question: "What would you like to do?"
  header: "Main Menu"
  options:
    - label: "1. Maintenance"
      description: "Regenerate executor, clean logs"
    - label: "2. Health Check"
      description: "Verify setup, diagnose issues"
    - label: "3. Configuration"
      description: "Build systems, skill domains"
    - label: "4. Quit"
      description: "Exit plan-marshall"
  multiSelect: false
```

### Menu Routing

| User Selection | Action |
|----------------|--------|
| "1. Maintenance" | Load: `Read references/menu-maintenance.md` → Execute |
| "2. Health Check" | Load: `Read references/menu-healthcheck.md` → Execute |
| "3. Configuration" | Load: `Read references/menu-configuration.md` → Execute |
| "4. Quit" | Output "Good bye!" → STOP |

After any menu option completes, return to Main Menu (except Quit).

---

## Deferred Loading Pattern

This skill uses **progressive disclosure** to minimize context usage:

1. **Core skill loads**: ~150 lines (this file - routing logic only)
2. **On wizard mode**: Load `references/wizard-flow.md` (~250 lines)
3. **On menu selection**: Load only the selected reference (~100-150 lines)

### How to Load a Reference

When routing indicates to load a reference:
```
Read references/{file}.md
```
Then execute the workflow described in that file. Each reference file is loaded in full when its menu path is chosen — only one reference is active at a time.

---

## Available References

| Reference | Purpose | Load When |
|-----------|---------|-----------|
| `wizard-flow.md` | First-run wizard steps 1-16 | mode=wizard or --wizard flag |
| `menu-maintenance.md` | Regenerate executor, cleanup | Menu option 1 |
| `menu-healthcheck.md` | Verify setup, diagnose issues | Menu option 2 |
| `menu-configuration.md` | Build systems, skill domains | Menu option 3 |
| `shared-settings.md` | **DEPRECATED** — Plan phases, review gates, quality pipelines now delegate to `manage-config` | Retained for transition reference only |
| `error-handling.md` | Error types and recovery | On error conditions |

> **Note**: `shared-doc-check.md` content has been inlined into `wizard-flow.md` and `menu-maintenance.md`. For TOON output format, see `plan-marshall:ref-toon-format`.

---

## Error Handling

If an error occurs during execution:
```
Read references/error-handling.md
```
Apply the recovery guidance for the specific error type.

