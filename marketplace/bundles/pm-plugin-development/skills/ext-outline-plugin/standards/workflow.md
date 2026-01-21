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

### Step 2: Extract Matching Criteria

**CRITICAL**: This step is MANDATORY. Skipping to analysis without criteria is a workflow violation.

**Note**: The request text comes from `request.md` - read it if not already loaded.

Analyze the request text to extract:

1. **Request fragment**: Exact quote defining the change scope
2. **Criteria statement**: What makes a component "affected" - in objective terms
3. **Match indicators**: Concrete patterns that indicate a match
4. **Exclude indicators**: Patterns that indicate non-match

```
ANALYZE request text:
  1. Identify the ACTION (migrate, rename, update, change)
  2. Identify the SUBJECT (what is being changed)
  3. Identify the SCOPE (outputs, references, usages)

Derive:
  request_fragment = "{exact quote from request}"
  criteria = "{subject} in {scope} context"
  match_indicators = [concrete patterns]
  exclude_indicators = [concrete patterns]
```

**Log the criteria**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Matching Criteria:
  request_fragment: \"{request_fragment}\"
  criteria: \"{criteria}\"
  match_indicators: {match_indicators}
  exclude_indicators: {exclude_indicators}"
```

### Criteria Quality Rules

| Requirement | Valid | Invalid |
|-------------|-------|---------|
| **Derived from request** | "Has JSON output blocks" | "Is documentation" |
| **Objective** | "Contains ```json in Output section" | "Seems to use JSON" |
| **Content-based** | "No Output section found" | "Commands don't have outputs" |

**CRITICAL**: Never use component TYPES as exclude indicators.

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

For each bundle with files, spawn an agent. Pass only: `plan_id`, `bundle`, `criteria`.

```
FOR each bundle where filter returned file_count > 0:
  IF has skills:
    Task: pm-plugin-development:skill-analysis-agent
      Input:
        plan_id: {plan_id}
        bundle: {bundle}
        criteria: {criteria object from Step 2}

  IF has commands:
    Task: pm-plugin-development:command-analysis-agent
      Input:
        plan_id: {plan_id}
        bundle: {bundle}
        criteria: {criteria object from Step 2}

  IF has agents:
    Task: pm-plugin-development:agent-analysis-agent
      Input:
        plan_id: {plan_id}
        bundle: {bundle}
        criteria: {criteria object from Step 2}
```

**IMPORTANT**: Launch all agents in a SINGLE message for true parallelism.

**Agent Responsibility**: Each agent runs the filter script to get its file paths, analyzes those files using LLM reasoning, and returns findings per the contract. Agents do NOT log - logging is centralized in Step 4a.

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
      match_indicators: {finding.match_indicators_found}
      exclude_indicators: {finding.exclude_indicators_found}
      evidence: {finding.evidence}"
  ELSE:
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
      decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) NOT_AFFECTED: {finding.file_path}
      match_indicators: {finding.match_indicators_found}
      exclude_indicators: {finding.exclude_indicators_found}
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
