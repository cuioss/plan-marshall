# First-Run Wizard Flow

Sequential structured setup for new projects. Execute steps in order.

**Bootstrap error recovery** (Steps 1-4): If any bootstrap step fails, report the error and abort the wizard. The user must resolve the issue (e.g., file permissions, missing Python) before re-running `/marshall-steward --wizard`.

---

## Step 1: Gitignore Setup (BOOTSTRAP)

Configure `.gitignore` for `.plan/` directory with tracked file exceptions.

**BOOTSTRAP**: Use DIRECT Python call (no executor yet):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/gitignore_setup.py
```

**Output (TOON)**:
```toon
status	created
gitignore_path	/path/to/.gitignore
entries_added	3
```

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
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/marshall-steward/scripts/determine_mode.py fix-docs
```

Interpret the output:
- `fix_status: ok` → No action needed, continue.
- `fix_status: fixed` → Content was appended deterministically. The `fixes` field lists what was fixed (e.g., `plan_temp:CLAUDE.md,file_ops:CLAUDE.md`).

---

## Step 3: Ensure Executor Permission (BOOTSTRAP)

Add the executor permission to project-local settings so script execution doesn't prompt:

**BOOTSTRAP**: Use DIRECT Python call (no executor yet):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/tools-permission-fix/scripts/permission_fix.py ensure \
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

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/*/skills/tools-script-executor/scripts/generate_executor.py generate
```

**Output (TOON)**:
```toon
status	scripts_discovered	executor_generated	logs_cleaned
success	109	.plan/execute-script.py	0
```

The script auto-detects the plugin cache location and generates `.plan/execute-script.py` with all script mappings embedded.

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

**Note**: marshal.json contains configuration only. Module list comes from derived-data.json (Step 9).

---

## Step 5b: Populate Providers

Scan executor SCRIPTS entries for `*_provider.py` files, load each module's `get_provider_declarations()`, and persist the combined declarations to `marshal.json` under the `providers` key. This must run after the executor is generated (Step 4) and marshal.json is initialized (Step 5), but before CI detection (Step 14) or credential setup (Step 15) which read from the providers list.

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials discover-and-persist
```

**Output (TOON)**:
```toon
status: success
action: discover-and-persist
count: 4
providers:
  - workflow-integration-github
  - workflow-integration-gitlab
  - workflow-integration-sonar
  - workflow-integration-git
```

| Field | Description |
|-------|-------------|
| `count` | Number of provider declarations discovered |
| `providers` | List of `skill_name` values for each discovered provider |

**Why here**: Steps 14 and 15 call `list-providers` and `load_declared_providers()`, both of which read from `marshal.json`. Without this step, the providers list would be empty and CI detection / credential setup would fail.

---

## Step 6: Plan Phase Settings (Optional)

```
AskUserQuestion:
  question: "Configure plan phase settings for this project?"
  header: "Plan Config"
  options:
    - label: "Use defaults (Recommended)"
      description: "branch=feature, compatibility=breaking, commits=per_deliverable"
    - label: "Configure"
      description: "Set branching, compatibility, and commit strategy"
  multiSelect: false
```

If user selects "Use defaults" → Skip to Step 7.

If user selects "Configure", use manage-config to set each plan phase field interactively:

**Branch strategy** (phase-1-init): Ask user for `feature` (recommended) or `direct`, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
```

**Backward compatibility** (phase-2-refine): Ask user for `breaking` (recommended), `deprecation`, or `smart_and_ask`, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
```

**Commit strategy** (phase-5-execute): Ask user for `per_deliverable` (recommended), `per_plan`, or `none`, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_strategy --value {per_deliverable|per_plan|none}
```

---

## Step 7: Quality Pipeline Configuration (Optional)

```
AskUserQuestion:
  question: "Configure verification and finalize pipelines?"
  header: "Pipelines"
  options:
    - label: "Use defaults (Recommended)"
      description: "All generic verify steps + 6 finalize steps with standard iterations"
    - label: "Configure"
      description: "Select individual steps and customize max iterations"
  multiSelect: false
```

If user selects "Use defaults" → Skip to Step 8.

If user selects "Configure", use manage-config to configure pipelines:

**Discover and set verification steps** (phase-5-execute):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```
Present discovered steps as multi-select, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {comma_separated_selected_steps}
```

**Discover and set finalize steps** (phase-6-finalize):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```
Present discovered steps as multi-select, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {comma_separated_selected_steps}
```

**Max iterations**: Ask user for verification iterations (default 5) and finalize iterations (default 3):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-max-iterations --value {5|3|10}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-max-iterations --value {3|1|5}
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

Discover modules directly from filesystem via extension API. This creates `derived-data.json` which is the single source of truth for module information.

**Prerequisites**: Step 8 sets up profile skip lists and mappings in `run-configuration.json`, so discovered profiles are already filtered.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Output (TOON)**:
```toon
status	success
modules_discovered	10
output_file	.plan/project-architecture/derived-data.json
```

This creates `.plan/project-architecture/derived-data.json` with:
- All modules with paths, build_systems, packaging
- Per-module details (packages, dependencies, source/test counts)
- Documentation paths (README locations)
- Build commands (with filtered profiles)

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

**Purpose**: Add resolved build commands to CLAUDE.md so ALL agents (including built-in Explore agents) know how to invoke builds without hard-coding tool-specific commands.

**Prerequisite**: Step 9 completed (architecture API is available).

**Check if already present**: Look for the heading `### Build Commands` in CLAUDE.md. If found, skip this step.

**Check for existing build sections**: Search CLAUDE.md for existing hand-written build command patterns: `mvn `, `mvnw`, `gradle `, `npm run`, `./pw `, `build command`. If any are found, present the user with a choice:

```
AskUserQuestion:
  questions:
    - question: "CLAUDE.md already has build commands. Replace with resolved commands?"
      header: "Build conflict"
      options:
        - label: "Replace existing"
          description: "Remove hand-written build commands and add resolved commands"
        - label: "Keep existing"
          description: "Skip adding resolved commands, keep current CLAUDE.md as-is"
      multiSelect: false
```

If user chooses "Keep existing", skip the rest of this step. If "Replace existing", remove the existing build command section before adding the resolved commands below.

**Resolve available commands** for the default module. Attempt ALL canonical commands — only include those that resolve successfully:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command compile --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command quality-gate --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command module-tests --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command verify --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command integration-tests --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command e2e --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command coverage --name default
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command benchmark --name default
```

For each successful resolution, collect the `executable` value. Track which canonical command names were found on the default module (the "default commands set").

**Collect child-module-only commands**: After resolving against default, iterate over all non-default modules. For each module, resolve the same canonical commands. Collect any commands that resolved successfully on the child module but were NOT found in the default commands set. These are child-module-only commands (e.g., `benchmark`, `integration-tests`, `e2e` that exist only on specific child modules).

```bash
# For each non-default module (from architecture info modules list):
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command {canonical} --name {module_name}
```

**Add to CLAUDE.md** under the heading `### Build Commands` (in a "Development Notes" or equivalent section):

```
- Never hard-code build commands (./pw, mvn, npm, gradle) — use these resolved commands instead:
  - Compile: `{resolved compile executable}`
  - Quality gate: `{resolved quality-gate executable}`
  - Tests: `{resolved module-tests executable}`
  - Full verify: `{resolved verify executable}`
  {- Integration tests: `{resolved integration-tests executable}` — only if resolved on default}
  {- E2E: `{resolved e2e executable}` — only if resolved on default}
  {- Coverage: `{resolved coverage executable}` — only if resolved on default}
  {- Benchmark: `{resolved benchmark executable}` — only if resolved on default}
  {- For each child-module-only command:}
  {- {Canonical} ({module_name}): `{resolved executable}` — only on {module_name}}
  - Always call build commands with a Bash timeout of at least 10 minutes (600000ms)
  - After each build call, analyze the result TOON: check `status` for success/error/timeout, review `errors[N]{file,line,message,category}` for failures, and consult `log_file` for full output if deeper investigation is needed.
```

**Note**: Only include commands that resolved successfully. Different projects have different available commands. Child-module-only commands are listed separately with their module name for clarity.

---

## Step 10: Review Unmatched Build Profiles (Maven Only)

**Condition**: Only if any Maven module was discovered.

Check the `derived-data.json` for profiles with `"canonical": "NO-MATCH-FOUND"` in any `modules.*.metadata.profiles` array.

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

Check the `derived-data.json` for modules where multiple profiles map to the same canonical command. The `commands` section in derived-data is built from `_build_commands()` which detects conflicts — look for a `conflicts` key in any module's commands output.

Alternatively, inspect `modules.*.metadata.profiles` and group by canonical value. If any canonical has more than one profile mapped to it, a conflict exists.

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

Skill domains are determined from the architecture analysis results. The `extensions_used` field in `derived-data.json` (populated during Step 9) contains the bundles whose extensions detected applicable modules in this project.

**Step 11a: Query architecture analysis for applicable domains**

The architecture analysis already determined which extensions are applicable by calling each extension's `discover_modules()` method. Query the results:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived
```

Look for `extensions_used` in the output - this lists bundles that found modules in the project. If `extensions_used` is empty (no extensions detected any modules), skip Steps 11b-11g and continue to Step 12.

**Example output**:
```toon
project:
  name: my-project

modules[3]{name,path,build_systems}:
  ...

extensions_used[2]:
  - pm-dev-java
  - pm-documents
```

**Step 11b: Discover available domains**

Query available domains dynamically from extension.py files:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-available
```

**Output (TOON)**:
```toon
status: success
discovered_domains[N]{key,bundle,name,applicable}:
java	pm-dev-java	Java Development	true
java-cui	pm-dev-java-cui	CUI Java Extensions	true
javascript	pm-dev-frontend	JavaScript Development	false
documentation	pm-documents	Documentation	true
plan-marshall-plugin-dev	pm-plugin-development	Plugin Development	false
requirements	pm-requirements	Requirements Engineering	false
```

Match `extensions_used` bundles from Step 11a to discovered domain keys.

**Step 11c: Configure applicable domains**

Configure all domains whose bundles appear in `extensions_used`:

```
Applicable domains (from architecture analysis):
- java (pm-dev-java)
- documentation (pm-documents)
```

**Step 11d: Apply domain configuration**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains configure --domains "java,java-cui,javascript"
```

**Output (TOON)**:
```toon
status: success
system_domain: configured
domains_configured: 3
domains: java,java-cui,javascript
```

This populates `skill_domains` in marshal.json with:
- `system` domain (always) with task_executors
- Each selected domain with bundle reference and workflow_skill_extensions (outline, triage)
- Domain verification steps from `provides_verify_steps()` auto-persisted to `plan.phase-5-execute.verification_domain_steps`

**Step 11e: Configure Active Profiles**

Control which profiles are emitted during architecture enrichment. By default, extensions use signal detection to decide per-module profile applicability. Setting active_profiles provides a global positive list.

```
AskUserQuestion:
  question: "Configure active profiles for skill domains?"
  header: "Active Profiles"
  options:
    - label: "Default: implementation, module_testing, quality (Recommended)"
      description: "Excludes integration_testing and documentation unless signal-detected"
    - label: "All profiles"
      description: "Include all defined profiles (integration_testing, documentation)"
    - label: "Custom"
      description: "Choose specific profiles to include"
  multiSelect: false
```

If "Default" → apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains active-profiles set --profiles implementation,module_testing,quality
```

If "All profiles" → skip (no active_profiles config = no filtering).

If "Custom" → ask which profiles:
```
AskUserQuestion:
  question: "Select profiles to include:"
  header: "Profiles"
  options:
    - label: "implementation"
    - label: "module_testing"
    - label: "integration_testing"
    - label: "quality"
    - label: "documentation"
  multiSelect: true
```

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains active-profiles set --profiles {comma-separated selection}
```

---

**Step 11f: Configure Task Executors**

Task executors map profile values to workflow skills that execute tasks of that profile.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  configure-task-executors
```

**Output (TOON)**:
```toon
status: success
task_executors_configured: 3
executors:
  implementation: plan-marshall:task-executor
  module_testing: plan-marshall:task-executor
  integration_testing: plan-marshall:task-executor
```

This auto-discovers profiles from configured domains and registers the unified `plan-marshall:task-executor` skill for each profile.

**Extensibility**: New profiles can be added by:
1. Adding profile to `skills_by_profile` in domain `extension.py`
2. The unified `plan-marshall:task-executor` handles profile dispatch internally
3. Re-running `/marshall-steward` to auto-discover and register

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
  - notation: project:verify-workflow
    name: verify-workflow
    description: Verify workflow outputs using hybrid script + LLM assessment
  - notation: project:sync-plugin-cache
    name: sync-plugin-cache
    description: Synchronize all marketplace bundles to the Claude plugin cache
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

## Step 12: Verify Skill Domain Configuration

Skill domains configure which implementation skills are loaded during plan execution:
- **System domain**: Contains task_executors (profile to skill mapping)
- **Technical domains**: Bundle reference and workflow_skill_extensions

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains list
```

**Expected output**: Shows configured domains:
```json
{
  "system": {
    "defaults": ["plan-marshall:dev-general-practices"],
    "optionals": [...],
    "task_executors": {
      "implementation": "plan-marshall:task-executor",
      "module_testing": "plan-marshall:task-executor",
      "integration_testing": "plan-marshall:task-executor"
    }
  },
  "java": {
    "bundle": "pm-dev-java",
    "workflow_skill_extensions": {
      "triage": "pm-dev-java:ext-triage-java"
    }
  }
}
```

**Note**: Task executors map profiles to execution skills. Domain-specific behavior is provided via workflow_skill_extensions (outline, triage). Profiles (core, implementation, module_testing, etc.) are loaded at runtime from `extension.py`.

---

## Step 13: Project Structure Analysis

Generate project structure knowledge for solution outline support.

**Prerequisites**: Step 9 created `.plan/project-architecture/derived-data.json` with all module information.

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

**Output**: `.plan/project-architecture/llm-enriched.json` with rich, meaningful content

### Step 13b: User Refinement (Optional)

Display generated structure and offer refinement:

```yaml
AskUserQuestion:
  question: "Review analyzed structure. Refine any module details?"
  header: "Structure"
  options:
    - label: "Accept analysis"
      description: "Use LLM-generated structure as-is"
    - label: "Refine responsibilities"
      description: "Adjust module descriptions manually"
  multiSelect: false
```

If user chooses "Refine responsibilities", for each module with uncertain analysis:

```yaml
AskUserQuestion:
  question: "Confirm 'oauth-sheriff-core' responsibility:"
  header: "Module"
  options:
    - label: "Validates OAuth access tokens against security policies"
      description: "LLM-suggested based on code analysis"
    - label: "Core business logic"
      description: "Generic description"
  multiSelect: false
```

Update with user input:
```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name oauth-sheriff-core --responsibility "Core OAuth token validation and refresh logic"
```

### Step 13c: Verify Structure

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

Verify that all modules have responsibilities and key packages. Missing fields indicate areas needing attention.

---

## Step 14: Detect CI Provider

Detect CI provider and verify system-authenticated tools using the unified provider model.

**Step 14a: Query system providers**

Read provider declarations from marshal.json (populated by Step 5b) and filter for `auth_type: system` CI providers:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
```

Parse the `providers` array. Filter entries where `auth_type == "system"` and `skill_name` starts with `workflow-integration-gi`. These are the CI provider declarations.

**Step 14b: Detect CI provider from repository**

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health detect
```

This detects the CI provider (github/gitlab) from the git remote URL and CI config files.

**Step 14c: Verify the detected provider's CLI tool**

Match the detected provider to its system provider declaration from Step 14a. Run the provider's `verify_command` to check authentication:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health verify --tool {required_tool}
```

Where `{required_tool}` is `gh` for GitHub or `glab` for GitLab (derived from the system provider's `verify_command`).

Display detection result to user. If tool not authenticated, warn:
- "GitHub detected but 'gh' not authenticated. Run 'gh auth login' for CI operations."
- "GitLab detected but 'glab' not authenticated. Run 'glab auth login' for CI operations."

**Step 14d: Persist CI configuration**

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist
```

**Output**: CI configuration persisted to marshal.json with detected provider and authenticated tools.

---

## Step 15: Credential Setup (Optional)

**Step 15a**: Read available providers from marshal.json (filter out `auth_type: system` providers since those are handled in Step 14):

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
```

Parse the `providers` array from output. If `count == 0`, skip to Step 16.

**Step 15b**: Ask user:

```
AskUserQuestion:
  questions:
    - question: "Configure credentials for external tools?"
      header: "Credentials"
      options:
        - label: "Skip (Recommended)"
          description: "Configure credentials later via /marshall-steward menu"
        - label: "Configure now"
          description: "Set up credentials for SonarCloud or other external tools"
      multiSelect: false
```

If user selects "Skip" → Continue to Step 16.

**Step 15c**: If user selects "Configure now", collect non-secret values step by step.

**IMPORTANT**: Each AskUserQuestion below MUST be followed by the next step. Do NOT abort or skip if a user answer seems unexpected. Always proceed to Step 15e and run the configure command.

1. Credential scope:

```
AskUserQuestion:
  questions:
    - question: "Credential scope?"
      header: "Scope"
      options:
        - label: "Global (Recommended)"
          description: "Shared across all projects using plan-marshall"
        - label: "Project"
          description: "Specific to this project only"
      multiSelect: false
```

Map selection to `--scope global` or `--scope project` for Step 15e.

2. Provider selection (only if multiple providers, otherwise use the single one):

```
AskUserQuestion:
  questions:
    - question: "Which credential provider?"
      header: "Provider"
      options:
        # Dynamic from Step 15a provider list
        - label: "{provider_display_name}"
          description: "{provider_description}"
      multiSelect: false
```

3. URL and auth type (use provider defaults as recommended options):

```
AskUserQuestion:
  questions:
    - question: "Base URL for {display_name}?"
      header: "URL"
      options:
        - label: "{default_url} (Recommended)"
          description: "Default URL for this provider"
      multiSelect: false
    - question: "Authentication type?"
      header: "Auth"
      options:
        - label: "{provider_auth_type} (Recommended)"
          description: "Default auth type for this provider"
        - label: "none"
          description: "No authentication needed"
      multiSelect: false
```

**Step 15d**: Auto-detect extra fields from `list-providers` output.

Check if the selected provider has `extra_fields` in the `list-providers` output. If yes, auto-detect values and confirm with user.

For `workflow-integration-sonar` (has `extra_fields: organization, project_key`):

1. Read `repo_url` from the CI provider entry in marshal.json (persisted during Step 14d):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ci get
```

2. Extract organization from `repo_url` (e.g., `https://github.com/cuioss/plan-marshall` → org=`cuioss`, repo=`plan-marshall`)
3. Derive project key as `{org}_{repo}` (e.g., `cuioss_plan-marshall`)
4. Confirm with user:

```
AskUserQuestion:
  questions:
    - question: "SonarCloud organization?"
      header: "Organization"
      options:
        - label: "{detected_org} (Recommended)"
          description: "Detected from repository URL"
      multiSelect: false
    - question: "SonarCloud project key?"
      header: "Project"
      options:
        - label: "{detected_project_key} (Recommended)"
          description: "Detected as org_repo from repository URL"
      multiSelect: false
```

User can accept recommended values or type custom values via "Other".

**Step 15e**: Run configure via executor. **ALWAYS execute this step** — creates credential file with placeholder secrets.

Build the command from collected values (no secret args — secrets go into the file as placeholders):

```bash
# With extra fields:
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
  --skill {skill} --url {url} --auth-type {auth_type} --scope {scope} \
  --extra organization={org} project_key={project_key}

# Without extra fields:
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
  --skill {skill} --url {url} --auth-type {auth_type} --scope {scope}
```

**CRITICAL**:
- Include `--scope` from Step 15c (global or project).
- Omit `--extra` if the provider has no `extra_fields` in the `list-providers` output.
- The keys used in `--extra` (e.g., `organization`, `project_key`) must match the `key` field from the provider's `extra_fields` array returned by `list-providers`.

**Step 15e2**: If configure returns `needs_editing: true`, tell user to edit the credential file:

1. Tell user: "Open `{path}` and replace the placeholder with your actual token/password."
2. Wait for user to confirm they've edited the file.
3. Run check to verify no placeholders remain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check --skill {skill} --scope {scope}
```

If check returns `incomplete`, tell user which placeholders remain and ask them to edit again.

If configure returns `exists_complete`, ask user whether to reuse the existing credential or reconfigure (remove + configure).

**Step 15f**: Verify connectivity (optional, separate step):

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify --skill {skill}
```

**Step 15g**: Add deny rules via executor:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials ensure-denied --target project
```

**Step 15h**: If the configured skill was `workflow-integration-sonar`, add sonar-roundtrip to finalize steps:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize add-step --step default:sonar-roundtrip --after default:automated-review
```

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

If yes:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-fixes --scope project
```

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
