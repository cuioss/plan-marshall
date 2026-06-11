---
name: manage-run-config
description: Run configuration handling for persistent command configuration storage
user-invocable: false
scope: global
---

# Manage Run Config Skill

Run configuration handling for persistent command configuration storage.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not bypass initialization (run-config.json must exist before queries)
- Timeout and warning operations use the noun-verb pattern (e.g., `timeout get`, `warning add`)
- Cleanup operations use `cleanup` and `cleanup-status` subcommands
- Architecture-refresh operations use the noun-verb pattern (`architecture-refresh get-tier-0`, `architecture-refresh set-tier-0`, etc.)
- Build-queue-limit operations use the noun-verb pattern (`build-queue-limit get`, `build-queue-limit set`)

## Run Configuration Structure

```json
{
  "version": 1,
  "commands": {
    "<command-name>": {
      "last_execution": {"date": "...", "status": "SUCCESS|FAILURE"},
      "acceptable_warnings": [],
      "skipped_files": []
    }
  },
  "maven": {
    "acceptable_warnings": {
      "transitive_dependency": [],
      "plugin_compatibility": [],
      "platform_specific": []
    }
  },
  "architecture_refresh": {
    "tier_0": "enabled",
    "tier_1": "prompt"
  },
  "build": {
    "queue": {
      "upper_limit_seconds": 600
    }
  },
  "ci": {
    "authenticated_tools": [],
    "verified_at": null
  }
}
```

See [standards/run-config-standard.md](standards/run-config-standard.md) for complete schema.

---

## Scripts

| Script | Notation |
|--------|----------|
| init | `plan-marshall:manage-run-config:run_config init` |
| validate | `plan-marshall:manage-run-config:run_config validate` |
| timeout get | `plan-marshall:manage-run-config:run_config timeout get` |
| timeout set | `plan-marshall:manage-run-config:run_config timeout set` |
| warning add | `plan-marshall:manage-run-config:run_config warning add` |
| warning list | `plan-marshall:manage-run-config:run_config warning list` |
| warning remove | `plan-marshall:manage-run-config:run_config warning remove` |
| architecture-refresh get-tier-0 | `plan-marshall:manage-run-config:run_config architecture-refresh get-tier-0` |
| architecture-refresh set-tier-0 | `plan-marshall:manage-run-config:run_config architecture-refresh set-tier-0` |
| architecture-refresh get-tier-1 | `plan-marshall:manage-run-config:run_config architecture-refresh get-tier-1` |
| architecture-refresh set-tier-1 | `plan-marshall:manage-run-config:run_config architecture-refresh set-tier-1` |
| build-queue-limit get | `plan-marshall:manage-run-config:run_config build-queue-limit get` |
| build-queue-limit set | `plan-marshall:manage-run-config:run_config build-queue-limit set` |
| cleanup | `plan-marshall:manage-run-config:run_config cleanup` |
| cleanup-status | `plan-marshall:manage-run-config:run_config cleanup-status` |

Script characteristics:
- Uses Python stdlib only (json, argparse, pathlib)
- All commands output TOON to stdout
- Exit code 0 for success, 1 for errors
- Supports `--help` flag

**Calling convention**: All commands use `plan-marshall:manage-run-config:run_config {command}`. The cleanup module is integrated into `run_config` as `cleanup`/`cleanup-status` subcommands.

---

## Standards

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [run-config-standard.md](standards/run-config-standard.md) | Schema, timeouts, warnings, cleanup | Full run configuration reference |

---

## Operations

Script: `plan-marshall:manage-run-config:run_config`

### init

Initialize run-config.json with defaults.

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config init
```

### validate

Validate configuration structure.

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config validate --file run-configuration.json
```

### timeout get / set

Manage adaptive command timeouts.

```bash
# Get current timeout for a command (--default: fallback seconds when unset)
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command mvn-verify --default 120000

# Set timeout value
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout set \
  --command mvn-verify --duration 300000
```

### warning add / list / remove

Manage acceptable build warning patterns.

```bash
# Add an acceptable warning
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning add \
  --category transitive_dependency --pattern "jakarta.json-api"

# List warnings for a category
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning list \
  --category transitive_dependency

# Remove a warning pattern
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning remove \
  --category transitive_dependency --pattern "jakarta.json-api"
```

### architecture-refresh get-tier-0 / set-tier-0 / get-tier-1 / set-tier-1

Manage the `architecture_refresh` tier knobs consumed by the `phase-6-finalize` `architecture-refresh` step. Defaults are returned when the section is absent — `init` does not need to materialise the section. Tier-0 controls the deterministic `architecture discover --force` step (default `enabled`); Tier-1 controls LLM re-enrichment (default `prompt`).

