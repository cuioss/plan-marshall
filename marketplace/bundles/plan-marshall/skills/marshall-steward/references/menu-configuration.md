# Menu Option: Configuration

Sub-menu for build systems and skill domains configuration.

---

## Configuration Submenu

```
AskUserQuestion:
  question: "What would you like to configure?"
  options:
    - label: "Build Systems"
      description: "Detect and configure Maven/Gradle/npm"
      value: "build"
    - label: "Skill Domains"
      description: "Configure implementation skills per domain"
      value: "skill-domains"
    - label: "Modules"
      description: "Define module structure (path, domains, build-systems)"
      value: "modules"
    - label: "Project Structure"
      description: "Manage module metadata, placement rules, conventions"
      value: "structure"
    - label: "Manage Commands"
      description: "Configure build commands per module (test, verify, etc.)"
      value: "commands"
    - label: "Full Reconfigure"
      description: "Run first-run wizard again"
      value: "wizard"
```

**Note**: Menu limited to 4 options per AskUserQuestion. Use nested menus if needed.

## Routing

| Selection | Action |
|-----------|--------|
| build | Execute "Configuration: Build System" below |
| skill-domains | Execute "Configuration: Skill Domains" below |
| modules | Execute "Configuration: Modules" below |
| structure | Execute "Configuration: Project Structure" below |
| commands | Execute "Configuration: Manage Commands" below |
| wizard | Load and execute: `Read references/wizard-flow.md` |

---

## Configuration: Build System

### Detect Build Systems

Build systems are auto-detected during project architecture discovery.

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture discover --force
```

### Auto-Configure Detected Systems

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config build-systems detect
```

This detects build systems from project files and adds them with default commands.

### Build System Mappings

| Detected | Domain Bundle | Build Script |
|----------|---------------|--------------|
| Maven | `pm-dev-java` | `pm-dev-java:plan-marshall-plugin:maven` |
| Gradle | `pm-dev-java` | `pm-dev-java:plan-marshall-plugin:gradle` |
| npm | `pm-dev-frontend` | `pm-dev-frontend:plan-marshall-plugin:npm` |

### View Configured Build Systems

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config build-systems list
```

### Add/Remove Build System

```bash
# Add Gradle with defaults
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config build-systems add --system gradle

# Remove unused build system
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config build-systems remove --system gradle
```

---

## Configuration: Skill Domains

Skill domains configure which implementation skills are loaded for different code types. Domains are auto-discovered from installed bundles.

Uses shared configuration flow (same as wizard Step 4d).

### Reconfigure Skill Domains

**Step 1: Discover available domains**

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains get-available
```

**Output** shows `discovered_domains[]` from bundle manifests.

**Step 2: User domain selection**

Present AskUserQuestion with available domains:

```yaml
AskUserQuestion:
  question: "Select skill domains to enable for this project:"
  header: "Skill Domains"
  multiSelect: true
  options:
    # Build dynamically from discovered_domains
    # Pre-select domains already configured in marshal.json
    - label: "Java Development"
      description: "Java code patterns, CDI, JUnit (pm-dev-java)"
    - label: "CUI Java Development"
      description: "CUI logging, testing, HTTP (pm-dev-java-cui)"
    - label: "JavaScript Development"
      description: "Modern JS, ESLint, Jest (pm-dev-frontend)"
    - label: "Plugin Development"
      description: "Claude Code components (pm-plugin-development)"
    - label: "Requirements Engineering"
      description: "User stories and specs (pm-requirements)"
```

**Step 3: Configure selected domains**

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains configure --domains "java,java-cui,javascript"
```

This configures:
- `system` domain (always) with workflow_skills for 5 phases
- Each selected domain with profile structure from bundle manifest

### List Domains

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config skill-domains list
```

### View Domain Configuration

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config skill-domains get --domain java
```

### Resolve Domain Skills (for task planning)

Aggregate core + profile skills with descriptions for LLM skill selection:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config resolve-domain-skills \
  --domain java --profile implementation
```

### Update Domain Skills

Update skills for a specific profile:

```bash
# Update implementation profile skills
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config skill-domains set \
  --domain java \
  --profile implementation \
  --defaults "pm-dev-java:java-core" \
  --optionals "pm-dev-java:java-cdi,pm-dev-java:java-maintenance"
```

