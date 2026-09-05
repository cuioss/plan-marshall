---
name: tools-permission-doctor
description: Diagnose permission issues across settings files (read-only analysis)
user-invocable: true
mode: script-executor
---

# Permission Doctor Skill

Read-only permission analysis for host-platform settings. Detects redundant permissions, security anti-patterns, and validates permission syntax without making changes.

## Enforcement

**Execution mode**: Run scripts exactly as documented; present analysis results without modifying files.

**Prohibited actions:**
- Do not modify any settings files; this skill is strictly read-only
- Do not invent script arguments not listed in the operations table
- Do not skip anti-pattern detection when analyzing settings

**Constraints:**
- Platform-neutral audits go through `python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime permission analyze --checks {checks} --scope {scope}` — the runtime resolves the active platform's settings path and load. This is the preferred entry point.
- The individual `permission_doctor` detection scripts run through `python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor {command} {args}`, addressed by `--scope` (never a literal settings path).
- Use `tools-permission-fix` for any write operations.
- User-approved permissions must be excluded from suspicious reports.
- Do not hardcode a platform settings-file path (no `~/.claude/settings.json`). Address the host platform by `--scope`; the runtime layer resolves the settings location for the active platform.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `permission_doctor` and `platform_runtime` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## What This Skill Provides

### Permission Validation Standards
- Syntax validation patterns for all permission types
- Path format validation rules
- Duplicate detection algorithms
- Permission categorization logic

### Architecture Patterns
- Global vs Local permission separation
- Universal git access patterns
- Project-specific permission patterns
- Skill and tool permission organization

### Security Anti-Patterns
- Suspicious permission detection patterns
- Critical system directory checks
- Dangerous command patterns
- Overly broad wildcard detection

## When to Activate This Skill

Activate when:
- Validating permission syntax
- Detecting security anti-patterns
- Understanding global/local architecture
- Analyzing permission issues without making changes

## Operations

### Operation: detect-redundant

Detect permissions in local settings that duplicate global settings.

**Script**: `permission_doctor.py detect-redundant`

**Input**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-redundant \
  --global-settings {global_path} \
  --local-settings {local_path}
```

**Output (TOON)**:
```text
redundant[1]{permission,reason,type}:
Bash(git:*)	Exact duplicate	exact_duplicate
marketplace_in_local[1]{permission,reason,type}:
Skill(pm-dev-builder:*)	Should be in global	marketplace_permission
summary:
  redundant_count: 1
  marketplace_in_local_count: 1
```

**Usage**: Call before fixing to identify redundancies between global and local settings.

---

### Operation: detect-suspicious

Detect permissions matching anti-patterns (security risks).

**Script**: `permission_doctor.py detect-suspicious`

**Input**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-suspicious \
  --settings {settings_path} \
  [--approved-file {run_config_path}]
```

**Output (TOON)**:
```text
suspicious[1]{permission,reason,severity}:
Write(/tmp/**)	System temp access	medium
already_approved[1]:
- Bash(sudo:*)
summary:
  total_suspicious: 1
  by_severity:
    high: 0
    medium: 1
    low: 0
```

**Usage**: Call to identify security anti-patterns. User-approved permissions are excluded.

---

### Operation: detect-missing-project-step-permissions

Detect `project:{skill}` step references in `marshal.json` that lack matching `Skill({skill})` allow rules in settings.

**Script**: `permission_doctor.py detect-missing-project-step-permissions`

**Input**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-missing-project-step-permissions \
  --marshal {marshal_path} \
  (--settings {settings_path} | --scope project|global)
```

**Scan scope**: `plan.phase-5-execute.steps` and `plan.phase-6-finalize.steps`. Entries starting with `project:` are enumerated; the substring after `project:` is matched against `permissions.allow` as either exact `Skill({skill})` or covering wildcard `Skill({skill}:*)`.

**Output (TOON)**:
```text
missing[1]{skill,step,phase}:
finalize-step-plugin-doctor	project:finalize-step-plugin-doctor	phase-6-finalize
present[1]{skill,step,phase,covered_by}:
sync-plugin-cache	project:sync-plugin-cache	phase-6-finalize	Skill(sync-plugin-cache)
summary:
  missing_count: 1
  present_count: 1
  project_steps_checked: 2
```

**Usage**: Run during health check and after `set-steps` configuration to surface missing `Skill()` allow rules. Pair with `tools-permission-fix:apply-project-step-permissions` to auto-add missing entries.

---

### Operation: analyze (platform-routed)

High-level, platform-neutral analysis. The runtime resolves the active platform's settings, runs the requested checks, and consolidates results — no settings path is named in the body.

**Input**:
```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime permission analyze \
  --checks redundant,suspicious,missing-steps \
  --scope both \
  [--marshal .plan/marshal.json]
```

(`--marshal` is required only when the `missing-steps` check is included.)

**Output (TOON)**:
```text
status: success
scope: both
checks_run[3]:
- missing-steps
- redundant
- suspicious
total_findings: 5
```

On a platform with no validated permission backend (e.g. OpenCode), the op returns an honest `no-op` with a `reason` and `alternative` instead of a fabricated finding set.

**Usage**: Preferred entry point for permission analysis. Consolidates the detection results across checks for the active platform.

## Scripts

| Script | Subcommand | Purpose |
|--------|------------|---------|
| `permission_doctor.py` | `detect-redundant` | Detects redundant permissions between global/local |
| `permission_doctor.py` | `detect-suspicious` | Detects security anti-patterns in permissions |
| `permission_doctor.py` | `detect-missing-project-step-permissions` | Detects `project:{skill}` steps in `marshal.json` without matching `Skill()` allow rules |
| `permission_common.py` | (library) | Shared utilities for settings loading and path resolution (also used by `tools-permission-fix`) |

## Standards Organization

- `standards/permission-validation-standards.md` - Validation patterns, syntax rules, categorization
- `standards/permission-architecture.md` - Global/Local separation, universal access patterns
- `standards/permission-anti-patterns.md` - Security patterns, suspicious permission detection

## Non-Prompting Requirements

This skill is designed to run without user prompts. Required permissions:

**Script Execution:**
- `Bash(python3 .plan/execute-script.py *)` - Script execution via executor

**Settings access** is performed inside the runtime / script layer, which resolves the active platform's settings location — the skill body reads no settings file directly.

**Ensuring Non-Prompting:**
- All operations are read-only analysis
- No file modifications performed
- Script invocation uses executor pattern

## Canonical invocations

The canonical argparse surface for `permission_doctor.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### detect-redundant

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-redundant \
  (--scope both | --global-settings GLOBAL_SETTINGS) [--local-settings LOCAL_SETTINGS]
```

`--scope` and `--global-settings` are mutually exclusive; `--global-settings` requires `--local-settings`.

### detect-suspicious

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-suspicious \
  (--settings SETTINGS | --scope {global,project}) [--approved-file APPROVED_FILE]
```

`--settings` and `--scope` are mutually exclusive.

### detect-missing-project-step-permissions

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-missing-project-step-permissions \
  --marshal MARSHAL (--settings SETTINGS | --scope {global,project})
```

`--settings` and `--scope` are mutually exclusive.

## Critical Rules

**Read-Only:**
- This skill NEVER modifies files
- All operations are analysis and reporting only
- Use `tools-permission-fix` skill for write operations

**Anti-Pattern Detection:**
- Uses 24 suspicious patterns from `standards/permission-anti-patterns.md`
- Severity scoring: high, medium, low
- User-approved permissions are excluded from reports

Part of: plan-marshall-core bundle
