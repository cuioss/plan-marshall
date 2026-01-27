# First-Run Wizard Flow

Sequential structured setup for new projects. Execute steps in order.

---

## Step 1: Gitignore Setup

Configure `.gitignore` for `.plan/` directory with tracked file exceptions.

**BOOTSTRAP**: Use DIRECT Python call (no executor yet):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/skills/marshall-steward/scripts/gitignore-setup.py
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

## Step 1b: Update Project Documentation

Check if project docs need `.plan/temp/` documentation:

**BOOTSTRAP**: Use DIRECT Python call (executor not yet available):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/skills/marshall-steward/scripts/determine-mode.py check-docs
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

If `status` is `needs_update`, add to each listed file's appropriate section:
```
- Use `.plan/temp/` for ALL temporary files (covered by `Write(.plan/**)` permission - avoids permission prompts)
```

---

## Step 1c: Ensure Executor Permission

Add the executor permission to project-local settings so script execution doesn't prompt:

**BOOTSTRAP**: Use DIRECT Python call (no executor yet):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/skills/permission-fix/scripts/permission-fix.py ensure \
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

## Step 2: Generate Executor

**BOOTSTRAP**: Use DIRECT Python call with glob (executor doesn't exist yet):

```bash
python3 ${PLUGIN_ROOT}/plan-marshall/skills/tools-script-executor/scripts/generate-executor.py generate
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

**Ensure executor permission** (prevents permission prompts when using executor):
```bash
python3 ${PLUGIN_ROOT}/plan-marshall/skills/permission-fix/scripts/permission-fix.py ensure \
  --permissions "Bash(python3 .plan/execute-script.py *)" \
  --target project
```

**Output**: "Executor ready with N script mappings"

**NOTE**: From this point on, all script calls use: `python3 .plan/execute-script.py {notation} ...`

---

## Step 3: Apply Extension Defaults

Apply project-specific configuration defaults from domain extensions BEFORE discovery. Each extension's `config_defaults()` callback is invoked to set domain-specific values in `run-configuration.json`.

**Why first**: This sets profile skip lists and mappings that the discovery step uses to filter profiles. Running this first ensures discovered modules contain only relevant profiles.

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

**Contract**: Extensions use write-once semantics - they only set defaults if keys don't already exist in `run-configuration.json`. User-defined values are never overwritten.

**Example defaults set by extensions**:
- Profile skip lists (e.g., `release,sonar,license-cleanup`)
- Profile-to-canonical mappings (e.g., `pre-commit:quality-gate`)
- Build-specific timeout defaults

See `standards/config-callback.md` in `extension-api` skill for the callback contract.

---

## Step 4: Discover Project Architecture (Source of Truth)

Discover modules directly from filesystem via extension API. This creates `derived-data.json` which is the single source of truth for module information.

**Prerequisites**: Step 3 sets up profile skip lists and mappings in `run-configuration.json`, so discovered profiles are already filtered.

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture discover --force
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

## Step 4.5: Review Unmatched Build Profiles (Maven Only)

**Condition**: Only if any Maven module was discovered.

Check the `derived-data.json` for profiles with `"canonical": "NO-MATCH-FOUND"` in any `modules.*.metadata.profiles` array.

**If NO-MATCH-FOUND profiles exist**:

Load skill `pm-dev-java:manage-maven-profiles` and follow its workflow to:
1. Ask user about each unmatched profile (Ignore/Skip/Map)
2. Apply configuration via `plan-marshall-config ext-defaults` commands
3. Re-run discovery to apply changes:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture discover --force
```

**If no Maven modules OR no unmatched profiles** → Skip to Step 5.

---

## Step 5: Initialize Marshal.json

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config init
```

**Output**: "Created .plan/marshal.json with defaults"

**Note**: marshal.json no longer contains module detection data - only configuration. Module list comes from derived-data.json.

---

## Step 5b: Plan Phase Settings

Configure plan phase settings for branching, compatibility, and commit strategy.

```
AskUserQuestion:
  question: "Configure plan phase settings for this project?"
  header: "Plan Config"
  options:
    - label: "Use defaults (Recommended)"
      description: "branch=direct, compatibility=breaking, commits=per_deliverable"
    - label: "Configure"
      description: "Set branching, compatibility, and commit strategy"
  multiSelect: false
```

If user selects "Use defaults" → Skip to Step 5c.

If user selects "Configure":

```
AskUserQuestion:
  question: "Branch strategy for plan execution?"
  header: "Branching"
  options:
    - label: "Direct (Recommended)"
      description: "Work on current branch"
    - label: "Feature branch"
      description: "Create feature branch per plan"
  multiSelect: false
```

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
```

```
AskUserQuestion:
  question: "Backward compatibility approach during plan execution?"
  header: "Compat"
  options:
    - label: "Breaking (Recommended)"
      description: "Clean-slate approach, no deprecation nor transitionary comments"
    - label: "Deprecation"
      description: "Add deprecation markers to old code, provide migration path"
    - label: "Smart and ask"
      description: "Assess impact and ask user when backward compatibility is uncertain"
  multiSelect: false
```

Maps to values: `breaking`, `deprecation`, `smart_and_ask`

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
```

```
AskUserQuestion:
  question: "Commit strategy during plan execution?"
  header: "Commits"
  options:
    - label: "Per deliverable (Recommended)"
      description: "Commit after all tasks for each deliverable complete (impl + tests)"
    - label: "Per plan"
      description: "Single commit of all changes at finalize"
    - label: "None"
      description: "No automatic commits"
  multiSelect: false
```

Maps to values: `per_deliverable`, `per_plan`, `none`

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute set --field commit_strategy --value {per_deliverable|per_plan|none}
```

---

## Step 5c: Quality Pipeline Configuration

Configure verification (phase 6) and finalize (phase 7) pipeline settings.

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

If user selects "Use defaults" → Skip to Step 6.

If user selects "Configure":

### Step 5c-1: Configure Verification Steps

Generic boolean steps:

```
AskUserQuestion:
  questions:
    - question: "Which generic verification steps to include?"
      header: "Verify Steps"
      multiSelect: true
      options:
        - label: "1_quality_check (Recommended)"
          description: "Build quality gate using canonical commands"
        - label: "2_build_verify (Recommended)"
          description: "Build verification using canonical commands"
```

Apply: for each deselected step:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify set-step --step {step_name} --enabled false
```

**Domain verification steps** are auto-populated from extensions during Step 6 (skill domain configuration). Each domain bundle declares its verification steps via `provides_verify_steps()` in `extension.py`.

### Step 5c-2: Select Finalize Steps

```
AskUserQuestion:
  questions:
    - question: "Which finalize steps to include?"
      header: "Finalize Steps"
      multiSelect: true
      options:
        - label: "1_commit_push (Recommended)"
          description: "Commit and push changes"
        - label: "2_create_pr"
          description: "Create pull request"
        - label: "3_automated_review"
          description: "CI automated review"
        - label: "4_sonar_roundtrip"
          description: "Sonar analysis roundtrip"
        - label: "5_knowledge_capture (Recommended)"
          description: "Capture learnings to memory"
        - label: "6_lessons_capture (Recommended)"
          description: "Record lessons learned"
```

Apply: for each deselected step:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-7-finalize set-step --step {step_name} --enabled false
```

### Step 5c-3: Max Iterations

```
AskUserQuestion:
  questions:
    - question: "Max iterations for verification phase (phase 6)?"
      header: "Verify Iters"
      multiSelect: false
      options:
        - label: "5 (Recommended)"
          description: "Standard retry limit for quality checks"
        - label: "3"
          description: "Fewer retries, faster completion"
        - label: "10"
          description: "More retries for complex projects"
    - question: "Max iterations for finalize phase (phase 7)?"
      header: "Finalize Iters"
      multiSelect: false
      options:
        - label: "3 (Recommended)"
          description: "Standard retry limit for commit/PR/CI"
        - label: "1"
          description: "Single attempt, fail fast"
        - label: "5"
          description: "More retries for CI roundtrips"
```

Apply selections:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify set-max-iterations --value {5|3|10}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-7-finalize set-max-iterations --value {3|1|5}
```

---

## Step 6: Skill Domain Configuration

Skill domains are determined from the architecture analysis results. The `extensions_used` field in `derived-data.json` (populated during Step 4) contains the bundles whose extensions detected applicable modules in this project.

**Step 6a: Query architecture analysis for applicable domains**

The architecture analysis already determined which extensions are applicable by calling each extension's `discover_modules()` method. Query the results:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture derived
```

Look for `extensions_used` in the output - this lists bundles that found modules in the project.

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

**Step 6b: Map bundles to domain keys**

Each bundle in `extensions_used` corresponds to a skill domain. Query available domains to get the mapping:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  skill-domains get-available
```

This returns all domains with their bundle mappings. Match `extensions_used` bundles to domain keys:
- `pm-dev-java` → `java`
- `pm-dev-java-cui` → `java-cui`
- `pm-dev-frontend` → `javascript`
- `pm-plugin-development` → `plan-marshall-plugin-dev`
- `pm-documents` → `documentation`
- `pm-requirements` → `requirements`

**Step 6c: Auto-configure applicable domains**

Configure all domains whose bundles appear in `extensions_used`:

```
Applicable domains (from architecture analysis):
- java (pm-dev-java)
- documentation (pm-documents)
```

**Step 6d: Configure selected domains**

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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
- Domain verification steps collected from `provides_verify_steps()` are returned in output for presentation to user

**Step 6e: Configure Task Executors**

Task executors map profile values to workflow skills that execute tasks of that profile.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  configure-task-executors
```

**Output (TOON)**:
```toon
status: success
task_executors_configured: 3
executors:
  implementation: pm-workflow:task-implementation
  module_testing: pm-workflow:task-module_testing
  integration_testing: pm-workflow:task-integration_testing
```

This auto-discovers profiles from configured domains and registers default task executors using convention: profile `X` → skill `pm-workflow:task-X`.

**Extensibility**: New profiles can be added by:
1. Adding profile to `skills_by_profile` in domain `extension.py`
2. Creating corresponding `pm-workflow:task-{profile}` skill
3. Re-running `/marshall-steward` to auto-discover and register

---

## Step 7: Verify Skill Domain Configuration

Skill domains configure which implementation skills are loaded during plan execution:
- **System domain**: Contains task_executors (profile to skill mapping)
- **Technical domains**: Bundle reference and workflow_skill_extensions

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config skill-domains list
```

**Expected output**: Shows configured domains:
```json
{
  "system": {
    "defaults": ["plan-marshall:ref-development-standards"],
    "optionals": [...],
    "task_executors": {
      "implementation": "pm-workflow:task-implementation",
      "module_testing": "pm-workflow:task-module_testing",
      "integration_testing": "pm-workflow:task-integration_testing"
    }
  },
  "java": {
    "bundle": "pm-dev-java",
    "workflow_skill_extensions": {
      "outline": "pm-dev-java:ext-outline-java",
      "triage": "pm-dev-java:ext-triage-java"
    }
  }
}
```

**Note**: Task executors map profiles to execution skills. Domain-specific behavior is provided via workflow_skill_extensions (outline, triage). Profiles (core, implementation, module_testing, etc.) are loaded at runtime from `extension.py`.

---

## Step 8: Project Structure Analysis

Generate project structure knowledge for solution outline support.

**Prerequisites**: Step 4 created `.plan/project-architecture/derived-data.json` with all module information.

### Step 8a: LLM Architectural Analysis

Invoke the analysis skill to read raw data and generate meaningful structure:

```
Skill: plan-marshall:analyze-project-architecture
```

The LLM analysis reads discovered data, samples documentation and source code, then enriches with:
- Semantic module responsibilities (not just names)
- Module purpose classification (library, extension, runtime, etc.)
- 2-4 key packages per module with descriptions
- Proposed skill domains
- Implementation tips and insights

**Output**: `.plan/project-architecture/llm-enriched.json` with rich, meaningful content

### Step 8b: User Refinement (Optional)

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
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  enrich module --name oauth-sheriff-core --responsibility "Core OAuth token validation and refresh logic"
```

### Step 8c: Verify Structure

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture info
```

Verify that all modules have responsibilities and key packages. Missing fields indicate areas needing attention.

---

## Step 9: Detect CI Provider

Detect CI provider and verify tools:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health status
```

Display detection result to user. If tool not authenticated, warn:
- "GitHub detected but 'gh' not authenticated. Run 'gh auth login' for CI operations."
- "GitLab detected but 'glab' not authenticated. Run 'glab auth login' for CI operations."

Persist CI configuration to marshal.json:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist
```

**Output**: CI configuration persisted to marshal.json with detected provider and authenticated tools.

---

## Step 10: Permission Setup

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
python3 .plan/execute-script.py plan-marshall:permission-fix:permission-fix apply-fixes --scope project
```

---

## Step 11: Summary

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
