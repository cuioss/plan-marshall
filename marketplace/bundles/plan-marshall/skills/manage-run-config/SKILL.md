---
name: manage-run-config
description: Run configuration handling for persistent command configuration storage
user-invocable: false
scope: global
---

# Manage Run Config Skill

Run configuration handling for persistent command configuration storage.

## Enforcement

> **Base contract**: See `plan-marshall:ref-manage-contract` for shared enforcement rules, TOON output format, and error response patterns.

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

See [standards/run-config-format.md](standards/run-config-format.md) for complete schema.

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
| [timeout-handling.md](standards/timeout-handling.md) | Adaptive timeout management | Managing command timeouts |
| [warning-handling.md](standards/warning-handling.md) | Acceptable warning patterns | Filtering build warnings |
| [run-config-format.md](standards/run-config-format.md) | Schema + cleanup operations | Full config schema and directory cleanup |

---

## Quick Start

### Initialize Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config init
```

### Validate Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config validate
```

---

## Integration

### With planning Bundle
- Commands record execution history to run configuration

### With lessons-learned Skill
- Lessons learned are stored separately via `plan-marshall:manage-lessons` skill
- Run configuration tracks execution state only

---

## Error Responses

> See `plan-marshall:ref-manage-contract` for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `key_not_found` | Configuration key doesn't exist |
| `invalid_value` | Value fails type validation (e.g., non-numeric timeout) |
| `not_initialized` | run-config.json missing (run `init` first) |
| `invalid_category` | Warning category not in: transitive_dependency, plugin_compatibility, platform_specific |
| `marshal_not_found` | marshal.json missing (cleanup needs retention settings) |

---

## References

- `standards/run-config-format.md` - Complete schema documentation
- `standards/timeout-handling.md` - Adaptive timeout management
- `standards/warning-handling.md` - Acceptable warning patterns
- `standards/run-config-format.md` also covers cleanup operations (merged from cleanup-operations.md)
