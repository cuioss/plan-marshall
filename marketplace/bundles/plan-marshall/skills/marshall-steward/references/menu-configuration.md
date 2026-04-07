# Menu Option: Configuration

Sub-menu for skill domains and project structure configuration.

## Table of Contents

- [Configuration Submenu](#configuration-submenu)
- [Routing](#routing)
- [Configuration: Plan Phase Settings](#configuration-plan-phase-settings)
- [Configuration: Review Gates](#configuration-review-gates)
- [Configuration: Quality Pipelines](#configuration-quality-pipelines)
- [Configuration: Skill Domains](#configuration-skill-domains)
- [Configuration: Project Structure](#configuration-project-structure)

---

## Configuration Submenu

```
AskUserQuestion:
  question: "What would you like to configure?"
  options:
    - label: "Skill Domains"
      description: "Configure implementation skills per domain"
      value: "skill-domains"
    - label: "Plan Phase Settings"
      description: "Branching, compatibility, commit strategy"
      value: "plan-phases"
    - label: "Project Structure"
      description: "View, regenerate, and enrich architecture data"
      value: "structure"
    - label: "Quality Pipelines"
      description: "Verification and finalize step pipelines"
      value: "quality-pipelines"
    - label: "Review Gates"
      description: "Auto-continue between phases or pause for review"
      value: "review-gates"
    - label: "Credentials & Secrets"
      description: "Manage external tool credentials"
      value: "credentials"
    - label: "Full Reconfigure"
      description: "Re-run setup wizard from Step 5 onwards (skips bootstrap steps 1-4)"
      value: "wizard"
```

## Routing

| Selection | Action |
|-----------|--------|
| skill-domains | Execute "Configuration: Skill Domains" below |
| plan-phases | Execute "Configuration: Plan Phase Settings" below |
| quality-pipelines | Execute "Configuration: Quality Pipelines" below |
| review-gates | Execute "Configuration: Review Gates" below |
| structure | Execute "Configuration: Project Structure" below |
| credentials | Execute "Configuration: Credentials & Secrets" below |
| wizard | Load `Read references/wizard-flow.md` — skip to Step 5 (bootstrap already done) |

---

## Configuration: Plan Phase Settings

Configure plan phase settings using manage-config. Show current values first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get
```

Display current values, then ask user which settings to change:

**Branch strategy** (phase-1-init): `feature` (recommended) or `direct`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
```

**Backward compatibility** (phase-2-refine): `breaking` (recommended), `deprecation`, or `smart_and_ask`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
```

**Commit strategy** (phase-5-execute): `per_deliverable` (recommended), `per_plan`, or `none`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_strategy --value {per_deliverable|per_plan|none}
```

**Confidence threshold** (phase-2-refine, menu-only): `95` (recommended), `90`, or `100`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field confidence_threshold --value {95|90|100}
```

---

## Configuration: Review Gates

Show current values first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get
```

Display current gate values, then ask user which transitions should auto-continue (multi-select):
- "Plan without asking" → outline to planning
- "Execute without asking" → planning to execution
- "Finalize without asking" → execution to finalize

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

## Configuration: Quality Pipelines

Show current config first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get
```

Display current values, then configure pipelines using manage-config:

**Verification steps** (phase-5-execute): Discover available steps, present as multi-select, apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {comma_separated_selected_steps}
```

**Finalize steps** (phase-6-finalize): Discover available steps, present as multi-select, apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {comma_separated_selected_steps}
```

**PR merge strategy**: Ask user for the merge strategy used when merging PRs during branch cleanup (default: squash):

```
AskUserQuestion:
  questions:
    - question: "Which merge strategy should be used when merging PRs?"
      header: "PR Merge"
      options:
        - label: "squash (Recommended)"
          description: "Squash all commits into one before merging"
        - label: "merge"
          description: "Create a merge commit preserving all commits"
        - label: "rebase"
          description: "Rebase commits onto the base branch"
      multiSelect: false
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set --field pr_merge_strategy --value {squash|merge|rebase}
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

## Configuration: Skill Domains

Skill domains configure which implementation skills are loaded for different code types. Applicable domains are determined from architecture analysis results.

### Reconfigure Skill Domains

**Step 1: Get applicable domains from architecture analysis**

Query `extensions_used` from the architecture analysis (populated during project discovery):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived
```

Look for `extensions_used` in the output - these are bundles that detected modules in this project.

**Step 2: Map bundles to domain keys**

Get all available domains with bundle mappings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-available
```

Bundle to domain key mapping:
- `pm-dev-java` → `java`
- `pm-dev-java-cui` → `java-cui`
- `pm-dev-frontend` → `javascript`
- `pm-plugin-development` → `plan-marshall-plugin-dev`
- `pm-documents` → `documentation`
- `pm-requirements` → `requirements`

**Step 3: User domain selection**

Present AskUserQuestion with applicable domains pre-selected:

```yaml
AskUserQuestion:
  question: "Confirm skill domains for this project:"
  header: "Skill Domains"
  multiSelect: true
  options:
    # Pre-select domains from extensions_used
    # Show all available domains, mark applicable ones
    - label: "Java Development (detected)"
      description: "Java code patterns, CDI, JUnit (pm-dev-java)"
    - label: "Documentation (detected)"
      description: "AsciiDoc, ADRs (pm-documents)"
    - label: "JavaScript Development"
      description: "Modern JS, ESLint, Jest (pm-dev-frontend)"
    - label: "Plugin Development"
      description: "Claude Code components (pm-plugin-development)"
```

**Step 4: Configure selected domains**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains configure --domains "java,documentation"
```

This configures:
- `system` domain (always) with task_executors
- Each selected domain with bundle reference and workflow_skill_extensions
- Auto-appends extension verify steps to `plan.phase-5-execute.steps`

**Note**: The `configure` command replaces all existing domains with the selected ones.

### List Domains

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains list
```

### View Domain Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get --domain java
```

### Resolve Domain Skills (for task planning)

Aggregate core + profile skills with descriptions for LLM skill selection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-domain-skills \
  --domain java --profile implementation
```

### Update Domain Skills

Update skills for a specific profile:

```bash
# Update implementation profile skills
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains set \
  --domain java \
  --profile implementation \
  --defaults "pm-dev-java:java-core" \
  --optionals "pm-dev-java:java-cdi,pm-dev-java:java-maintenance"
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
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

Shows all modules with their purpose, responsibilities, and key packages.

### Operation: View Module Details

**Step 1: List modules**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

**Step 2: Get module details**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --name "{module}"
```

For full details including reasoning:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --name "{module}" --full
```

### Operation: Enrich Module

Add learned information to a module:

```bash
# Update responsibility
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name "{module}" --responsibility "{description}"

# Add tip
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich tip --module "{module}" --tip "{tip text}"

# Add insight
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module "{module}" --insight "{insight text}"

# Add best practice
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich best-practice --module "{module}" --practice "{practice text}"
```

### Operation: Regenerate

Regenerate project architecture from build files with optional enrichment.

**Step 1: Check for existing enrichment**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --check
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
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Step 3: Initialize enrichment (if reset or new)**

If user chose "Reset enrichment" or no enrichment existed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --force
```

**Step 4: LLM Architectural Analysis (automatic)**

Invoke the analysis skill to auto-populate enrichment with semantic descriptions:

```
Skill: plan-marshall:manage-architecture
```

The LLM reads discovered data, samples documentation and source code, then enriches with:
- Semantic module responsibilities
- Module purpose classification (infrastructure, domain-standards, tooling, etc.)
- Key packages per module with descriptions

**Step 5: Offer refinement (optional)**

After automatic analysis completes, offer user the option to refine:

```yaml
AskUserQuestion:
  question: "LLM analysis complete. Would you like to refine any descriptions?"
  header: "Refinement"
  options:
    - label: "Accept all"
      description: "Use LLM-generated descriptions as-is"
    - label: "Refine"
      description: "Review and adjust specific modules"
  multiSelect: false
```

If user chooses "Refine", use the "Edit Module" operation flow.

This regenerates `.plan/project-architecture/derived-data.json` from current build file definitions.

---

---

## Configuration: Credentials & Secrets

Manage credentials for external tool authentication (SonarCloud, etc.).

### Credentials Submenu

```
AskUserQuestion:
  question: "What would you like to do with credentials?"
  options:
    - label: "Configure new"
      description: "Set up credentials for an external tool"
      value: "configure"
    - label: "Edit existing"
      description: "Update URL, token, or password for a configured tool"
      value: "edit"
    - label: "List"
      description: "Show configured credentials (no secrets)"
      value: "list"
    - label: "Verify"
      description: "Test connectivity for a configured tool"
      value: "verify"
    - label: "Remove"
      description: "Remove credentials for a tool"
      value: "remove"
```

### Routing

| Selection | Action |
|-----------|--------|
| configure | Two-phase workflow (see below) |
| edit | Two-phase workflow (see below) |
| list | `python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials list` |
| verify | `python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials verify --skill {skill}` |
| remove | `python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials remove --skill {skill}` |

For `edit`, `verify`, and `remove`: if `--skill` is not known, first run `list` to show available skills, then ask the user which one to operate on.

### Configure Workflow

All values are collected via `AskUserQuestion` and passed as CLI args — no interactive input needed.

1. Discover providers:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials list-providers
   ```
2. Collect all values via `AskUserQuestion`: skill, URL, auth type, and token/username/password
3. For providers with `extra_fields` (e.g., sonar), auto-detect from CI config and confirm with user
4. Run configure via executor with all values as CLI args:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials configure \
     --skill {skill} --url {url} --auth-type {auth_type} \
     --token {token} \
     --extra organization={org} project_key={project_key} \
     --no-verify
   ```
5. Optionally verify:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials verify --skill {skill}
   ```
6. Run ensure-denied:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials ensure-denied --target project
   ```
7. If the configured skill was `workflow-integration-sonar`, check and add sonar-roundtrip:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-6-finalize get
   ```
   If `default:sonar-roundtrip` not in steps:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-6-finalize add-step --step default:sonar-roundtrip --after default:automated-review
   ```

### Edit Workflow

All values collected via `AskUserQuestion` — no interactive input needed.

1. Collect values via `AskUserQuestion`: URL, auth type, token/password (optional changes)
2. Run edit via executor with CLI args:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials edit \
     --skill {skill} --url {url} --auth-type {auth_type}
   ```
   For token changes, the LLM cannot update secrets via edit — use `remove` + `configure` instead.

---

After any configuration completes, return to Main Menu.
