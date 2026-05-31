---
name: tools-permission-fix
description: Write operations for fixing and managing Claude Code permissions - add, remove, consolidate, ensure, apply-fixes, executor migration, wildcard generation.
user-invocable: true
---

# Permission Fix Skill

**PURPOSE**: Write operations for fixing and managing host-platform permissions, including marketplace permission synchronization and executor pattern migration.

**COMPLEMENTARY SKILL**: Use `plan-marshall:tools-permission-doctor` for read-only analysis before applying fixes.

## Enforcement

**Execution mode**: Run scripts exactly as documented; use `--dry-run` before applying changes.

**Prohibited actions:**
- Do not modify settings files without running analysis first (use `tools-permission-doctor`)
- Do not invent script arguments not listed in the operations table
- Do not skip dry-run verification for bulk operations

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix {command} {args}`
- Always use `--dry-run` first to preview changes before applying

## Script Reference

| Script | Notation | Purpose |
|--------|----------|---------|
| `permission_fix` | `plan-marshall:tools-permission-fix:permission_fix` | Write operations for permissions |

**Shared dependency**: Imports `permission_common` from `tools-permission-doctor/scripts/`. The executor's PYTHONPATH ensures this is resolvable.

## Operations

### apply-fixes - Apply Safe Fixes

Normalize paths, remove duplicates, sort, and add default permissions.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-fixes \
  --settings ~/.claude/settings.json \
  --dry-run
```

**Output (TOON)**:
```
duplicates_removed: 2
paths_fixed: 1
defaults_added[2]:
- Edit(.plan/**)
- Write(.plan/**)
sorted: true
changes_made: true
dry_run: true
```

### add - Add Permission

Add a single permission to settings.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix add \
  --permission "Bash(docker:*)" \
  --target project
```

**Output (TOON)**:
```
success: true
action: added
settings_file: /path/to/.claude/settings.json
```

### remove - Remove Permission

Remove a single permission from settings.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove \
  --permission "Bash(docker:*)" \
  --target project
```

**Output (TOON)**:
```
success: true
action: removed
settings_file: /path/to/.claude/settings.json
```

### ensure - Ensure Permissions Exist

Ensure multiple permissions exist (add missing, skip existing).

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure \
  --permissions "Bash(git:*),Bash(npm:*),Bash(docker:*)" \
  --target global
```

**Output (TOON)**:
```
success: true
added[1]:
- Bash(docker:*)
already_exists[2]:
- Bash(git:*)
- Bash(npm:*)
added_count: 1
total_permissions: 45
```

### consolidate - Consolidate Timestamped Permissions

Replace timestamped permissions with wildcards.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix consolidate \
  --settings ~/.claude/settings.json \
  --dry-run
```

**Output (TOON)**:
```
consolidated: 5
removed[2]:
- Read(target/output-2024-01-01.log)
- ...
wildcards_added[1]:
- Read(target/output-*.log)
dry_run: true
```

### ensure-wildcards - Ensure Marketplace Wildcards

Ensure all marketplace bundle wildcards exist in settings.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure-wildcards \
  --settings ~/.claude/settings.json \
  --marketplace-json marketplace/.claude-plugin/marketplace.json \
  --dry-run
```

**Output (TOON)**:
```
added[2]:
- Skill(new-bundle:*)
- SlashCommand(/new-bundle:*)
already_present: 14
total: 16
dry_run: true
```

### remove-redundant - Remove Redundant Permissions from Local Settings

Remove permissions from local/project settings that are exact duplicates of global settings,
covered by a broader global wildcard, or marketplace permissions that should live in global settings.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove-redundant \
  --scope both \
  --dry-run
```

Or with explicit paths:

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove-redundant \
  --global-settings ~/.claude/settings.json \
  --local-settings .claude/settings.json \
  --dry-run
