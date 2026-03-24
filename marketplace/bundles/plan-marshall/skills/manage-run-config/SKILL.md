---
name: manage-run-config
description: Run configuration handling for persistent command configuration storage
user-invocable: false
---

# Run Config Skill

## Enforcement

- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config ...`
- Never read or write run configuration files directly
- All script output follows TOON format contract

---

Run configuration handling for persistent command configuration storage.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse JSON/TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify run-config.json directly; all mutations go through the script API
- Do not invent script arguments not listed in the Scripts table
- Do not bypass initialization (run-config.json must exist before queries)

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config {command} {args}` or `plan-marshall:manage-run-config:cleanup {args}`
- Timeout and warning operations use the noun-verb pattern (e.g., `timeout get`, `warning add`)
- Cleanup uses a separate script notation

## What This Skill Provides

- Read and update run configuration entries
- Track command execution history
- Manage acceptable warnings and skip lists
- Adaptive timeout management
- Validate run configuration format

## When to Activate This Skill

Activate this skill when:
- Recording command execution results
- Managing acceptable warnings lists
- Managing command timeouts
- Validating run configuration structure

---

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

See [references/run-config-format.md](references/run-config-format.md) for complete schema.

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
| cleanup | `plan-marshall:manage-run-config:cleanup` |

Script characteristics:
- Uses Python stdlib only (json, argparse, pathlib)
- Outputs JSON (init/validate) or TOON (timeout/cleanup) to stdout
- Exit code 0 for success, 1 for errors
- Supports `--help` flag

---

## Standards

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [timeout-handling.md](standards/timeout-handling.md) | Adaptive timeout management | Managing command timeouts |
| [warning-handling.md](standards/warning-handling.md) | Acceptable warning patterns | Filtering build warnings |
| [cleanup-operations.md](standards/cleanup-operations.md) | Directory cleanup | Cleaning old files |

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

## Integration Points

### With planning Bundle
- Commands record execution history to run configuration

### With lessons-learned Skill
- Lessons learned are stored separately via `plan-marshall:manage-lessons` skill
- Run configuration tracks execution state only

---

## References

- `references/run-config-format.md` - Complete schema documentation
- `standards/timeout-handling.md` - Adaptive timeout management
- `standards/warning-handling.md` - Acceptable warning patterns
- `standards/cleanup-operations.md` - Directory cleanup operations
