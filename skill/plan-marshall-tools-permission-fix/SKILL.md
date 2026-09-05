---
name: plan-marshall-tools-permission-fix
description: Write operations for fixing and managing host-platform permissions - add, remove, consolidate, ensure, apply-fixes, executor migration, wildcard generation.
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Permission Fix Skill

**PURPOSE**: Write operations for fixing and managing host-platform permissions, including marketplace permission synchronization and executor pattern migration.

**COMPLEMENTARY SKILL**: Use `plan-marshall:tools-permission-doctor` for read-only analysis before applying fixes.

## Enforcement

**Execution mode**: Run scripts exactly as documented; use `--dry-run` before applying changes.

**Prohibited actions:**
- Do not modify settings without running analysis first (use `tools-permission-doctor`)
- Do not invent script arguments not listed in the operations table
- Do not skip dry-run verification for bulk operations
- Do not hardcode a platform settings-file path (no `~/.claude/settings.json`, no `--settings <path>` literal). Address the host platform by `--scope` / `--target`; the runtime layer resolves the settings location for the active platform.

**Constraints:**
- Platform-routed permission edits go through `python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime permission {operation} {args}` — the runtime owns settings path-resolution + I/O for the active platform.
- Executor-pattern and marketplace-wildcard operations that have no runtime op run through `python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix {command} {args}`, addressed by `--scope` / `--target` (never a literal settings path).
- Always use `--dry-run` first to preview changes before applying.

## Platform-routed permission edits

The common permission mutations are platform-neutral: they flow through the `platform-runtime` permission ops, which carry the operation's semantic intent and let the runtime resolve + write the active platform's settings. The runtime is the single home for settings path-resolution and load/save — the body never names a settings file.

| Intent | Platform-routed command |
|--------|-------------------------|
| Normalize / dedupe / sort + ensure defaults | `platform_runtime permission fix --scope project --operation normalize [--dry-run]` |
| Add a permission | `platform_runtime permission fix --scope project --operation add --permissions '{"kind":"executor","runtime":"docker"}' [--dry-run]` |
| Remove a permission | `platform_runtime permission fix --scope project --operation remove --permissions '{"kind":"executor","runtime":"docker"}' [--dry-run]` |
| Ensure permissions exist | `platform_runtime permission fix --scope global --operation ensure --permissions '{"kind":"executor","runtime":"git"}' '{"kind":"executor","runtime":"npm"}' [--dry-run]` |
| Consolidate enumerated entries into wildcards | `platform_runtime permission fix --scope project --operation consolidate [--dry-run]` |
| Protect a directory from being read | `platform_runtime permission fix --scope global --operation protect-path --permissions /absolute/path/to/protect [--dry-run]` |
| Set the full permission list | `platform_runtime permission configure --scope project --permissions '{"kind":"path","tool":"Read","path":"**"}' '{"kind":"path","tool":"Edit","path":".plan/**"}'` |
| Ensure marketplace bundle wildcards | `platform_runtime permission ensure-wildcards --scope project --marketplace-dir marketplace [--dry-run]` |
| Ensure `project:{skill}` step permissions | `platform_runtime permission ensure-steps --marshal .plan/marshal.json --scope project [--dry-run]` |

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime permission fix \
  --scope project --operation normalize --dry-run
```

**Output (TOON)**:
```text
status: success
scope: project
fix_operation: normalize
changes_applied: 3
dry_run: true
```

On a platform with no validated permission backend (e.g. OpenCode), each op returns an honest `no-op` with a `reason` and `alternative` — never a fabricated success. The body does not branch on the platform; it routes the intent and the runtime reports what it did.

## Executor-pattern and marketplace-wildcard operations

These operations have no `platform-runtime` permission op; they run on `permission_fix` directly, addressed by `--scope` / `--target` so no literal settings path appears in the call.

⚠️ **The platform-routed ops in the table above honour the active target; the executor-pattern ops below do not route through a `platform-runtime` permission op.** They run on `permission_fix` directly and address a concrete settings file by `--settings` / `--scope`. Settings-path resolution flows through `permission_common`, which now routes via the runtime registry (`_active_runtime` → `_runtime_for_target`): on a platform without a validated permission backend the path resolution declines rather than silently writing a Claude-shaped file.

### apply-project-step-permissions — Add Skill() rules for project: steps

Append `Skill({skill})` allow rules for every `project:{skill}` entry in `marshal.json` (under `phase-5-execute.steps` and `phase-6-finalize.steps`) that lacks a matching rule.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-project-step-permissions \
  --marshal .plan/marshal.json \
  --settings {settings_path} \
  --dry-run
```

