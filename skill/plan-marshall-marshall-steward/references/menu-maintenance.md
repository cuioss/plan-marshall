# Menu Option: Maintenance

Sub-menu for maintenance operations.

---

## Maintenance Submenu

The Maintenance submenu has 6 options, which exceeds the `AskUserQuestion` 4-option cap. It is presented as a paginated menu following the "More actions..." pattern documented in `plan-marshall/workflow/planning.md` (§ Action: list): each page presents at most 4 options, and every non-final page reserves its 4th slot for a "More..." continuation that triggers the next page's `AskUserQuestion`. The final page exposes the "Back" element returning to the Main Menu without quitting.

**Page 1** — first 3 operations plus the "More..." continuation:

```text
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
    - label: "More..."
      description: "Show remaining maintenance operations"
  multiSelect: false
```

**Page 2** — shown only when the user selects "More..." on Page 1 — the remaining operations plus the "Back" element:

```text
AskUserQuestion:
  question: "Which maintenance operation?"
  header: "Maintenance (continued)"
  options:
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
| "More..." | Present Maintenance Page 2 `AskUserQuestion` | — |
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

**Worktree detection**: Before invoking generate_executor, detect whether the maintenance menu is running inside a git worktree. Two signals:

1. The repo top-level path resolves to something under `.plan/local/worktrees/`:
   ```bash
   git -C . rev-parse --show-toplevel
   ```
   Capture this value as `REPO_ROOT`. If `REPO_ROOT` contains the `/.plan/local/worktrees/` segment, the maintenance run is inside a worktree.

2. As a secondary check, `git -C . rev-parse --is-inside-work-tree` returns `true` when inside any working tree; combined with the path check above it confirms a valid git context.

When running inside a worktree, pass the worktree absolute path via `--marketplace-root <REPO_ROOT>` so the regenerated executor's script mappings resolve against the worktree's `marketplace/bundles/` rather than the main checkout (or the plugin cache). When running against the main checkout, omit the flag.

**Inside a worktree** (path under `.plan/local/worktrees/`):
```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate --marketplace-root "$REPO_ROOT"
```

**Outside a worktree** (main checkout, default path):
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
executor_generated: /path/to/repo/.plan/execute-script.py
logs_cleaned: 0
```

The executor is written directly to `<root>/.plan/execute-script.py`.
Runtime state (plans, archived-plans, run-configuration.json,
lessons-learned, memory, logs) lives at `<root>/.plan/local/` — the same
tracked `.plan/` tree, under a dedicated `local/` subdirectory covered
by the existing `Write(.plan/**)` permission.

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

`discover --force` seeds an `enriched.json` stub for every newly-observed module and preserves every existing module's curated enrichment, so no separate re-initialize step is needed.

**Step 3: LLM Architectural Analysis (automatic)**

Invoke the analysis skill to auto-populate enrichment with semantic descriptions:

```text
Skill: plan-marshall:manage-architecture
```

This regenerates the per-module architecture layout under `.plan/project-architecture/` from current build file definitions: a refreshed `_project.json` (whose `modules` index is the source of truth for which modules exist) plus an `enriched.json` stub per indexed module. Previously-enriched per-module `enriched.json` files are preserved by the `discover --force` seeding pass, which seeds only missing stubs and never blanks existing curated enrichment. Derived module data is not persisted — it is computed on demand by `crawl_module_derived`.

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

deleted[3]{category,count,size_bytes}:
logs	3	512
archived_plans	2	8192
temp	5	1024
```

### Retention Settings

Configurable via marshal.json:

| Setting | Default | Description |
|---------|---------|-------------|
| `logs_days` | 1 | Delete logs older than N days |
| `archived_plans_days` | 5 | Delete archived plans older than N days |
| `lessons_superseded_days` | 0 | Delete superseded lesson stubs older than N days; tombstones at `.tombstones/{id}.json` are preserved |
| `temp_on_maintenance` | true | Clean temp directory on maintenance |
| `plugin_cache_keep_versions` | 5 | Keep the N numerically-newest plugin-cache version dirs per bundle — one arm of the `cache_retention sweep` keep-union (see [`manage-config` data-model.md](../../manage-config/standards/data-model.md)) |
| `plugin_cache_keep_days` | 3 | Keep plugin-cache version dirs younger than D days — the other knob-driven arm of the same keep-union (see [`manage-config` data-model.md](../../manage-config/standards/data-model.md)) |

### Configure Retention

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config system retention set --field logs_days --value 7
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config system retention set --field archived_plans_days --value 14
```