```

**Output (TOON)**:
```
removed_redundant[2]:
- Bash(git:*)
- Edit(.plan/**)
moved_to_global[1]:
- Skill(pm-dev-java:*)
already_in_global[0]:
marketplace_skipped[0]:
removed_count: 2
moved_count: 1
dry_run: true
changes_made: true
applied: false
local_path: .claude/settings.json
global_path: /Users/me/.claude/settings.json
```

**Options**:
- `--move-marketplace` (default: true): Move marketplace permissions (Skill/SlashCommand) from local to global settings
- `--no-move-marketplace`: Skip moving marketplace permissions; only remove exact duplicates and wildcard-covered entries
- `--dry-run`: Preview changes without modifying files

**Usage**: Run after `tools-permission-doctor detect-redundant` to clean up permission drift. The health check in marshall-steward uses this operation to fix the "duplicate global rules + marketplace permissions in project-local settings" issue.

---

### apply-project-step-permissions - Add Skill() Rules for project: Steps

Append `Skill({skill})` allow rules for every `project:{skill}` entry in `marshal.json` under `phase-5-execute.steps` and `phase-6-finalize.steps` that does not already have a matching rule (exact or covering wildcard).

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-project-step-permissions \
  --marshal .plan/marshal.json \
  --settings .claude/settings.json \
  --dry-run
```

**Output (TOON)**:
```
added[1]:
- Skill(finalize-step-plugin-doctor)
missing[1]{skill,step,phase,rule}:
finalize-step-plugin-doctor	project:finalize-step-plugin-doctor	phase-6-finalize	Skill(finalize-step-plugin-doctor)
already_present[1]{skill,step,phase,covered_by}:
sync-plugin-cache	project:sync-plugin-cache	phase-6-finalize	Skill(sync-plugin-cache)
summary:
  added_count: 1
  already_present_count: 1
  project_steps_checked: 2
dry_run: true
applied: false
```

**Usage**: Pair with `tools-permission-doctor:detect-missing-project-step-permissions` to close the gap surfaced by the health check — run doctor to detect, then fix to apply.

## Target Selection

The `add`, `remove`, and `ensure` operations support `--target`:

| Target | File |
|--------|------|
| `global` | `~/.claude/settings.json` |
| `project` | `.claude/settings.json` or `.claude/settings.local.json` |

## Dry Run

All write operations support `--dry-run` to preview changes without modifying files.

## Integration with Permission Doctor

Recommended workflow:

1. **Analyze first**: Use `tools-permission-doctor detect-redundant` or `detect-suspicious`
2. **Review findings**: Check the analysis output
3. **Apply fixes**: Use `tools-permission-fix apply-fixes` or specific operations
4. **Verify**: Re-run analysis to confirm fixes

## Default Permissions

`apply-fixes` automatically adds these if missing:

| Permission | Reason |
|------------|--------|
| `Edit(.plan/**)` | Plan file modifications |
| `Write(.plan/**)` | Plan file creation |
| `Read(~/.claude/plugins/cache/**)` | Skills reference files via relative paths |

## Executor Pattern Operations

### generate-wildcards - Generate Permission Wildcards

Generate Skill and SlashCommand wildcards from marketplace inventory.

```bash
# Scan marketplace directory directly
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix generate-wildcards \
  --marketplace-dir marketplace

# Or from pre-existing inventory JSON file
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix generate-wildcards \
  --input inventory.json
```

### ensure-executor - Ensure Executor Permission

Ensure the executor permission exists in settings.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure-executor \
  --target global \
  --dry-run
```

### cleanup-scripts - Remove Redundant Script Permissions

Remove individual script path permissions (redundant with executor pattern).

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix cleanup-scripts \
  --target global \
  --remove-broad-python \
  --dry-run
```

### migrate-executor - Full Migration to Executor Pattern

Complete migration: add executor permission + cleanup redundant permissions.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix migrate-executor \
  --target global \
  --remove-broad-python \
  --dry-run
```

## Executor Permission Pattern

The executor pattern uses a single permission for all marketplace scripts:
- `Bash(python3 .plan/execute-script.py *)`

This replaces individual script path permissions because the executor invokes scripts via subprocess (not checked by the host platform's permission system).

### Migration Path
1. Run `ensure-executor` to add the executor permission
2. Run `cleanup-scripts` to remove redundant individual permissions
3. Or run `migrate-executor` to do both in one step

## Error Handling

All operations return TOON with error details:

```
error: Settings file not found: /path/to/settings.json
success: false
```

## Canonical invocations

The canonical argparse surface for `permission_fix.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### apply-fixes

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-fixes \
  (--settings SETTINGS | --scope {global,project}) [--dry-run]
```

`--settings` and `--scope` are mutually exclusive.

### add

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix add \
  --permission PERMISSION [--target {global,project}]
```

### remove

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove \
  --permission PERMISSION [--target {global,project}]
```

### ensure

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure \
  --permissions PERMISSIONS [--target {global,project}]
```

### consolidate

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix consolidate \
  (--settings SETTINGS | --scope {global,project}) [--dry-run]
```

`--settings` and `--scope` are mutually exclusive.

### ensure-wildcards

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure-wildcards \
  --settings SETTINGS --marketplace-json MARKETPLACE_JSON [--dry-run]
```

### remove-redundant

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove-redundant \
  (--scope both | --global-settings GLOBAL_SETTINGS) [--local-settings LOCAL_SETTINGS] \
  [--move-marketplace] [--no-move-marketplace] [--dry-run]
```

`--scope` and `--global-settings` are mutually exclusive; `--global-settings` requires `--local-settings`.

### apply-project-step-permissions

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-project-step-permissions \
  --marshal MARSHAL --settings SETTINGS [--dry-run]
```

### generate-wildcards

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix generate-wildcards \
  [--marketplace-dir MARKETPLACE_DIR | --input INPUT]
```

`--marketplace-dir` and `--input` are mutually exclusive; `--input` defaults to stdin.

### ensure-executor

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure-executor \
  [--target {global,project}] [--dry-run]
```

### cleanup-scripts

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix cleanup-scripts \
  [--target {global,project}] [--remove-broad-python] [--dry-run]
```

### migrate-executor

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix migrate-executor \
  [--target {global,project}] [--remove-broad-python] [--dry-run]
```
