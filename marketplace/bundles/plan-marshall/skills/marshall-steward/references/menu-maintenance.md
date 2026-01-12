# Menu Option: Maintenance

Sub-menu for maintenance operations.

---

## Maintenance Submenu

```
AskUserQuestion:
  question: "Which maintenance operation?"
  header: "Maintenance"
  options:
    - label: "1. All"
      description: "Regenerate executor + cleanup (recommended)"
    - label: "2. Regenerate Executor"
      description: "Rebuild executor with fresh script mappings"
    - label: "3. Cleanup"
      description: "Clean temp, old logs, archived plans, memory"
    - label: "4. Back"
      description: "Return to main menu"
  multiSelect: false
```

## Routing

| User Selection | Action | After Completion |
|----------------|--------|------------------|
| "1. All" | Execute Operation: All (below) | → Return to Main Menu |
| "2. Regenerate Executor" | Execute Operation: Regenerate (below) | → Return to Main Menu |
| "3. Cleanup" | Execute Operation: Cleanup (below) | → Return to Main Menu |
| "4. Back" | Do nothing | → Return to Main Menu |

---

## Operation: All (Regenerate + Cleanup)

Execute BOTH operations in sequence:

1. Execute "Operation: Regenerate Executor" (below)
2. Execute "Operation: Cleanup" (below)

**Output**: Combined summary of both operations.

---

## Operation: Regenerate Executor

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/script-executor/scripts/generate-executor.py generate
```

The script uses subcommands (`generate`, `verify`, `drift`, `paths`, `cleanup`), not positional arguments.

Verify syntax:
```bash
python3 -m py_compile .plan/execute-script.py && echo "Executor syntax OK"
```

**Output (TOON)**:
```toon
status	scripts_discovered	executor_generated	logs_cleaned
success	47	.plan/execute-script.py	0
```

---

## Operation: Cleanup

Clean all directories based on retention settings from marshal.json:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:cleanup run
```

**Output (TOON)**:
```toon
status: success
operation: cleanup
dry_run: false

deleted[4]{category,count,size_bytes}:
logs	3	512
archived_plans	2	8192
memory	10	2048
temp	5	1024
```

### Retention Settings

Configurable via marshal.json:

| Setting | Default | Description |
|---------|---------|-------------|
| `logs_days` | 1 | Delete logs older than N days |
| `archived_plans_days` | 5 | Delete archived plans older than N days |
| `memory_days` | 5 | Delete memory files older than N days |
| `temp_on_maintenance` | true | Clean temp directory on maintenance |

### Configure Retention

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config system retention set --field logs_days --value 7
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config system retention set --field archived_plans_days --value 14
```

### Cleanup with Custom Retention

```bash
python3 .plan/execute-script.py plan-marshall:run-config:cleanup run \
    --logs-days 1 --archived-days 5 --memory-days 5
```

### Dry Run (Preview)

```bash
python3 .plan/execute-script.py plan-marshall:run-config:cleanup run --dry-run
```

**NOTE**: The `.plan/temp/` directory is the default temp directory for ALL temporary files. It is covered by the existing `Write(.plan/**)` permission (avoiding permission prompts for `/tmp/`) and cleaned during maintenance.

---

## Update Project Documentation (if needed)

Check if project docs need `.plan/temp/` documentation:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine-mode check-docs
```

**Output (TOON)**:
```toon
status	ok
files_needing_update	0
```

Or if updates needed:
```toon
status	needs_update
files_needing_update	2
missing	CLAUDE.md,agents.md
```

If `status` is `needs_update`, add to each listed file:
```
- Use `.plan/temp/` for ALL temporary files (covered by `Write(.plan/**)` permission - avoids permission prompts)
```

---

After any operation completes, return to Main Menu.