### Cleanup with Custom Retention

```bash
# Retention is configured via `manage-config system retention set` (shown above);
# run_config cleanup honors the configured retention values.
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup
```

### Dry Run (Preview)

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config cleanup --dry-run
```

**NOTE**: The `.plan/temp/` directory is the default temp directory for ALL temporary files. It is covered by the existing `Write(.plan/**)` permission (avoiding permission prompts for `/tmp/`) and cleaned during maintenance.

---

## Operation: Worktree Cleanup

Reconcile git worktrees under `<root>/.plan/local/worktrees/` against active and archived plans. Orphaned worktrees (plans that no longer exist in either `plans/` or `archived-plans/`) are reported; worktrees whose plan is archived (finalized) are offered for removal.

### Step 1: List managed worktrees

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-list
```

Parse the TOON output. Each worktree entry has `plan_id`, `path`, and `branch`.

### Step 2: Cross-reference against plans

For each worktree entry, check whether a plan with that id is still active:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Categorize:

- **Active** (`status: success`, phase not `complete`) → leave alone.
- **Archived** (`status: error, error: plan_not_found`, but a matching directory exists under archived-plans) → candidate for removal.
- **Orphaned** (plan missing from both active and archived dirs) → report but do NOT auto-remove. The user must explicitly confirm removal because the plan may have been manually relocated or the worktree may hold salvageable work.

### Step 3: Confirm and remove archived worktrees

For each archived candidate, ask the user:

```text
AskUserQuestion:
  question: "Remove worktree for archived plan '{plan_id}' at {path}?"
  options:
    - label: "Yes, remove"
    - label: "No, keep"
  multiSelect: false
```

On "Yes, remove":

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove \
  --plan-id {plan_id}
```

If the removal fails with `worktree_remove_failed` (non-clean worktree), surface the error and do NOT retry with `--force`. The user must manually inspect and recover.

### Step 4: Report orphans

Emit a summary of orphaned worktrees without removing them:

```text
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

## Detect/Restore Dropped Finalize Steps (meta-project)

The meta-project's `phase-6-finalize.steps` array carries **hand-maintained** `project:` finalize steps — the `project:finalize-step-{pre-submission-self-review,plugin-doctor,deploy-target,sync-plugin-cache}` skills shipped under `.claude/skills/`. These are NOT preset-driven: the named finalize-step presets (`local` / `standard` / `full`, built by `FinalizeStepPresets` from each step doc's `presets:` frontmatter via `extension_discovery.find_implementors`) are **consumer-scoped** and carry zero `project:` entries, because a preset that seeded a `project:` step would reference a skill a consumer project cannot resolve (project step docs declare `presets: []`). A full reconfigure or preset re-apply therefore must not be used to "restore" the meta-project's project-local steps — doing so would overwrite them with a consumer preset that omits them.

To detect whether any shipped `project:` step has drifted out of the configured array, run the finalize-step check (also surfaced by the healthcheck — see `menu-healthcheck.md` Step 6c):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-missing-finalize-steps
```

- `status: ok` → nothing dropped.
- `status: missing` with `missing_project_finalize_steps` → the listed `project:` steps are shipped under `.claude/skills/finalize-step-*` but absent from `phase-6-finalize.steps`. **Restore** them by re-adding the listed notations to `plan.phase-6-finalize.steps` (hand-edit or `finalize-steps set-steps`), preserving their canonical position in the array; do NOT re-apply a preset.

Consumer projects ship no project-local finalize steps, so `missing_project_finalize_steps` is always absent there.

---

After any operation completes, return to Main Menu.
