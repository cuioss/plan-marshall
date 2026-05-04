# First-Run Wizard Flow

Sequential structured setup for new projects. Execute steps in order.

**Bootstrap error recovery** (Steps 1-4): If any bootstrap step fails, report the error and abort the wizard. The user must resolve the issue (e.g., file permissions, missing Python) before re-running `/marshall-steward --wizard`.

---

## Step 1: Gitignore Setup (BOOTSTRAP)

Configure `.gitignore` for `.plan/` directory with tracked file exceptions.

**BOOTSTRAP**: Use DIRECT Python call (no executor yet):

```bash
GITIGNORE_SETUP=$(ls ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/gitignore_setup.py | head -n 1)
python3 "$GITIGNORE_SETUP"
```

**Output (TOON)**:
```toon
status	created
gitignore_path	/path/to/.gitignore
entries_added	4
```

The generated block looks like:

```
# Planning system (managed by /marshall-steward)
# Runtime state (plans, run-configuration, lessons-learned, memory, logs — managed by plan-marshall)
.plan/*
!.plan/marshal.json
!.plan/project-architecture/
.claude/worktrees/
```

The `.plan/*` rule already covers `.plan/local/` (where runtime state
lives); the documentation comment above it explains the layout for
human readers.

**Tracked Files**:
- `.plan/marshal.json` - Project configuration
- `.plan/project-architecture/` - Project architecture data

| status | Meaning |
|--------|---------|
| `created` | New .gitignore created with planning entries |
| `updated` | Existing .gitignore updated with planning entries |
| `unchanged` | Planning entries already present |

**NOTE**: `execute-script.py` is NOT tracked because it contains local absolute paths and must be regenerated per-machine.

---

## Step 2: Update Project Documentation (BOOTSTRAP)

**BOOTSTRAP**: Use DIRECT Python call (executor not yet available):

```bash
DETERMINE_MODE=$(ls ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/determine_mode.py | head -n 1)
python3 "$DETERMINE_MODE" fix-docs
```

Interpret the output:
- `fix_status: ok` → No action needed, continue.
- `fix_status: fixed` → Content was appended deterministically. The `fixes` field lists what was fixed (e.g., `plan_temp:CLAUDE.md,file_ops:CLAUDE.md`).

---

## Step 3: Ensure Executor Permission (BOOTSTRAP)

Add the executor permission to project-local settings so script execution doesn't prompt:

**BOOTSTRAP**: Use DIRECT Python call (no executor yet):

```bash
PERMISSION_FIX=$(ls ${PLUGIN_ROOT}/plan-marshall/*/skills/tools-permission-fix/scripts/permission_fix.py | head -n 1)
python3 "$PERMISSION_FIX" ensure \
  --permissions "Bash(python3 .plan/execute-script.py *)" \
  --target project
```

**Output (TOON)**:
```toon
status	added
permission	Bash(python3 .plan/execute-script.py *)
target	project
settings_file	/path/to/.claude/settings.local.json
```

| status | Meaning |
|--------|---------|
| `added` | Permission added to project settings |
| `exists` | Permission already present |

This ensures script execution works without prompting, independent of global settings.

---

## Step 4: Generate Executor (BOOTSTRAP)

