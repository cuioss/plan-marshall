---
name: tools-permission-fix
description: Write operations for fixing and managing Claude Code permissions - add, remove, consolidate, ensure, apply-fixes, executor migration, wildcard generation.
user-invocable: true
---

# Permission Fix Skill

**PURPOSE**: Write operations for fixing and managing Claude Code permissions, including marketplace permission synchronization and executor pattern migration.

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
| permission_fix | `plan-marshall:tools-permission-fix:permission_fix` | Write operations for permissions |

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

This replaces individual script path permissions because the executor invokes scripts via subprocess (not checked by Claude Code permissions).

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
