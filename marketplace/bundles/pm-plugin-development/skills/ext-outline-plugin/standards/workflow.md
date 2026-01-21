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

Spawn analysis agents for each component type from the loaded inventory:

```
Task: pm-plugin-development:skill-analysis-agent
  Input:
    file_paths: {inventory.skills from Step 1}
    criteria: {from Step 2}
    batch_id: "skills"
    plan_id: {plan_id}

Task: pm-plugin-development:command-analysis-agent
  Input:
    file_paths: {inventory.commands from Step 1}
    criteria: {from Step 2}
    batch_id: "commands"
    plan_id: {plan_id}

Task: pm-plugin-development:agent-analysis-agent
  Input:
    file_paths: {inventory.agents from Step 1}
    criteria: {from Step 2}
    batch_id: "agents"
    plan_id: {plan_id}
```

**IMPORTANT**: Launch all agents in a SINGLE message for true parallelism.

Only spawn agents for types that have files in inventory. Skip empty types.

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
- profile: implementation
- depends: none

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
| `profile` | implementation |
| `depends` | none, or deliverable number(s) |

---

## Decomposition Patterns

| Request Pattern | Typical Deliverables |
|-----------------|----------------------|
| "Add new skill" | 1. Create SKILL.md 2. Create standards 3. Update plugin.json |
| "Add new command" | 1. Create command.md 2. Update plugin.json |
| "Rename notation X to Y" | 1-N. Update each affected component |
| "Change output format" | 1-N. Update each producer/consumer |
| "Migrate to new API" | 1-N. Migrate each caller |