**BOOTSTRAP**: Use DIRECT Python call with glob (executor doesn't exist yet):

**Worktree detection**: Before invoking generate_executor, detect whether the wizard is running inside a git worktree (as opposed to the main checkout). Two signals:

1. The repo top-level path resolves to something under `.claude/worktrees/`:
   ```bash
   git -C . rev-parse --show-toplevel
   ```
   Capture this value as `REPO_ROOT`. If `REPO_ROOT` contains the `/.claude/worktrees/` segment, the wizard is running inside a worktree.

2. As a secondary check, `git -C . rev-parse --is-inside-work-tree` returns `true` when inside any working tree (not specific to worktrees, but combined with the path check above it confirms a valid git context).

When the wizard is running inside a worktree, pass the worktree absolute path to `generate_executor.py` via `--marketplace-root <REPO_ROOT>` so the generated executor's script mappings resolve against the worktree's `marketplace/bundles/` rather than the main checkout (or the plugin cache). When running against the main checkout, omit the flag and let the script auto-detect the plugin cache.

**Inside a worktree** (path under `.claude/worktrees/`):
```bash
GENERATE_EXECUTOR=$(ls ${PLUGIN_ROOT}/plan-marshall/*/skills/tools-script-executor/scripts/generate_executor.py | head -n 1)
python3 "$GENERATE_EXECUTOR" generate --marketplace-root "$REPO_ROOT"
```

**Outside a worktree** (main checkout, default path):
```bash
GENERATE_EXECUTOR=$(ls ${PLUGIN_ROOT}/plan-marshall/*/skills/tools-script-executor/scripts/generate_executor.py | head -n 1)
python3 "$GENERATE_EXECUTOR" generate
```

**Output (TOON)**:
```toon
status	scripts_discovered	executor_generated	logs_cleaned
success	109	.plan/execute-script.py	0
```

The script auto-detects the plugin cache location and generates `.plan/execute-script.py` with all script mappings embedded. When `--marketplace-root` is supplied, mappings are anchored to the supplied path instead of the auto-detected cache.

**Verify syntax**:
```bash
python3 -m py_compile .plan/execute-script.py && echo "Executor syntax OK"
```

**Output**: "Executor ready with N script mappings"

**NOTE**: From this point on, all script calls use: `python3 .plan/execute-script.py {notation} ...`

---

## Step 5: Initialize Marshal.json

Initialize marshal.json early to establish the `skill_domains` structure needed by later steps.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config init
```

**If marshal.json already exists**:
- The command will fail with "marshal.json already exists"
- Check if existing config has required structure: `skill-domains list`
- If that fails with "skill_domains not configured", use `--force` to recreate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config init --force
```

**Output**: "Created .plan/marshal.json with defaults"

**Note**: marshal.json contains configuration only. The module list comes from `_project.json["modules"]` (Step 9), which is the source of truth — per-module `derived.json` files are loaded lazily off that index.

---

## Step 5b: Discover and Activate Providers

See [provider-setup.md](provider-setup.md#provider-discovery-and-activation-step-5b) for the full discovery and activation workflow; Step 5b-4 auto-selects the CI provider on high-confidence detection with manual fallback.

---

## Step 6: Plan Phase Settings (Optional)

Ask the user to accept defaults (`branch=feature`, `compatibility=breaking`, `commits=per_deliverable`, `rebase_on_execute_start=true`, `rebase_strategy=merge`) or configure each field interactively. If configuring, apply each choice via manage-config:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_strategy --value {per_deliverable|per_plan|none}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_on_execute_start --value {true|false}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_strategy --value {merge|rebase}
```

The two `rebase_*` fields control the sync-with-main step at the start of phase-5-execute: `rebase_on_execute_start` toggles the step on/off (default `true`), and `rebase_strategy` selects between `merge` (default, PR-safe) and `rebase` (rewrites history, requires force-push when a PR is already open).

---

## Step 7: Quality Pipeline Configuration (Optional)

Ask the user to accept defaults (all generic verify steps + 6 finalize steps, default iterations) or configure individually. If configuring, discover available steps and apply:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {selection}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {selection}
```

Before calling `set-steps` for either phase, run the shared order resolution sub-flow so the command cannot fail with `missing_order` or `order_collision`. See [menu-configuration.md § Order resolution sub-flow](menu-configuration.md#order-resolution-sub-flow) for the full `AskUserQuestion` + `set-step-order-override` prompts.

For max iterations (verification default 5, finalize default 3):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-max-iterations --value {n}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-max-iterations --value {n}
```

---

## Step 7c: Review Gates (Optional)

Configure whether phase transitions pause for user review or auto-continue. Default: all transitions pause.

Ask user which transitions should auto-continue (multi-select):
- "Plan without asking" → outline (phase 3) to planning (phase 4)
- "Execute without asking" → planning (phase 4) to execution (phase 5)
- "Finalize without asking" → execution (phase 5) to finalize (phase 6)

Apply each selection via manage-config:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline set --field plan_without_asking --value {true|false}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan set --field execute_without_asking --value {true|false}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field finalize_without_asking --value {true|false}
```

---

## Step 8: Apply Extension Defaults

Apply project-specific configuration defaults from domain extensions BEFORE discovery. Each extension's `config_defaults()` callback is invoked to set domain-specific values in `marshal.json`.

**Why before discovery**: This sets profile skip lists and mappings that the discovery step uses to filter profiles. Running this first ensures discovered modules contain only relevant profiles.

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery apply-config-defaults
```

**Output (TOON)**:
```toon
status	success
extensions_called	3
extensions_skipped	2
errors_count	0
```

| Field | Description |
|-------|-------------|
| `extensions_called` | Extensions that provided config_defaults() |
| `extensions_skipped` | Extensions without config_defaults() implementation |
| `errors_count` | Failures during callback execution |

**Contract**: Extensions use write-once semantics - they only set defaults if keys don't already exist in `marshal.json`. User-defined values are never overwritten.

**Example defaults set by extensions**:
- Profile skip lists (e.g., `release,sonar,license-cleanup`)
- Profile-to-canonical mappings (e.g., `pre-commit:quality-gate`)
- Build-specific timeout defaults

See `standards/extension-contract.md` in `extension-api` skill for the callback contract.

---

## Step 9: Discover Project Architecture (Source of Truth)

Discover modules directly from filesystem via extension API. This writes the per-module architecture layout under `.plan/project-architecture/`: a top-level `_project.json` whose `modules` index is the single source of truth for "which modules exist", plus one subdirectory per module containing a deterministic `derived.json`. Per-module directories present on disk but absent from `_project.json["modules"]` MUST be ignored — the index is authoritative, not the filesystem.

**Prerequisites**: Step 8 sets up profile skip lists and mappings in `run-configuration.json`, so discovered profiles are already filtered.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Output (TOON)**:
```toon
status	success
modules_discovered	10
output_dir	.plan/project-architecture/
```

This produces:
- `.plan/project-architecture/_project.json` — project metadata (`name`, `description`, `extensions_used`) and the module index.
- `.plan/project-architecture/{module}/derived.json` — per-module discovery output (paths, build systems, packaging, packages, dependencies, source/test counts, documentation paths, build commands with filtered profiles).

**Verification** - Display discovered modules:
```
Modules discovered: 10
  - bom (pom, maven)
  - oauth-sheriff-core (jar, maven)
  - oauth-sheriff-quarkus-parent (pom, maven)
  - oauth-sheriff-quarkus (jar, maven) [parent: oauth-sheriff-quarkus-parent]
  - oauth-sheriff-quarkus-deployment (jar, maven+npm) [parent: oauth-sheriff-quarkus-parent]
  ...
```

**Hybrid modules** are detected automatically when both pom.xml and package.json exist.

---

## Step 9b: Document Build Commands in CLAUDE.md

**Purpose**: Add resolved build commands to CLAUDE.md so agents invoke builds via canonical names, not hard-coded tool commands.

**Prerequisite**: Step 9 completed (architecture API is available).

**Skip condition**: If CLAUDE.md already has a `### Build Commands` heading, skip this step.

**Conflict handling**: If CLAUDE.md contains hand-written build patterns (`mvn`, `mvnw`, `gradle`, `npm run`, `./pw`, "build command"), ask the user to Replace existing or Keep existing. On Keep, skip the rest of this step.

**Resolve available commands** for the default module across all canonical commands (`compile`, `quality-gate`, `module-tests`, `verify`, `integration-tests`, `e2e`, `coverage`, `benchmark`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command {canonical} --module default
```

Collect the `executable` value from each successful resolution. Track which canonical command names resolved on the default module (the "default commands set").

**Collect child-module-only commands**: For each non-default module, resolve the same canonical commands and keep any that resolved on the child module but NOT on default. These become child-module-only entries (e.g., `benchmark` or `e2e` exclusive to specific modules).

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command {canonical} --module {module_name}
```

**Add to CLAUDE.md** under the heading `### Build Commands` (in a "Development Notes" section) with bullets: a "Never hard-code" preamble, one bullet per resolved canonical command (`Compile`, `Quality gate`, `Tests`, `Full verify`, plus `Integration tests`, `E2E`, `Coverage`, `Benchmark` only when resolved on default), one bullet per child-module-only command in the form `{Canonical} ({module_name}): {executable} — only on {module_name}`, a reminder to use a 10-minute Bash timeout (600000ms), and a reminder to analyze each build's TOON result (`status`, `errors[N]{file,line,message,category}`, `log_file`).

Only include commands that resolved successfully.

---

## Step 10: Review Unmatched Build Profiles (Maven Only)

**Condition**: Only if any Maven module was discovered.

Iterate the modules listed in `_project.json["modules"]` and load each module's `derived.json` to look for profiles with `"canonical": "NO-MATCH-FOUND"` in `metadata.profiles`.

**If NO-MATCH-FOUND profiles exist**:

Load skill `pm-dev-java:manage-maven-profiles` and follow its workflow to:
1. Ask user about each unmatched profile (Ignore/Skip/Map)
2. Apply configuration via `manage-config ext-defaults` commands
3. Re-run discovery to apply changes:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**If no Maven modules OR no unmatched profiles** → Continue to Step 10b.

### Step 10b: Resolve Profile Conflicts (Maven Only)

**Condition**: Only if any Maven module was discovered.

Iterate the modules listed in `_project.json["modules"]` and inspect each module's `derived.json` for cases where multiple profiles map to the same canonical command. The `commands` section in each `derived.json` is built from `_build_commands()` which detects conflicts — look for a `conflicts` key in any module's commands output.

Alternatively, inspect each module's `metadata.profiles` and group by canonical value. If any canonical has more than one profile mapped to it, a conflict exists.

**If conflicts exist** (e.g., both `pre-commit` and `sonar` map to `quality-gate`):

Ask the user which profile to use for each conflicting canonical command:

```
AskUserQuestion:
  questions:
    - question: "Multiple profiles map to '{canonical}'. Which should be used?"
      header: "Profile conflict"
      options:
        # For each conflicting profile (dynamic):
        - label: "{profile_id}"
          description: "Uses: mvn verify -P{profile_id}"
      multiSelect: false
```

After user selects, update the module's commands to use the chosen profile:
1. Store the user's choice via `manage-config ext-defaults set` with key `build.maven.profiles.map.canonical` and value `{profile_id}:{canonical}` (append to existing comma-separated mappings)
2. Re-run discovery to apply the explicit mapping:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**If no conflicts** → Skip to Step 11.

---

## Step 11: Skill Domain Configuration

Skill domains are determined from the architecture analysis results. The `extensions_used` field in `_project.json` (populated during Step 9) contains the bundles whose extensions detected applicable modules in this project.

**Step 11a: Query architecture analysis for applicable domains**

The architecture analysis already determined which extensions are applicable by calling each extension's `discover_modules()` method. Query the results:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived
```

Look for `extensions_used` in the output - this lists bundles that found modules in the project. If `extensions_used` is empty (no extensions detected any modules), skip Steps 11b-11g and continue to Step 12.

**Step 11b: Discover available domains**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-available
```

The output lists `discovered_domains[N]{key,bundle,name,applicable}`. Match `extensions_used` bundles from Step 11a to discovered domain keys.

**Step 11c-11d: Apply domain configuration**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains configure --domains "{comma,separated,keys}"
```

This populates `skill_domains` in marshal.json with: the `system` domain (always) with execute_task_skills, each selected domain with bundle reference and workflow_skill_extensions (outline, triage), and domain verification steps from `provides_verify_steps()` auto-persisted to `plan.phase-5-execute.verification_domain_steps`.

**Step 11e: Configure Active Profiles**

Control which profiles are emitted during architecture enrichment. Ask the user to choose Default (recommended: `implementation,module_testing,quality`), All profiles (no filtering), or Custom (multiSelect from `implementation,module_testing,integration_testing,quality,documentation`). Apply the chosen list (skip apply entirely for "All profiles"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains active-profiles set --profiles {comma-separated selection}
```

---

**Step 11f: Configure Execute-Task Skills**

Map profile values to workflow skills that execute tasks of that profile:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  configure-execute-task-skills
```

This auto-discovers profiles from configured domains and registers the unified `plan-marshall:execute-task` skill for each profile. New profiles are added by extending `skills_by_profile` in the domain `extension.py` and re-running `/marshall-steward`.

---

**Step 11g: Discover and Attach Project-Level Skills**

Scan `.claude/skills/` for project-level skills and let the user assign them to configured domains.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains discover-project
```

**Output (TOON)**:
```toon
status: success
count: 2
skills:
  - notation: project:sync-plugin-cache
    name: sync-plugin-cache
    description: Synchronize all marketplace bundles to the Claude plugin cache
  - notation: project:finalize-step-plugin-doctor
    name: finalize-step-plugin-doctor
    description: Finalize-phase wrapper that runs plugin-doctor against skills touched by the plan
```

If skills are found (`count > 0`), present them to the user with `AskUserQuestion`:
- List each discovered skill with its description
- For each skill, let the user select which configured domain to attach it to:
  - "system" = cross-domain (always loaded)
  - A specific domain (e.g., "documentation") = loaded during that domain's tasks
  - "skip" = do not attach

For each assignment, call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains attach-project --domain {domain} --skills {comma-separated project:skill notations}
```

If no project-level skills are found (`count == 0`), skip this step silently.

---

**Step 11h: Bulk Populate skills_by_profile**

Populate `skills_by_profile` for every module × every applicable extension so that downstream `phase-4-plan` tasks always receive a non-empty skill list. This `enrich-all` invocation iterates across all discovered modules and all configured domain extensions in a single call, eliminating the need for per-module enrichment loops.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture enrich all
```

**Output (TOON)**:

| Field | Description |
|-------|-------------|
| `modules_enriched` | Count of modules that received at least one `skills_by_profile` update |
| `pairs_applied` | Number of (module, domain) pairs where skills were successfully written |
| `pairs_skipped` | Number of (module, domain) pairs that were skipped (not applicable or already populated with identical content) |
| `errors` | Array of per-pair error entries; empty on a fully clean run |

**Handling errors**: If `errors` is non-empty, log the error list for review. The run is still considered successful because each (module, domain) pair is isolated — a failure on one pair does not block others from being populated. Do not abort the wizard.

**Idempotency**: The command is idempotent — re-running `/marshall-steward` is safe and produces `pairs_applied=0` on subsequent runs when nothing has changed, so the wizard can be executed repeatedly without side effects.

---

## Step 11i: Register Recipes (Discovery Only)

Recipes are deterministic plan templates that bypass the iterative refine → outline → Q-Gate pipeline. The wizard does not "configure" recipes — they self-register at runtime via three sources:

1. **Built-in** — `provides_recipes()` in `plan-marshall-plugin/extension.py` (always available).
2. **Project-local** — `recipe-*` skills under `.claude/skills/` (zero-config; just drop the skill).
3. **Extension-provided** — `provides_recipes()` callbacks from any active extension's domain bundle.

Enumerate the recipes currently visible to the steward to confirm the project picked up the expected ones:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes
```

**Recipe-registration flow** (showing how a new recipe surfaces):

```
       ┌──────────────────────────────────────────────┐
       │ Source 1: extension.provides_recipes()       │
       │   plan-marshall-plugin → refactor-to-...     │
       │   plan-marshall-plugin → lesson_cleanup      │
       └────────────────────┬─────────────────────────┘
                            │
       ┌──────────────────────────────────────────────┐
       │ Source 2: .claude/skills/recipe-*/SKILL.md   │
       │   (project-local recipes, no plugin.json)    │
       └────────────────────┬─────────────────────────┘
                            │
       ┌──────────────────────────────────────────────┐
       │ Source 3: extension.provides_recipes() from  │
       │   any active extension bundle                 │
       └────────────────────┬─────────────────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │ _discover_all_recipes  │
                │ (manage-config helper) │
                └───────────┬────────────┘
                            │ output consumed by:
                            ▼
       ┌──────────────────────────────────────────────┐
       │ • manage-config list-recipes                 │
       │ • manage-config resolve-recipe --recipe KEY  │
       │ • marshall-steward Configuration → Recipes   │
       │ • phase-1-init --recipe KEY (explicit)       │
       │ • phase-1-init Step 5c (auto-suggest)        │
       └──────────────────────────────────────────────┘
```

**Two built-in recipes ship with plan-marshall**:

- `refactor-to-profile-standards` (codebase_wide, tech_debt) — Iterates packages across modules.
- `lesson_cleanup` (single_lesson, change_type derived from lesson kind) — Auto-suggested by `phase-1-init` Step 5c when `source == lesson` and the lesson body is doc-shaped.

**No wizard configuration is required for built-in recipes** — they are always available once the plugin is installed and the executor is generated. The wizard's only role is to surface them via `references/menu-recipes.md` so users know they exist. Project-local recipes (Source 2) require dropping a `recipe-*` skill under `.claude/skills/` and re-running `/marshall-steward` to regenerate the executor with the new notation.

See [`references/menu-recipes.md`](menu-recipes.md) for the full catalog and the procedure to add a new built-in recipe.

---

## Step 12: Verify Skill Domain Configuration

Skill domains configure which implementation skills are loaded during plan execution. The `system` domain holds execute_task_skills (profile -> skill); technical domains hold bundle reference and workflow_skill_extensions (outline, triage).

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains list
```

Confirm that `system` has `execute_task_skills` populated and each technical domain has a `bundle` reference. Profiles (core, implementation, module_testing, etc.) are loaded at runtime from `extension.py`.

---

## Step 13: Project Structure Analysis

Generate project structure knowledge for solution outline support.

**Prerequisites**: Step 9 created the per-module architecture layout (`_project.json` plus per-module `derived.json` files) under `.plan/project-architecture/`.

### Step 13a: LLM Architectural Analysis

Invoke the analysis skill to read raw data and generate meaningful structure:

```
Skill: plan-marshall:manage-architecture
```

The LLM analysis reads discovered data, samples documentation and source code, then enriches with:
- Semantic module responsibilities (not just names)
- Module purpose classification (library, extension, runtime, etc.)
- 2-4 key packages per module with descriptions
- Proposed skill domains
- Implementation tips and insights

**Output**: One `.plan/project-architecture/{module}/enriched.json` per module, each holding the LLM-augmented fields for that module. The top-level `_project.json` may also receive enriched project-level metadata (e.g., `description`, `description_reasoning`).

### Step 13b: User Refinement (Optional)

Display the generated structure and ask whether to accept as-is or refine module responsibilities. On refine, iterate modules with uncertain analysis, confirm each responsibility with the user, and persist the chosen text:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name {module_name} --responsibility "{text}"
```

### Step 13c: Verify Structure

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

Verify that all modules have responsibilities and key packages. Missing fields indicate areas needing attention.

### Step 13d: Architecture Refresh Tier Knobs

Configure how the `phase-6-finalize` `architecture-refresh` step behaves on every plan finalize. Both knobs persist to `run-config.json` via the `plan-marshall:manage-run-config` `architecture-refresh` subcommand group documented in `manage-run-config/SKILL.md`. Defaults match the user-locked decision from Phase D (`tier_0=enabled`, `tier_1=prompt`).

This step is also the entry point reached when a returning user selects **Configuration → Full Reconfigure** from the maintenance menu, so the same prompts cover both first-run setup and ongoing maintenance.

**Question 1 — Tier 0 (deterministic refresh)**:

```
AskUserQuestion:
  question: "Refresh architecture data on every plan finalize?"
  header: "Architecture Refresh — Tier 0"
  options:
    - label: "Enabled (recommended)"
      description: "Run `architecture discover --force` and commit if any module diff is detected"
    - label: "Disabled"
      description: "Skip the deterministic refresh entirely"
  multiSelect: false
```

Map the selection to a `tier_0` value (`Enabled (recommended)` → `enabled`; `Disabled` → `disabled`) and persist:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  architecture-refresh set-tier-0 --value {enabled|disabled}
```

**Question 2 — Tier 1 (LLM re-enrichment)**:

```
AskUserQuestion:
  question: "When affected modules need LLM re-enrichment, what should the finalize step do?"
  header: "Architecture Refresh — Tier 1"
  options:
    - label: "Prompt me each time (recommended)"
      description: "AskUserQuestion fires when modules need re-enrichment so you can decide per-plan"
    - label: "Re-enrich automatically"
      description: "Run enrich Steps 5–8 per affected module, commit chore(architecture), push"
    - label: "Skip — only commit deterministic refresh"
      description: "Always skip Tier 1 and append a 'Skip — note in PR' line for affected modules"
  multiSelect: false
```

Map the selection to a `tier_1` value (`Prompt me each time (recommended)` → `prompt`; `Re-enrich automatically` → `auto`; `Skip — only commit deterministic refresh` → `disabled`) and persist:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  architecture-refresh set-tier-1 --value {prompt|auto|disabled}
```

**Note**: `change_type ∈ {bug_fix, verification}` skips Tier 1 regardless of this setting (see `phase-6-finalize/standards/architecture-refresh.md`). Both knobs are read at finalize time via the `architecture-refresh get-tier-0` / `get-tier-1` subcommands; neither is materialised in `run-config.json` until the user explicitly sets a value, so default behaviour is preserved on fresh projects.

---

## Step 14: Detect CI Provider

See [provider-setup.md](provider-setup.md#ci-provider-detection-step-14) for the full CI detection, verification, and persistence workflow.

---

## Step 15: Credential Setup (Optional)

See [provider-setup.md](provider-setup.md#credential-setup-step-15-optional) for the full credential configuration workflow (scope selection, provider selection, URL/auth setup, extra fields, verification, and deny rules).

---

## Step 16: Permission Setup (Optional)

```
AskUserQuestion:
  question: "Configure permissions now?"
  options:
    - label: "Yes"
      description: "Set up global and project permissions"
      value: "yes"
    - label: "Later"
      description: "Skip permission setup for now"
      value: "no"
```

If yes, run these two commands sequentially — the first applies project-scope fixes; the second installs a narrow global allow rule for the `TERM_PROGRAM` detection pattern used by workflow auto-open / IDE hand-off steps (eliminates the `simple_expansion` permission prompt):

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-fixes --scope project
```

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure --permissions 'Bash(echo "TERM_PROGRAM=$TERM_PROGRAM")' --target global
```

The `ensure` subcommand is idempotent — re-running the wizard does not duplicate the entry.

---

## Step 17: Summary

Output final summary:

```toon
status: success
operation: wizard_complete

gitignore: configured
executor:
  path: .plan/execute-script.py
  script_count: 45
marshal:
  path: .plan/marshal.json
project_architecture:
  path: .plan/project-architecture/
  modules_count: 3
skill_domains:
  - documentation
  - plan-marshall-plugin-dev

next_steps:
  - Run /plan-marshall to create a new plan
  - Use /marshall-steward for maintenance tasks
```

After summary output, wizard is complete. Exit skill execution.
