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
    - label: "5. Worktree Cleanup"
      description: "Reconcile git worktrees against active/archived plans"
    - label: "6. Back"
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
| "5. Worktree Cleanup" | Execute Operation: Worktree Cleanup (below) | → Return to Main Menu |
| "6. Back" | Do nothing | → Return to Main Menu |

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
status: success
scripts_discovered: 47
executor_generated: /Users/<user>/.plan-marshall/<project>/execute-script.py
shim_generated: /path/to/repo/.plan/execute-script.py
logs_cleaned: 0
```

The real executor now lives in the per-project global directory at
`~/.plan-marshall/<project>/execute-script.py`; the repo-local
`.plan/execute-script.py` is a thin shim that exec's it. Every documented
call site (`python3 .plan/execute-script.py …`) still works unchanged.

**Legacy drift detection**: if the repo-local `.plan/` still contains any
of the runtime entries that moved to the global dir in PR1 (`plans/`,
`archived-plans/`, `lessons-learned/`, `archived-lessons/`, `memory/`,
`logs/`, `temp/`, `run-configuration.json`, `marshall-state.toon`, the
pre-shim `execute-script.py`), `generate` adds two extra fields to the
output and prints a notice on stderr:

```toon
legacy_drift_count: 1
legacy_drift[1]:
  - temp
```

These entries are no longer read and are safe to delete. Cleanup is
manual on purpose — the clean-slate migration intentionally does not
move or delete them automatically.

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

## Operation: Worktree Cleanup

Reconcile git worktrees under `~/.plan-marshall/{project}/worktrees/` against active and archived plans. Orphaned worktrees (plans that no longer exist in either `plans/` or `archived-plans/`) are reported; worktrees whose plan is archived (finalized) are offered for removal.

### Step 1: List managed worktrees

```bash
python3 .plan/execute-script.py plan-marshall:manage-worktree:manage-worktree list
```

Parse the TOON output. Each worktree entry has `plan_id`, `path`, and `branch`.

### Step 2: Cross-reference against plans

For each worktree entry, check whether a plan with that id is still active:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Categorize:

- **Active** (`status: success`, phase not `complete`) → leave alone.
- **Archived** (`status: error, error: plan_not_found`, but a matching directory exists under archived-plans) → candidate for removal.
- **Orphaned** (plan missing from both active and archived dirs) → report but do NOT auto-remove. The user must explicitly confirm removal because the plan may have been manually relocated or the worktree may hold salvageable work.

### Step 3: Confirm and remove archived worktrees

For each archived candidate, ask the user:

```
AskUserQuestion:
  question: "Remove worktree for archived plan '{plan_id}' at {path}?"
  options:
    - label: "Yes, remove"
    - label: "No, keep"
  multiSelect: false
```

On "Yes, remove":

```bash
python3 .plan/execute-script.py plan-marshall:manage-worktree:manage-worktree remove \
  --plan-id {plan_id}
```

If the removal fails with `worktree_remove_failed` (non-clean worktree), surface the error and do NOT retry with `--force`. The user must manually inspect and recover.

### Step 4: Report orphans

Emit a summary of orphaned worktrees without removing them:

```
Orphaned worktrees (plan not found in active or archived dirs):
  - {plan_id} at {path}
  ...

To remove manually after verifying no salvageable work:
  git worktree remove {path}
```

---

## Update Project Documentation (if needed)

Run fix-docs:
```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode fix-docs
```

Interpret the output:
- `fix_status: ok` → No action needed.
- `fix_status: fixed` → Content was appended deterministically. The `fixes` field lists what was fixed (e.g., `plan_temp:CLAUDE.md,file_ops:CLAUDE.md`).

---

After any operation completes, return to Main Menu.
