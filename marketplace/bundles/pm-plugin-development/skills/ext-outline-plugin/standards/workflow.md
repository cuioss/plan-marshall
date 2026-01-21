# Plugin Outline Workflow

Unified workflow for plugin development outline phase. Routes based on change_type, not scope size.

## Critical Requirement

Deliverables MUST contain explicit file paths. A deliverable that says "update all X" without listing the files is INVALID.

## Inputs from Assessment

The Assessment Protocol (SKILL.md) provides these inputs:

| Input | Source | Description |
|-------|--------|-------------|
| `change_type` | Assessment Step 2 | create, modify, migrate, refactor |
| `work/inventory_filtered.toon` | Plan directory | Persisted inventory with scope and file paths |

The `work/inventory_filtered.toon` file contains:
- `scope.affected_artifacts` - Component types to target
- `scope.bundle_scope` - Bundles to target (all or specific list)
- `inventory.skills`, `inventory.commands`, `inventory.agents` - File paths

## Workflow Routing

Route based on `change_type`:

```
IF change_type == "create":
  → Create Flow (files don't exist yet)
ELSE:  # modify, migrate, refactor
  → Modify Flow (discovery + analysis)
```

---

## Create Flow

For creating new components. No discovery needed because files don't exist yet.

### Step 1: Log Decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Create flow: {affected_artifacts} in {bundle_scope}"
```

### Step 2: Build Deliverables

Create one deliverable per component to create. Use the deliverable template below.

**Execution Skills** (deliverables delegate to these):
- `pm-plugin-development:plugin-create` - For creating new components

---

## Modify Flow

For modifying, migrating, or refactoring existing components. Uses discovery and analysis.

### Step 1: Load Persisted Inventory

The Assessment Protocol (SKILL.md) already ran the inventory-assessment-agent which persisted results. Read the filtered inventory:

```bash
# Check reference exists
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} \
  --field inventory_filtered
```

If `inventory_filtered` is not set, ERROR: "Assessment incomplete - inventory_filtered not persisted"

```bash
# Read the inventory file
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/inventory_filtered.toon
```

Parse the TOON content to extract:
- `scope.affected_artifacts` - Component types
- `scope.bundle_scope` - Bundle filter (all or specific)
- `inventory.skills` - Skill file paths
- `inventory.commands` - Command file paths
- `inventory.agents` - Agent file paths

### Step 2: Load Request Text

Read the request text from `request.md` if not already loaded:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Extract the request text - this will be passed directly to analysis agents for semantic reasoning.

**Log the analysis start**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Starting semantic analysis
  request: \"{request_text}\""
```

### Step 3: Parallel Component Analysis

Analysis is split into two phases: **script filtering** (deterministic) and **agent analysis** (LLM reasoning).

**Step 3a: Extract Bundles**

Parse `inventory_filtered.toon` to get unique bundles:
```python
bundles = set()
for component_type in ['skills', 'commands', 'agents']:
    for path in inventory.get(component_type, []):
        # path: marketplace/bundles/{bundle}/...
        bundle = path.split('/')[2]
        bundles.add(bundle)
```

**Step 3b: Filter by Bundle (Script)**

For each bundle × component_type combination, run the filter script:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type {type}
```

**Output** (TOON):
```toon
status: success
bundle: pm-dev-java
component_type: skills
file_count: 17
files[17]:
  marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
  ...
```

Skip if `file_count: 0`.

**Step 3c: Spawn Analysis Agents**

For each bundle with files, spawn an agent. Pass: `plan_id`, `bundle`, `request_text`.

```
FOR each bundle where filter returned file_count > 0:
  IF has skills:
    Task: pm-plugin-development:skill-analysis-agent
      Input:
        plan_id: {plan_id}
        bundle: {bundle}
        request_text: {request text from Step 2}

  IF has commands:
    Task: pm-plugin-development:command-analysis-agent
      Input:
        plan_id: {plan_id}
        bundle: {bundle}
        request_text: {request text from Step 2}

  IF has agents:
    Task: pm-plugin-development:agent-analysis-agent
      Input:
        plan_id: {plan_id}
        bundle: {bundle}
        request_text: {request text from Step 2}
