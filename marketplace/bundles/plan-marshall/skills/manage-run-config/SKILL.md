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
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config validate
```

### timeout get / set

Manage adaptive command timeouts.

```bash
# Get current timeout for a command
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command mvn-verify

# Set timeout value
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout set \
  --command mvn-verify --value 300000
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
| `invalid_value` | Value fails type validation (e.g., non-numeric timeout) |
| `not_initialized` | run-config.json missing (run `init` first) |
| `invalid_category` | Warning category not in: transitive_dependency, plugin_compatibility, platform_specific |
| `marshal_not_found` | marshal.json missing (cleanup needs retention settings) |

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `marshall-steward` | init | Initialize run configuration during setup |
| Build skills | timeout set | Update timeouts after command execution |
| Build skills | warning add | Register acceptable warning patterns |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| Build skills | timeout get | Read timeout values for command execution |
| Build skills | warning list | Filter build warnings against accepted patterns |
| `manage-memories` cleanup | cleanup | Remove stale memory files using retention settings |

---

## Related

- `manage-config` — Project-level marshal.json configuration (provides retention settings)
- `manage-lessons` — Complementary global persistence (lessons learned)
- `manage-memories` — Complementary global persistence (session context)