---

## Configuration: Modules

Modules define project structure with domain and build system mappings.

### Detect Modules

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config modules detect
```

### List Modules

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config modules list
```

### Add Module

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config modules add \
  --module my-module \
  --path path/to/module \
  --domains "java,java-testing" \
  --build-systems "maven"
```

---

## Configuration: Project Structure

Manage project structure knowledge including module metadata, placement rules, and conventions.

### Step 1: Select Operation

```yaml
AskUserQuestion:
  question: "What would you like to do with project structure?"
  header: "Operation"
  options:
    - label: "View"
      description: "Display current project structure"
    - label: "Edit Module"
      description: "Update module metadata (layer, responsibility, tips)"
    - label: "Manage Placement"
      description: "Add or update placement rules"
    - label: "Regenerate"
      description: "Re-detect structure from project files"
  multiSelect: false
```

### Operation: View

Display current project architecture:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture info
```

Shows all modules with their purpose, responsibilities, and key packages.

### Operation: View Module Details

**Step 1: List modules**

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules
```

**Step 2: Get module details**

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module --name "{module}"
```

For full details including reasoning:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module --name "{module}" --full
```

### Operation: Enrich Module

Add learned information to a module:

```bash
# Update responsibility
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  enrich module --name "{module}" --responsibility "{description}"

# Add tip
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  enrich tip --module "{module}" --tip "{tip text}"

# Add insight
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  enrich insight --module "{module}" --insight "{insight text}"

# Add best practice
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  enrich best-practice --module "{module}" --practice "{practice text}"
```

### Operation: Regenerate

Regenerate project architecture from build files with optional enrichment.

**Step 1: Check for existing enrichment**

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture init --check
```

If status is `exists`, ask user:

```yaml
AskUserQuestion:
  question: "Existing enrichment data found. How should we proceed?"
  header: "Enrichment"
  options:
    - label: "Keep enrichment"
      description: "Rediscover modules but preserve LLM-added descriptions"
    - label: "Reset enrichment"
      description: "Start fresh with empty enrichment"
  multiSelect: false
```

**Step 2: Run discovery**

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture discover --force
```

**Step 3: Initialize enrichment (if reset or new)**

If user chose "Reset enrichment" or no enrichment existed:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture init --force
```

**Step 4: Prompt for enrichment (if modules found)**

If `modules_discovered > 0`, offer interactive enrichment:

```yaml
AskUserQuestion:
  question: "Found {N} modules. Would you like to add descriptions now?"
  header: "Enrichment"
  options:
    - label: "Yes - Guide me"
      description: "Walk through each module for description"
    - label: "Skip for now"
      description: "Add descriptions later via Edit Module"
  multiSelect: false
```

If user chooses "Yes - Guide me":

1. List modules with `architecture modules`
2. For each module, show current info with `architecture module --name "{module}"`
3. Ask user for responsibility description
4. Save with `architecture enrich module --name "{module}" --responsibility "{user input}"`

This regenerates `.plan/project-architecture/derived-data.json` from current build file definitions.

---

## Configuration: Manage Commands

Manage canonical commands for project modules. Allows adding profile-based commands, removing unused commands, or resetting to defaults.

### Step 1: Select Module

```yaml
AskUserQuestion:
  question: "Which module do you want to configure?"
  header: "Module"
  options:
    - label: "default"
      description: "Root project (N commands)"
    - label: "{module-name}"
      description: "{module-type} (N commands)"
    - label: "All modules"
      description: "Reconfigure all module commands"
  multiSelect: false
```

Build options dynamically from marshal.json module_config.

### Step 2: Select Operation

```yaml
AskUserQuestion:
  question: "What do you want to do with '{module}' commands?"
  header: "Operation"
  options:
    - label: "View"
      description: "Show current command configuration"
    - label: "Add"
      description: "Add new commands from detected profiles"
    - label: "Profile Mappings"
      description: "Map unclassified profiles to commands or skip"
    - label: "Reset"
      description: "Reset to auto-detected defaults"
  multiSelect: false
```

### Operation: View

