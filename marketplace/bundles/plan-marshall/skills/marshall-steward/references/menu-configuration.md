# Menu Option: Configuration

Sub-menu for skill domains and project structure configuration.

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
    - label: "Full Reconfigure"
      description: "Run first-run wizard again"
      value: "wizard"
```

## Routing

| Selection | Action |
|-----------|--------|
| skill-domains | Execute "Configuration: Skill Domains" below |
| plan-phases | Execute "Configuration: Plan Phase Settings" below |
| quality-pipelines | Execute "Configuration: Quality Pipelines" below |
| structure | Execute "Configuration: Project Structure" below |
| wizard | Load and execute: `Read references/wizard-flow.md` |

---

## Configuration: Plan Phase Settings

Manage phase-specific settings distributed across init, execute, and other phases.

### Step 1: Select Phase to Configure

```
AskUserQuestion:
  question: "Which phase settings to configure?"
  header: "Phase"
  options:
    - label: "Init (phase 1)"
      description: "Branch strategy"
    - label: "Execute (phase 5)"
      description: "Compatibility, commit strategy"
    - label: "Refine (phase 2)"
      description: "Confidence threshold"
  multiSelect: false
```

### Phase 1 - Init Settings

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-1-init get
```

**branch_strategy**:
```
AskUserQuestion:
  question: "Branch strategy for plan execution?"
  header: "Branching"
  options:
    - label: "Direct"
      description: "Work on current branch"
    - label: "Feature branch"
      description: "Create feature branch per plan"
  multiSelect: false
```

Apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
```

### Phase 5 - Execute Settings

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute get
```

**compatibility**:
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

**commit_strategy**:
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

Apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute set --field {field} --value {value}
```

---

## Configuration: Quality Pipelines

Manage verification (phase 6) and finalize (phase 7) pipeline settings.

### Step 1: Show Current Pipeline Config

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify get
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-7-finalize get
```

### Step 2: Select What to Configure

```
AskUserQuestion:
  question: "What to configure?"
  header: "Pipeline"
  options:
    - label: "Verification steps"
      description: "Toggle generic and domain verification steps"
    - label: "Finalize steps"
      description: "Toggle finalize steps"
    - label: "Max iterations"
      description: "Set retry limits for verification and finalize"
  multiSelect: false
```

### Step 3a: Configure Verification Steps

Generic boolean steps:

```
AskUserQuestion:
  question: "Which generic verification steps to include?"
  header: "Verify Steps"
  multiSelect: true
  options:
    - label: "1_quality_check"
      description: "Build quality gate using canonical commands"
    - label: "2_build_verify"
      description: "Build verification using canonical commands"
```

Apply: for each deselected step:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify set-step --step {step_name} --enabled false
```

Domain steps (auto-populated from extensions via `provides_verify_steps()`):

```bash
# Toggle a domain step off
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify set-domain-step --domain java --step 1_technical_impl --enabled false
```

### Step 3b: Configure Finalize Steps

```
AskUserQuestion:
  question: "Which finalize steps to include?"
  header: "Finalize Steps"
  multiSelect: true
  options:
    - label: "1_commit_push"
      description: "Commit and push changes"
    - label: "2_create_pr"
      description: "Create pull request"
    - label: "3_automated_review"
      description: "CI automated review"
    - label: "4_sonar_roundtrip"
      description: "Sonar analysis roundtrip"
    - label: "5_knowledge_capture"
      description: "Capture learnings to memory"
    - label: "6_lessons_capture"
      description: "Record lessons learned"
```

Apply: for each deselected step:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-7-finalize set-step --step {step_name} --enabled false
```

### Step 3c: Set Max Iterations

```
AskUserQuestion:
  questions:
    - question: "Max iterations for verification phase?"
      header: "Verify Iters"
      multiSelect: false
      options:
        - label: "5 (Default)"
          description: "Standard retry limit for quality checks"
        - label: "3"
          description: "Fewer retries, faster completion"
        - label: "10"
          description: "More retries for complex projects"
    - question: "Max iterations for finalize phase?"
      header: "Finalize Iters"
      multiSelect: false
      options:
        - label: "3 (Default)"
          description: "Standard retry limit for commit/PR/CI"
        - label: "1"
          description: "Single attempt, fail fast"
        - label: "5"
          description: "More retries for CI roundtrips"
```

Apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify set-max-iterations --value {5|3|10}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-7-finalize set-max-iterations --value {3|1|5}
```

---

## Configuration: Skill Domains

Skill domains configure which implementation skills are loaded for different code types. Applicable domains are determined from architecture analysis results.

### Reconfigure Skill Domains

**Step 1: Get applicable domains from architecture analysis**

Query `extensions_used` from the architecture analysis (populated during project discovery):

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture derived
```

Look for `extensions_used` in the output - these are bundles that detected modules in this project.

**Step 2: Map bundles to domain keys**

Get all available domains with bundle mappings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  skill-domains configure --domains "java,documentation"
```

This configures:
- `system` domain (always) with task_executors
- Each selected domain with bundle reference and workflow_skill_extensions
- Collects verify steps from domain extensions for presentation

**Note**: The `configure` command replaces all existing domains with the selected ones.

### List Domains

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config skill-domains list
```

### View Domain Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config skill-domains get --domain java
```

### Resolve Domain Skills (for task planning)

Aggregate core + profile skills with descriptions for LLM skill selection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config resolve-domain-skills \
  --domain java --profile implementation
```

### Update Domain Skills

Update skills for a specific profile:

```bash
# Update implementation profile skills
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config skill-domains set \
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

**Step 4: LLM Architectural Analysis (automatic)**

Invoke the analysis skill to auto-populate enrichment with semantic descriptions:

```
Skill: plan-marshall:analyze-project-architecture
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

## Thin Agent Architecture (7-Phase Model)

The pm-workflow bundle uses thin agents that load phase skills statically:

| Agent | Purpose | Phase Skill |
|-------|---------|-------------|
| `plan-init-agent` | Initialize plan, detect domains | `pm-workflow:phase-1-init` |
| `request-refine-agent` | Clarify request | `pm-workflow:phase-2-refine` |
| `solution-outline-agent` | Create deliverables | `pm-workflow:phase-3-outline` |
| `task-plan-agent` | Create tasks from deliverables | `pm-workflow:phase-4-plan` |
| `task-execute-agent` | Execute single task | `pm-workflow:phase-5-execute` + `task.skills` |
| `q-gate-validation-agent` | Quality verification | `pm-workflow:phase-6-verify` |
| `plan-finalize-agent` | Commit, PR | `pm-workflow:phase-7-finalize` |

Phase skills are statically known (not resolved from config). Domain-specific extensions are loaded via `resolve-workflow-skill-extension --domain {domain} --type {outline|triage}`.

---

After any configuration completes, return to Main Menu.