```

**IMPORTANT**: Launch all agents in a SINGLE message for true parallelism.

**Agent Responsibility**: Each agent runs the filter script to get its file paths, uses semantic reasoning to evaluate each file against the request, and returns findings per the contract. Agents do NOT log - logging is centralized in Step 4a.

**Step 3d: Error Handling**

**CRITICAL**: If ANY analysis agent fails due to API errors, **HALT the workflow immediately**.

```
IF any agent returns API error (529, timeout, connection error):
  HALT with error:
    status: error
    error_type: api_unavailable
    message: "Analysis agent failed due to API error. Retry later."
    failed_agent: {agent_name}
    bundle: {bundle}

  DO NOT:
    - Fall back to grep/search
    - Skip the failed bundle
    - Continue with partial analysis
    - Attempt manual file inspection
```

**Rationale**: Semantic analysis requires LLM reasoning. Simple grep cannot distinguish output specs from config/input JSON, leading to false positives that corrupt downstream deliverables.

### Step 4: Aggregate and Validate

Collect findings from each agent:

```
all_findings = skill_findings + command_findings + agent_findings
affected_files = [f for f in all_findings where f.status == "affected"]
```

**Validate completeness**:
```
total_analyzed = sum of all findings
expected_total = sum of all inventory files

IF total_analyzed != expected_total:
  ERROR: "Analysis incomplete: {total_analyzed}/{expected_total}"
```

### Step 4a: Log All Decisions (Centralized)

**CRITICAL**: The parent workflow logs all decisions. Agents return findings; parent handles logging.

**Why centralized?** Subagents cannot be relied upon to execute "secondary" script calls (logging). By centralizing logging in the parent workflow, we guarantee the audit trail exists.

```
FOR each finding in all_findings:
  IF finding.status == "affected":
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
      decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) AFFECTED: {finding.file_path}
      reasoning: {finding.reasoning}
      evidence: {finding.evidence}"
  ELSE:
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
      decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) NOT_AFFECTED: {finding.file_path}
      reasoning: {finding.reasoning}
      evidence: {finding.evidence}"
```

**Validation**: After logging, verify count:
```
logged_count = count of AFFECTED/NOT_AFFECTED logged
expected_count = total_analyzed from Step 4

IF logged_count != expected_count:
  ERROR: "Logging incomplete: {logged_count}/{expected_count}"
```

### Step 5: Link Affected Files

Persist affected files for execute phase:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "{comma-separated-paths}"
```

### Step 6: Build Deliverables

Create deliverables from affected files, grouped by bundle (or ~5-8 files per deliverable).

**Execution Skills** (deliverables delegate to these):
- `pm-plugin-development:plugin-maintain` - For modifying existing components

---

## Deliverable Template

```markdown
### {N}. {Action Verb} {Component Type}: {Name/Bundle}

**Metadata:**
- change_type: {create|modify|migrate|refactor}
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: {bundle-name}
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `{explicit/path/to/file1.md}`
- `{explicit/path/to/file2.md}`

**Change per file:** {What will be created or modified}

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {path}`
- Criteria: No quality issues detected

**Success Criteria:**
- {Specific criterion 1}
- {Specific criterion 2}
```

### Field Reference

| Field | Valid Values |
|-------|--------------|
| `change_type` | create, modify, migrate, refactor |
| `execution_mode` | automated, manual, mixed |
| `domain` | plan-marshall-plugin-dev |
| `module` | Bundle name (e.g., pm-dev-java, pm-workflow) |
| `depends` | none, or deliverable number(s) |
| `**Profiles:**` | Block with: implementation, testing |

---

## Decomposition Patterns

| Request Pattern | Typical Deliverables |
|-----------------|----------------------|
| "Add new skill" | 1. Create SKILL.md 2. Create standards 3. Update plugin.json |
| "Add new command" | 1. Create command.md 2. Update plugin.json |
| "Rename notation X to Y" | 1-N. Update each affected component |
| "Change output format" | 1-N. Update each producer/consumer |
| "Migrate to new API" | 1-N. Migrate each caller |