Show current commands for the module from project architecture:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name "{module}"
```

Display output shows module with commands section.

### Operation: Add

First, detect available profiles not yet configured:

```bash
python3 .plan/execute-script.py pm-dev-java:maven-profile-management:profiles list
```

Then present multi-select for profiles to add:

```yaml
AskUserQuestion:
  question: "Select profiles to add as commands:"
  header: "Add Commands"
  multiSelect: true
  options:
    - label: "integration-tests → integration-tests"
      description: "mvn verify -Pintegration-tests"
    - label: "benchmark → performance"
      description: "mvn verify -Pbenchmark"
```

Profile-to-command mapping is managed via run-config profile-mapping.

### Operation: Profile Mappings

Manage user decisions for profiles that can't be auto-classified. Mappings are stored in `run-configuration.json` and applied during command generation.

**Step 1: View current mappings**

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping list
```

**Output (JSON)**:
```json
{
  "success": true,
  "count": 3,
  "mappings": {
    "jfr": "skip",
    "quick": "skip",
    "benchmark": "performance"
  }
}
```

**Step 2: Check for unmapped profiles**

Check for profiles that need classification:

```bash
python3 .plan/execute-script.py pm-dev-java:maven-profile-management:profiles unmatched
```

If output contains unmatched profiles, present them to user:

```yaml
AskUserQuestion:
  question: "Profile '{profile_id}' can't be auto-classified. What is it?"
  header: "Profile"
  options:
    - label: "Skip (internal/unused)"
      description: "Exclude from command generation"
    - label: "Integration tests"
      description: "Integration or E2E test execution"
    - label: "Coverage"
      description: "Code coverage analysis"
    - label: "Benchmark"
      description: "Benchmark or performance testing"
  multiSelect: false
```

**Step 3: Save mapping**

```bash
# Single mapping
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping set \
  --profile-id "{profile_id}" --canonical "{canonical}"

# Batch mappings
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping batch-set \
  --mappings-json '{"jfr": "skip", "quick": "skip"}'
```

**Valid canonicals**: `integration-tests`, `coverage`, `performance`, `quality-gate`, `skip`

Profile mappings are persisted to `run-configuration.json` and used during command execution.

**Remove a mapping**:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping remove \
  --profile-id "{profile_id}"
```

### Operation: Remove

Present multi-select of current commands:

```yaml
AskUserQuestion:
  question: "Select commands to remove from '{module}':"
  header: "Remove Commands"
  multiSelect: true
  options:
    - label: "coverage"
      description: "mvn verify -Pcoverage"
    - label: "performance"
      description: "mvn verify -Pbenchmark"
```

Remove selected commands by editing marshal.json directly:

```bash
# Read current config, remove selected commands, write back
python3 .plan/execute-script.py plan-marshall:json-file-operations:manage-json-file delete-field \
  .plan/marshal.json --field "module_config.{module}.commands.{canonical}"
```

### Operation: Reset

Reset module to auto-detected defaults:

```yaml
AskUserQuestion:
  question: "Reset '{module}' commands to defaults?"
  header: "Confirm Reset"
  options:
    - label: "Yes - Auto-detect"
      description: "Use smart defaults based on module type and profiles"
    - label: "Yes - Minimal"
      description: "Only required commands (module-tests, quality-gate, verify)"
    - label: "Cancel"
      description: "Keep current configuration"
  multiSelect: false
```

Execute reset by re-running architecture discovery:

```bash
# Re-discover modules and commands from project structure
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture discover --force
```

Commands are automatically derived from detected build files and profiles.

---

## Thin Agent Architecture (5-Phase Model)

The pm-workflow bundle uses thin agents that load skills from system domain:

| Agent | Purpose | Skill Source |
|-------|---------|--------------|
| `plan-init-agent` | Initialize plan, detect domains | System defaults only |
| `solution-outline-agent` | Create deliverables | `resolve-workflow-skill --phase outline` |
| `task-plan-agent` | Create tasks from deliverables | `resolve-workflow-skill --phase plan` |
| `task-execute-agent` | Execute single task | `resolve-workflow-skill --phase execute` + `task.skills` |
| `plan-finalize-agent` | Commit, PR, triage | `resolve-workflow-skill --phase finalize` |

Workflow skills are resolved from `system.workflow_skills`. Domain-specific extensions are loaded via `resolve-workflow-skill-extension --domain {domain} --type {outline|triage}`.

---

After any configuration completes, return to Main Menu.
