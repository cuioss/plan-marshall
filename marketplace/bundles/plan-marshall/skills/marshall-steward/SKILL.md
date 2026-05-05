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
| determine_mode | `plan-marshall:marshall-steward:determine_mode` | Determine wizard vs menu mode; also exposes `seed-blocking-finding-types` for the wizard's blocking-partition seed step |
| gitignore_setup | `plan-marshall:marshall-steward:gitignore_setup` | Configure .gitignore for .plan/ |
| bootstrap_plugin | _(direct Python call)_ | Detect plugin root, cache in `.plan/local/marshall-state.toon` |

### Delegated Scripts (require executor)

| Script | Notation | Purpose |
|--------|----------|---------|
| generate-executor | `plan-marshall:tools-script-executor:generate_executor` | Executor generation. Both surfaces (wizard Step 4 and maintenance "Regenerate Executor") detect whether they are running inside a git worktree (path under `.claude/worktrees/`) and, when so, pass `--marketplace-root <worktree-absolute-path>` so the generated executor's script mappings resolve against the worktree's `marketplace/bundles/` instead of the main checkout or the plugin cache. |
| manage-config | `plan-marshall:manage-config:manage-config` | Project-level marshal.json CRUD |
| run_config | `plan-marshall:manage-run-config:run_config` | Clean temp, logs, archived-plans, memory |
| ci_health | `plan-marshall:tools-integration-ci:ci_health` | CI provider detection |
| permission_doctor | `plan-marshall:tools-permission-doctor:permission_doctor` | Permission analysis |
| permission_fix | `plan-marshall:tools-permission-fix:permission_fix` | Permission fixes |
| extension_discovery | `plan-marshall:extension-api:extension_discovery` | Extension config defaults |
| credentials | `plan-marshall:manage-providers:credentials` | External tool provider management |

---

## Prerequisites

The `/marshall-steward` command must set `${PLUGIN_ROOT}` before loading this skill:

1. Run `bootstrap_plugin.py get-root` (direct Python call with glob) to detect plugin root
2. Set `${PLUGIN_ROOT}` to the returned path
3. The plugin root is cached in `.plan/local/marshall-state.toon` for subsequent calls

---

## Step 1: Determine Mode

Determine whether to run wizard or menu based on existing files.

**BOOTSTRAP**: Since execute-script.py may not exist yet, use DIRECT Python call with glob:

```bash
DETERMINE_MODE=$(ls ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/determine_mode.py | head -n 1)
python3 "$DETERMINE_MODE" mode
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
| `wizard-flow.md` | First-run wizard steps 1-16 (includes architecture_refresh tier prompts at Step 13d) | mode=wizard or --wizard flag |
| `menu-maintenance.md` | Regenerate executor, cleanup | Menu option 1 |
| `menu-healthcheck.md` | Verify setup, diagnose issues | Menu option 2 |
| `menu-configuration.md` | Build systems, skill domains, architecture refresh tier knobs | Menu option 3 |
| `menu-recipes.md` | Built-in recipes available in the wizard | Linked from `menu-configuration.md` |
| `shared-settings.md` | **DEPRECATED** — Plan phases, review gates, quality pipelines now delegate to `manage-config` | Retained for transition reference only |
| `error-handling.md` | Error types and recovery | On error conditions |

---

## Blocking-Finding Partition Seed (Wizard Step)

After `marshal.json` is initialised the wizard seeds a default per-phase **blocking-finding partition** into each phase slot. The partition drives the `pending_findings_blocking_count` invariant in `phase-handshake` (see [`plan-marshall:plan-marshall/references/phase-handshake.md`](../plan-marshall/references/phase-handshake.md)) — it determines which finding types refuse the phase boundary advance when their `pending` count is non-zero.

**Wizard step** (runs once on first-run wizard, after `marshal.json` exists):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode \
  seed-blocking-finding-types
```

**Effect on `marshal.json`**: writes `plan.phase-{phase}.blocking_finding_types` for every phase slot whose key is currently absent. Phase slots that already declare `blocking_finding_types` are left untouched — the seed never clobbers a user customisation.

**Default partition:**

| Phase slot | Default `blocking_finding_types` |
|------------|----------------------------------|
| `phase-1-init` | `["build-error", "test-failure", "lint-issue", "sonar-issue", "qgate"]` |
| `phase-2-refine` | `["build-error", "test-failure", "lint-issue", "sonar-issue", "qgate"]` |
| `phase-3-outline` | `["build-error", "test-failure", "lint-issue", "sonar-issue", "qgate"]` |
| `phase-4-plan` | `["build-error", "test-failure", "lint-issue", "sonar-issue", "qgate"]` |
| `phase-5-execute` | `["build-error", "test-failure", "lint-issue", "sonar-issue", "qgate"]` |
| `phase-6-finalize` | `["build-error", "test-failure", "lint-issue", "sonar-issue", "qgate", "pr-comment"]` |