```bash
# Read current tier settings (defaults: tier_0=enabled, tier_1=prompt)
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh get-tier-0
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh get-tier-1

# Disable the deterministic refresh entirely
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh set-tier-0 \
  --value disabled

# Switch LLM re-enrichment to fully automatic (prompt|auto|disabled)
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh set-tier-1 \
  --value auto
```

Allowed values:
- `tier_0`: `enabled`, `disabled`
- `tier_1`: `prompt`, `auto`, `disabled`

Invalid values surface the standard `status: error, error: invalid_value, allowed: [...]` contract.

### build-queue-limit get / set

Manage the adaptive `build.queue.upper_limit_seconds` knob consumed by `build_queue.validate_lock_queue` — the self-healing build-queue stale reaper. The limit is the per-build held-duration ceiling the reaper measures against: an active slot is reaped once its age exceeds `2 ×` this limit. It defaults to and floors at 600 s (10 min), is capped at a 3600 s (1 h) ceiling, and is monotonic-up but clamped — `build_queue` `release` grows it toward the longest observed real build held-duration so a legitimately long build is never falsely reaped, while the ceiling prevents a single anomalously long hold from ratcheting it beyond an hour. The knob lives under the `build.queue` block in the main-anchored `run-configuration.json`, so reads/writes resolve against the main checkout regardless of caller cwd.

```bash
# Read the current limit (default/floor 600 s, always clamped to [600, 3600])
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config build-queue-limit get

# Set the limit explicitly (positive int seconds; clamped to [600, 3600])
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config build-queue-limit set \
  --value 1800
```

A non-positive `--value` surfaces the standard `status: error, error: invalid_value` contract; a value outside `[600, 3600]` is clamped (not rejected) on write.

### cleanup / cleanup-status

Directory cleanup using retention settings from marshal.json.

```bash
# Check what would be cleaned up
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup-status

# Run cleanup
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `key_not_found` | Configuration key doesn't exist |
| `invalid_value` | Value fails type/enum validation (e.g., non-numeric timeout, architecture-refresh enum mismatch) |
| `not_initialized` | run-config.json missing (run `init` first) |
| `invalid_category` | Warning category not in: transitive_dependency, plugin_compatibility, platform_specific |
| `marshal_not_found` | marshal.json missing (cleanup needs retention settings) |

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `marshall-steward` | init | Initialize run configuration during setup |
| `marshall-steward` | architecture-refresh set-tier-0/1 | Persist user-selected tier knobs from setup/maintenance wizard |
| Build skills | timeout set | Update timeouts after command execution |
| Build skills | warning add | Register acceptable warning patterns |
| `manage-locks` `build_queue` release | build-queue-limit set | Persist the clamped adaptive upper limit from the released entry's held duration |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| Build skills | timeout get | Read timeout values for command execution |
| Build skills | warning list | Filter build warnings against accepted patterns |
| `phase-6-finalize` architecture-refresh step | architecture-refresh get-tier-0/1 | Read tier knobs to decide deterministic refresh / LLM re-enrichment behaviour |
| `manage-locks` `build_queue` acquire/release | build-queue-limit get | Read the adaptive upper limit to compute the `2 ×` stale-reclaim threshold |

---

## Canonical invocations

The canonical argparse surface for `run_config.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### init

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config init [--force]
```

### validate

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config validate --file FILE
```

### timeout

`timeout` carries the nested sub-verbs `get` and `set`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command COMMAND --default DEFAULT

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout set \
  --command COMMAND --duration DURATION
```

### warning

`warning` carries the nested sub-verbs `add`, `list`, and `remove`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning add \
  --category {transitive_dependency,plugin_compatibility,platform_specific} --pattern PATTERN \
  [--build-system BUILD_SYSTEM]

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning list \
  [--category {transitive_dependency,plugin_compatibility,platform_specific}] [--build-system BUILD_SYSTEM]

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning remove \
  --category {transitive_dependency,plugin_compatibility,platform_specific} --pattern PATTERN \
  [--build-system BUILD_SYSTEM]
```

### architecture-refresh

`architecture-refresh` carries the nested sub-verbs `get-tier-0`, `set-tier-0`, `get-tier-1`, and `set-tier-1`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh get-tier-0

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh set-tier-0 \
  --value {enabled,disabled}

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh get-tier-1

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config architecture-refresh set-tier-1 \
  --value {prompt,auto,disabled}
```

### build-queue-limit

`build-queue-limit` carries the nested sub-verbs `get` and `set`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config build-queue-limit get

python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config build-queue-limit set \
  --value VALUE
```

### cleanup

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup \
  [--dry-run] [--target {all,temp,logs,archived-plans}]
```

### cleanup-status

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup-status
```

## Related

- `manage-config` — Project-level marshal.json configuration (provides retention settings)
- `manage-lessons` — Complementary global persistence (lessons learned)
