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
- `system` domain (always) with workflow_skills for 6 phases and task_executors
- Each selected domain with nested structure from bundle manifest:
  - `workflow_skill_extensions` (outline, triage)
  - `core` (defaults + optionals)
  - Profile blocks (implementation, module_testing, integration_testing, quality)

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

Skill domains configure which implementation skills are loaded during plan execution. The 6-phase model uses:
- **System domain**: Contains workflow_skills (init, outline, plan, execute, finalize) and task_executors
- **Technical domains**: Profile-based skills and workflow_skill_extensions

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config skill-domains list
```

**Expected output**: Shows configured domains:
```json
{
  "system": {
    "workflow_skills": {
      "1-init": "pm-workflow:phase-1-init",
      "2-refine": "pm-workflow:phase-2-refine",
      "3-outline": "pm-workflow:phase-3-outline",
      "4-plan": "pm-workflow:phase-4-plan",
      "5-execute": "pm-workflow:phase-5-execute",
      "6-verify": "pm-workflow:phase-6-verify",
      "7-finalize": "pm-workflow:phase-7-finalize"
    },
    "task_executors": {
      "implementation": "pm-workflow:task-implementation",
      "module_testing": "pm-workflow:task-module_testing",
      "integration_testing": "pm-workflow:task-integration_testing"
    }
  },
  "java": {
    "workflow_skill_extensions": {
      "outline": "pm-dev-java:java-outline-ext",
      "triage": "pm-dev-java:ext-triage-java"
    },
    "core": {...},
    "architecture": {...},
    "implementation": {...},
    "module_testing": {...},
    "integration_testing": {...},
    "quality": {...}
  }
}
```

**Note**: Workflow skills are resolved from system domain. Task executors map profiles to execution skills. Domain-specific behavior is provided via workflow_skill_extensions (outline, triage).

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