**Rationale:**

- **Block at every phase boundary**: `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate` — these are correctness gates that must clear before any phase advances.
- **Block only inside `6-finalize`**: `pr-comment` — PR review feedback is only meaningful once a PR exists, which happens during finalize.
- **Never block** (omitted from every partition): `insight`, `tip`, `best-practice`, `improvement` — long-lived knowledge types that accumulate across plans and should not gate an active boundary.

**Idempotency contract:** the seed is safe to re-run. Each subsequent invocation skips every phase whose `blocking_finding_types` key is already present (status `unchanged`). Projects override the defaults by editing `marshal.json` directly; the seed will never overwrite a manual edit.

**Output (TOON)** when at least one phase was newly written:

```toon
status	success
seed_status	seeded
seeded_count	6
skipped_count	0
seeded	phase-1-init,phase-2-refine,phase-3-outline,phase-4-plan,phase-5-execute,phase-6-finalize
```

When every phase already has the key:

```toon
status	success
seed_status	unchanged
seeded_count	0
skipped_count	6
skipped	phase-1-init,phase-2-refine,phase-3-outline,phase-4-plan,phase-5-execute,phase-6-finalize
```

When `marshal.json` is missing:

```toon
status	success
seed_status	missing_marshal
seeded_count	0
skipped_count	0
```

## Architecture Refresh Tier Knobs

The wizard and the maintenance Configuration submenu both expose two `architecture_refresh` tier knobs that drive the `phase-6-finalize` `architecture-refresh` step. The canonical schema, defaults, and value contract are owned by `plan-marshall:manage-run-config` (see `manage-run-config/standards/run-config-standard.md` and the `architecture-refresh get-tier-0/get-tier-1/set-tier-0/set-tier-1` subcommands documented in `manage-run-config/SKILL.md`).

| Knob | Subcommand | Default | Allowed values |
|------|------------|---------|----------------|
| `architecture_refresh.tier_0` | `manage-run-config architecture-refresh set-tier-0 --value {value}` | `enabled` | `enabled`, `disabled` |
| `architecture_refresh.tier_1` | `manage-run-config architecture-refresh set-tier-1 --value {value}` | `prompt` | `prompt`, `auto`, `disabled` |

Surfaces inside this skill:

| Surface | Reference | Section |
|---------|-----------|---------|
| First-run wizard | `references/wizard-flow.md` | Step 13d |
| Maintenance menu (returning users) | `references/wizard-flow.md` | Step 13d (reached via Configuration → Full Reconfigure, which re-runs the wizard from Step 5 onwards) |

Both surfaces share the same wizard-flow Step 13d question set, and both delegate persistence to the `manage-run-config architecture-refresh set-tier-*` subcommands — this skill never edits `run-config.json` directly.

---

## Built-In Recipes

The steward exposes the following built-in recipes (registered via `provides_recipes()` in `plan-marshall-plugin/extension.py`). Recipes are loaded by `phase-3-outline` when a plan's status metadata sets `plan_source=recipe` and `recipe_key=<key>`.

| Recipe key | Recipe skill | Default change_type | Scope |
|------------|--------------|---------------------|-------|
| `refactor-to-profile-standards` | `plan-marshall:recipe-refactor-to-profile-standards` | `tech_debt` | `codebase_wide` |
| `lesson_cleanup` | `plan-marshall:recipe-lesson-cleanup` | _derived from lesson kind_ (see below) | `single_lesson` |

**lesson_cleanup derived change_type**:

| Lesson kind | change_type |
|-------------|-------------|
| `bug` | `bug_fix` |
| `improvement` | `enhancement` |
| `anti-pattern` | `tech_debt` |

The `lesson_cleanup` recipe is auto-suggested by `phase-1-init` Step 5c when `source == lesson` and the lesson body is doc-shaped (no code-touching fences, no code-action verbs as primary subject). See `references/menu-recipes.md` for the wizard-facing description and `marketplace/bundles/plan-marshall/skills/recipe-lesson-cleanup/SKILL.md` for the recipe contract.

> **Note**: `shared-doc-check.md` content has been inlined into `wizard-flow.md` and `menu-maintenance.md`. For TOON output format, see `plan-marshall:ref-toon-format`.

---

## Error Handling

If an error occurs during execution:
```
Read references/error-handling.md
```
Apply the recovery guidance for the specific error type.