`{settings_path}` is a **Claude** settings file — the warning above applies to this operation too, so `--settings` selects which Claude file is written, not which platform. Resolve it from the platform layer rather than hardcoding a `.claude/` path, and prefer `--scope` where the subcommand accepts it. Pair with `tools-permission-doctor:detect-missing-project-step-permissions` — run doctor to detect, then fix to apply.

**Output (TOON)**:
```text
added[1]:
- Skill(finalize-step-plugin-doctor)
summary:
  added_count: 1
  already_present_count: 1
  project_steps_checked: 2
dry_run: true
applied: false
```

### remove-redundant — Remove redundant local-settings permissions

Remove permissions from the project-local settings that are exact duplicates of the global settings or covered by a broader global wildcard, optionally moving marketplace permissions to global.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove-redundant \
  --scope both \
  --dry-run
```

**Options**:
- `--move-marketplace` (default: true): Move marketplace permissions (Skill/SlashCommand) from local to global.
- `--no-move-marketplace`: Skip moving marketplace permissions; only remove duplicates and wildcard-covered entries.
- `--dry-run`: Preview without writing.

**Usage**: Run after `tools-permission-doctor detect-redundant` to clean up permission drift.

### generate-wildcards — Generate permission wildcards

Generate Skill and SlashCommand wildcards from marketplace inventory.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix generate-wildcards \
  --marketplace-dir marketplace
```

### ensure-executor — Ensure executor permission

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure-executor \
  --target global \
  --dry-run
```

### cleanup-scripts — Remove redundant script permissions

Remove individual script path permissions (redundant with the executor pattern).

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix cleanup-scripts \
  --target global \
  --remove-broad-python \
  --dry-run
```

### migrate-executor — Full migration to executor pattern

Add the executor permission and clean up redundant per-script permissions in one step.

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix migrate-executor \
  --target global \
  --remove-broad-python \
  --dry-run
```

## Dry run

All write operations support `--dry-run` to preview changes without modifying any settings.

## Integration with Permission Doctor

Recommended workflow:

1. **Analyze first**: Use `tools-permission-doctor detect-redundant` or `detect-suspicious`.
2. **Review findings**: Check the analysis output.
3. **Apply fixes**: Route common edits through `platform_runtime permission fix`; run executor-pattern operations on `permission_fix`.
4. **Verify**: Re-run analysis to confirm.

## Executor Permission Pattern

The executor pattern uses a single permission for all marketplace scripts:
- `Bash(python3 .plan/execute-script.py *)`

This replaces individual script path permissions because the executor invokes scripts via subprocess (not checked by the host platform's permission system).

### Migration Path
1. Run `ensure-executor` to add the executor permission.
2. Run `cleanup-scripts` to remove redundant individual permissions.
3. Or run `migrate-executor` to do both in one step.

## Error Handling

All operations return TOON with error details:

```text
error: invalid_scope
status: error
```

## Canonical invocations

The canonical argparse surface for `permission_fix.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### apply-fixes

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-fixes \
  (--settings SETTINGS | --scope {global,project}) [--dry-run]
```

`--settings` and `--scope` are mutually exclusive.

Among its fixes, `apply-fixes` ensures a default allow set. It reports which defaults it added as `defaults_added`, a list of **semantic ids** rather than rule text — the rendered grammar stays inside the target. The ids are fixed:

| id | Ensures |
|---|---|
| `plan-dir-edit` | plan-marshall's own `.plan/` directory is writable by every file-editing tool |
| `bundle-cache-read` | the deployed bundle cache is readable, so skills can reach the files they reference by relative path |

Ensuring is two-sided: the target also prunes rules it has **retired** as defaults, reported the same way under `defaults_removed`. A retired rule is removed rather than left alone because an allow rule that matches no tool call is reported by the host as unmatched on every startup. One id is currently retired:

| id | Retires |
|---|---|
| `plan-dir-write` | the separate `.plan/` write rule — file permission checks match `Edit(...)` rules, which already cover every file-editing tool, so it guarded nothing |

`defaults_added_count` and `defaults_removed_count` carry the same lengths as scalars, matching how the neighbouring operations report (`permissions_added`, `rules_total`).

The same two-sided ensure applies to `permission fix --operation normalize` in the platform-routed table above — it is the other surface that ensures this set, and it prunes the retired ids too. It reports the net effect as `changes_applied` rather than as semantic-id lists.

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
