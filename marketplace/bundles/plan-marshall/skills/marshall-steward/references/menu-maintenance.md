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
      description: "Regenerate executor + architecture + cleanup (recommended)"
    - label: "2. Regenerate Executor"
      description: "Rebuild executor with fresh script mappings"
    - label: "3. Regenerate Architecture"
      description: "Re-detect project structure and extensions"
    - label: "4. Cleanup"
      description: "Clean temp, old logs, archived plans, memory"
    - label: "5. Back"
      description: "Return to main menu"
  multiSelect: false
```

## Routing

| User Selection | Action | After Completion |
|----------------|--------|------------------|
| "1. All" | Execute Operation: All (below) | → Return to Main Menu |
| "2. Regenerate Executor" | Execute Operation: Regenerate Executor (below) | → Return to Main Menu |
| "3. Regenerate Architecture" | Execute Operation: Regenerate Architecture (below) | → Return to Main Menu |
| "4. Cleanup" | Execute Operation: Cleanup (below) | → Return to Main Menu |
| "5. Back" | Do nothing | → Return to Main Menu |

---

## Operation: All (Regenerate + Architecture + Cleanup)

Execute ALL operations in sequence. If any step fails, report the error and abort remaining steps.

1. Execute "Operation: Regenerate Executor" (below)
2. Execute "Operation: Regenerate Architecture" (below)
3. Execute "Operation: Cleanup" (below)

**Output**: Combined summary of all operations (or error with step that failed).

---

## Operation: Regenerate Executor

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
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

## Operation: Regenerate Architecture

Re-detect project structure and extensions, preserving existing enrichment data. Unlike the Configuration → Project Structure path (see `menu-configuration.md` § Project Structure), maintenance mode defaults to keeping enrichment (no user prompt) — it's a quick refresh, not a full reconfiguration.

**Step 1: Check existing enrichment**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --check
```

**Step 2: Run discovery (always `--force` in maintenance)**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Step 3: Re-initialize enrichment (preserving existing by default)**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --force
```

**Step 4: LLM Architectural Analysis (automatic)**

Invoke the analysis skill to auto-populate enrichment with semantic descriptions:

```
Skill: plan-marshall:manage-architecture
```

This regenerates `.plan/project-architecture/derived-data.json` from current build file definitions with updated module data and extensions.

---

## Operation: Cleanup

Clean all directories based on retention settings from marshal.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup
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
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config system retention set --field logs_days --value 7
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config system retention set --field archived_plans_days --value 14
```

### Cleanup with Custom Retention

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup \
    --logs-days 1 --archived-days 5 --memory-days 5
```

### Dry Run (Preview)

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup --dry-run
```

**NOTE**: The `.plan/temp/` directory is the default temp directory for ALL temporary files. It is covered by the existing `Write(.plan/**)` permission (avoiding permission prompts for `/tmp/`) and cleaned during maintenance.

---

## Update Project Documentation (if needed)

Run check-docs:
```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine-mode check-docs
```

Interpret the output:
- `status: ok` → No action needed.
- `status: needs_update` → Apply fixes for each missing marker:
  - `plan_temp` → Append to listed file: `- Use .plan/temp/ for ALL temporary files (covered by Write(.plan/**) permission - avoids permission prompts)`
  - `file_ops` → Append to CLAUDE.md: `- Never use Bash for file operations (find, grep, cat, ls) — use Glob, Read, Grep tools instead`

---

After any operation completes, return to Main Menu.
