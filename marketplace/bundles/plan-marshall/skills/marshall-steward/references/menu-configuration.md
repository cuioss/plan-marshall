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
    - label: "Project Structure"
      description: "View, regenerate, and enrich architecture data"
      value: "structure"
    - label: "Full Reconfigure"
      description: "Run first-run wizard again"
      value: "wizard"
```

## Routing

| Selection | Action |
|-----------|--------|
| skill-domains | Execute "Configuration: Skill Domains" below |
| structure | Execute "Configuration: Project Structure" below |
| wizard | Load and execute: `Read references/wizard-flow.md` |

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

## Thin Agent Architecture (5-Phase Model)

The pm-workflow bundle uses thin agents that load skills from system domain:

| Agent | Purpose | Skill Source |
|-------|---------|--------------|
| `plan-init-agent` | Initialize plan, detect domains | System defaults only |
| `solution-outline-agent` | Create deliverables | `resolve-workflow-skill --phase 2-outline` |
| `task-plan-agent` | Create tasks from deliverables | `resolve-workflow-skill --phase 3-plan` |
| `task-execute-agent` | Execute single task | `resolve-workflow-skill --phase 4-execute` + `task.skills` |
| `plan-finalize-agent` | Commit, PR, triage | `resolve-workflow-skill --phase 5-finalize` |

Workflow skills are resolved from `system.workflow_skills`. Domain-specific extensions are loaded via `resolve-workflow-skill-extension --domain {domain} --type {outline|triage}`.

---

After any configuration completes, return to Main Menu.
