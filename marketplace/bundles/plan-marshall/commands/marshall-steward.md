---
name: marshall-steward
description: Project configuration wizard for planning system
allowed-tools: Read, Bash, Skill, AskUserQuestion
---

# /marshall-steward

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

## Execution

### Step 0: Verify Prerequisites

Before running any Python scripts, verify python3 is available:

```bash
command -v python3 >/dev/null 2>&1 && python3 --version
```

If python3 check fails, inform the user:
```
Error: python3 is required but not installed.
Please install Python 3.8+ and try again.
```

**Note**: Git availability is checked during CI detection (Step 6) and recorded in run-configuration.json.

### Step 1: Bootstrap Plugin Root

Get the plugin root path (cached in `.plan/marshall-state.toon` after first detection).

**If `.plan/marshall-state.toon` exists**, read `plugin_root` from it:
```
Read: .plan/marshall-state.toon
```

**If state file doesn't exist or lacks `plugin_root`**, find and run the bootstrap script:
```bash
python3 ~/.claude/plugins/cache/*/plan-marshall/*/skills/marshall-steward/scripts/bootstrap-plugin.py get-root
```

This detects the plugin root and caches it in `.plan/marshall-state.toon`. Extract `plugin_root` from the output.

Store the plugin root path for use in subsequent steps (e.g., `PLUGIN_ROOT=/Users/.../.claude/plugins/cache/plan-marshall`).

### Step 2: Determine Mode

Run the mode detection script using the plugin root (glob pattern handles any version):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/determine-mode.py mode
```

If `--wizard` flag was provided, skip to wizard mode regardless of output.

### Step 3: Route Based on Output

| mode | reason | Action |
|------|--------|--------|
| `wizard` | `executor_missing` | Read skill, start at "First-Run Wizard" Step 1 |
| `wizard` | `marshal_missing` | Read skill, start at "First-Run Wizard" Step 2 |
| `menu` | `both_exist` | Read skill, go to "Interactive Menu" |

### Step 4: Execute Skill

Resolve and read the skill file:

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/bootstrap-plugin.py resolve plan-marshall skills/marshall-steward/SKILL.md
```

Read the `resolved_path` from output and follow the skill instructions. Execute the section identified in Step 3.
